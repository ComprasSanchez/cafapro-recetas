from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set, Literal, cast
import os
import numpy as np

from sqlalchemy import select, update, or_, and_
from sqlalchemy.orm import Session

from core.process_tif import TiffProcessor, ScanOut
from app.db.models import (
    Archivo,
    ArchivoDetalle,
    Recetas,
    Asociacion,
    Troqueles,
    EstadoTroquelEnum,
    Recepcion,
    Debitos,
    Prestador,
)
from app.infra.s3_storage import S3Storage

from app.service.integraciones.medicamento_client import MedicamentoClient
from app.dto.medicamentos_dto import MedicamentoDTO


@dataclass(frozen=True)
class ProcesarItemIn:
    file_name: str
    full_path: str


@dataclass
class ProcesarResumen:
    ok: int = 0
    sin_match: int = 0
    duplicados: int = 0
    ya_asociado: int = 0
    errores: List[str] = None

    def __post_init__(self) -> None:
        if self.errores is None:
            self.errores = []


@dataclass(frozen=True)
class _MatchResult:
    ref_to_archivo: Dict[str, Optional[Archivo]]
    duplicated_refs: Set[str]
    missing_refs: Set[str]


class TiffService:
    def __init__(
        self,
        *,
        storage: S3Storage,
        tif: Optional[TiffProcessor] = None,
        client: Optional[MedicamentoClient] = None,
    ) -> None:
        self._storage = storage
        self._tif = tif or TiffProcessor()
        self._client = client or MedicamentoClient()

    # -------------------------
    # Helpers
    # -------------------------
    @staticmethod
    def _norm_str(x) -> str:
        return str(x).strip() if x is not None else ""

    @staticmethod
    def _exists_processed_base_in_recepcion(s: Session, recepcion_id: int, base_name: str) -> bool:
        # buscamos si ya existe alguna key que contenga ".../<base>_f.jpg" o ".../<base>_d.jpg"
        like_pat = f"%/{base_name}_%"
        rid = (
            s.execute(
                select(Recetas.receta_id)
                .where(
                    and_(
                        Recetas.recepcion_id == int(recepcion_id),
                        or_(
                            Recetas.ubicacion_frente.ilike(like_pat),
                            Recetas.ubicacion_dorso.ilike(like_pat),
                        ),
                    )
                )
                .limit(1)
            )
            .scalar_one_or_none()
        )
        return rid is not None

    @staticmethod
    def _archivo_ts(a: Archivo) -> datetime:
        return datetime.combine(a.fecha, a.hora)

    @staticmethod
    def _esta_vencido(archivo_ts: datetime, fecha_presentacion: datetime) -> bool:
        cutoff = fecha_presentacion - timedelta(days=60)
        return archivo_ts < cutoff

    @staticmethod
    def _base_from_tif_path(full_path: str) -> str:
        return Path(full_path).stem  # "pami_20260202155525044"

    @staticmethod
    def _match_all_refs(s: Session, refs: List[str]) -> _MatchResult:
        refs_norm = [str(r).strip() for r in refs if r and str(r).strip()]
        refs_set = set(refs_norm)
        if not refs_set:
            return _MatchResult(ref_to_archivo={}, duplicated_refs=set(), missing_refs=set())

        rows = (
            s.execute(
                select(Archivo).where(
                    or_(
                        Archivo.nro_referencia.in_(list(refs_set)),
                        Archivo.nro_receta.in_(list(refs_set)),
                    )
                )
            )
            .scalars()
            .all()
        )

        by_token: Dict[str, List[Archivo]] = {}
        for a in rows:
            nro_ref = str(getattr(a, "nro_referencia", "") or "").strip()
            nro_rec = str(getattr(a, "nro_receta", "") or "").strip()
            if nro_ref and nro_ref in refs_set:
                by_token.setdefault(nro_ref, []).append(a)
            if nro_rec and nro_rec in refs_set:
                by_token.setdefault(nro_rec, []).append(a)

        duplicated = {tok for tok, arr in by_token.items() if len(arr) > 1}
        missing = {tok for tok in refs_set if tok not in by_token}

        ref_to_archivo: Dict[str, Optional[Archivo]] = {}
        for tok in refs_set:
            if tok in duplicated:
                ref_to_archivo[tok] = None
            elif tok in by_token:
                ref_to_archivo[tok] = by_token[tok][0]
            else:
                ref_to_archivo[tok] = None

        return _MatchResult(ref_to_archivo=ref_to_archivo, duplicated_refs=duplicated, missing_refs=missing)

    @staticmethod
    def _obs_slug_from_nombre(nombre: str) -> str:
        return (nombre or "").strip().lower()

    @staticmethod
    def _year_month_from_basename_or_fallback(base_name: str, archivo: Archivo, tif_path: str) -> tuple[str, str]:
        # base_name: "pami_20260202155525044" o "apross_123456"
        part = base_name.split("_", 1)[1] if "_" in base_name else base_name

        if len(part) >= 6 and part[:6].isdigit():
            yyyy = part[:4]
            mm = part[4:6]
            if len(yyyy) == 4 and 1 <= int(mm) <= 12:
                return yyyy, mm

        # fallback: fecha del Archivo (IMED)
        try:
            return f"{archivo.fecha.year:04d}", f"{archivo.fecha.month:02d}"
        except Exception:
            ts = datetime.fromtimestamp(os.path.getmtime(tif_path))
            return f"{ts.year:04d}", f"{ts.month:02d}"

    @staticmethod
    def _build_s3_keys(*, prestador_imed: str, yyyy: str, mm: str, base_name: str) -> tuple[str, str]:
        base = f"{prestador_imed}/{yyyy}/{mm}"
        return (
            f"{base}/{base_name}_f.jpg",
            f"{base}/{base_name}_d.jpg",
        )

    def procesar(
            self,
            s: Session,
            recepcion_id: int,
            usuario_id: int,
            items: List[ProcesarItemIn],
    ) -> ProcesarResumen:
        resumen = ProcesarResumen()
        med_cache: Dict[str, Optional[MedicamentoDTO]] = {}

        # -----------------------------------------
        # 0) Cargar recepción + prestador.imed
        # -----------------------------------------
        rec: Recepcion | None = (
            s.execute(select(Recepcion).where(Recepcion.recepcion_id == recepcion_id)).scalar_one_or_none()
        )
        if not rec:
            raise RuntimeError(f"No existe la recepción {recepcion_id}")

        pr_row = (
            s.execute(select(Prestador).where(Prestador.prestador_id == rec.prestador_id)).scalar_one_or_none()
        )
        if not pr_row:
            raise RuntimeError("No existe el Prestador asociado a la recepción.")

        prestador_imed = (getattr(pr_row, "imed", "") or "").strip()
        if not prestador_imed:
            raise RuntimeError("Prestador.imed está vacío; no se puede armar key S3.")

        fecha_presentacion = rec.fecha_presentacion
        MOTIVO_DEBITO_VENCIDO_60_ID = 11

        # -----------------------------------------
        # 1) Idempotencia SOLO dentro de la misma recepción
        #    (skip si ya existe alguna key con base_name)
        # -----------------------------------------
        items_filtrados: List[ProcesarItemIn] = []
        for it in items:
            base_name = self._base_from_tif_path(it.full_path)  # ej: "pami_20260202155525044"
            if base_name and self._exists_processed_base_in_recepcion(s, recepcion_id, base_name):
                resumen.ya_asociado += 1
                continue
            items_filtrados.append(it)

        if not items_filtrados:
            return resumen

        # -----------------------------------------
        # 2) Scan TIFF (headers + troqueles + detections)
        # -----------------------------------------
        scanned: List[Tuple[ProcesarItemIn, ScanOut, List[np.ndarray]]] = []
        all_refs: List[str] = []

        for it in items_filtrados:
            try:
                scan, pages = self._tif.scan_with_pages(it.full_path)
                scanned.append((it, scan, pages))
                all_refs.extend(scan.headers or [])
            except Exception as e:
                resumen.errores.append(f"{it.file_name}: scan error: {e}")

        if not scanned:
            return resumen

        # -----------------------------------------
        # 3) Match masivo por referencias (headers)
        # -----------------------------------------
        match = self._match_all_refs(s, refs=all_refs)

        # -----------------------------------------
        # 4) Elegir 1 Archivo por TIFF (por ref)
        # -----------------------------------------
        work: List[Tuple[int, ScanOut, List[np.ndarray], str, str]] = []

        for it, scan, pages  in scanned:
            refs = [self._norm_str(x) for x in (scan.headers or []) if self._norm_str(x)]

            if not refs:
                resumen.sin_match += 1
                continue

            # si alguna ref es duplicada => no sabemos qué archivo elegir
            if any(ref in match.duplicated_refs for ref in refs):
                resumen.duplicados += 1
                continue

            archivo: Optional[Archivo] = None
            for ref in refs:
                a = match.ref_to_archivo.get(ref)
                if a is not None:
                    archivo = a
                    break

            if archivo is None:
                resumen.sin_match += 1
                continue

            work.append((archivo.archivo_id, scan, pages, it.full_path, it.file_name))

        if not work:
            return resumen

        archivo_ids = [w[0] for w in work]

        # -----------------------------------------
        # 5) Garantía: Archivos de la corrida asignados a recepción actual
        # -----------------------------------------
        s.execute(
            update(Archivo)
            .where(Archivo.archivo_id.in_(archivo_ids))
            .values(recepcion_id=int(recepcion_id))
        )
        s.flush()

        # -----------------------------------------
        # 6) Bulk load Archivos + Detalles
        # -----------------------------------------
        archivos = (
            s.execute(select(Archivo).where(Archivo.archivo_id.in_(archivo_ids)))
            .scalars()
            .all()
        )
        archivo_by_id: Dict[int, Archivo] = {a.archivo_id: a for a in archivos}

        detalles = (
            s.execute(select(ArchivoDetalle).where(ArchivoDetalle.archivo_id.in_(archivo_ids)))
            .scalars()
            .all()
        )
        detalles_by_archivo: Dict[int, List[ArchivoDetalle]] = {}
        for d in detalles:
            detalles_by_archivo.setdefault(d.archivo_id, []).append(d)

        # -----------------------------------------
        # 7) Asociaciones vigentes por nro_referencia (bulk)
        # -----------------------------------------
        refs_set: Set[str] = set()
        for aid in archivo_ids:
            ar = archivo_by_id.get(aid)
            ref = self._norm_str(getattr(ar, "nro_referencia", None))
            if ref:
                refs_set.add(ref)

        vigente_por_ref: Dict[str, List[Tuple[int, int]]] = {}  # ref -> [(asoc_id, receta_id)]
        if refs_set:
            rows = (
                s.execute(
                    select(Asociacion.asociacion_id, Asociacion.receta_id, Archivo.nro_referencia)
                    .join(Archivo, Archivo.archivo_id == Asociacion.archivo_id)
                    .where(
                        Asociacion.vigente.is_(True),
                        Archivo.nro_referencia.in_(list(refs_set)),
                    )
                )
                .all()
            )
            for asoc_id, receta_id, nro_ref in rows:
                ref = self._norm_str(nro_ref)
                if ref:
                    vigente_por_ref.setdefault(ref, []).append((int(asoc_id), int(receta_id)))

        # -----------------------------------------
        # 8) Persistencia
        # -----------------------------------------
        troqueles_to_add: List[Troqueles] = []
        asoc_to_add: List[Asociacion] = []
        refs_desactivados: Set[str] = set()

        for archivo_id, scan, pages, tiff_path, file_name in work:
            archivo = archivo_by_id.get(archivo_id)
            if not archivo:
                resumen.errores.append(f"{file_name}: archivo_id {archivo_id} no existe en DB")
                continue

            ref = self._norm_str(getattr(archivo, "nro_referencia", None))

            # vencido
            archivo_ts = self._archivo_ts(archivo)
            esta_vencido = self._esta_vencido(archivo_ts, fecha_presentacion)

            if getattr(archivo, "vencido", False) != esta_vencido:
                archivo.vencido = esta_vencido

            # versionado por ref
            prev = vigente_por_ref.get(ref, []) if ref else []
            if prev:
                resumen.ya_asociado += 1
                if ref and ref not in refs_desactivados:
                    refs_desactivados.add(ref)

                    asoc_ids = [a_id for a_id, _ in prev]
                    receta_ids = [r_id for _, r_id in prev]

                    s.execute(
                        update(Asociacion)
                        .where(Asociacion.asociacion_id.in_(asoc_ids))
                        .values(vigente=False)
                    )

                    s.execute(
                        update(Recetas)
                        .where(Recetas.receta_id.in_(receta_ids))
                        .values(vigente=False)
                    )

            dets = detalles_by_archivo.get(archivo_id, [])

            # -------------------------
            # cods_detalle + importe_por_cod
            # -------------------------
            importe_por_cod: Dict[str, float] = {}
            cods_detalle: Set[str] = set()

            for d in dets:
                ca = self._norm_str(getattr(d, "cod_medic", None))
                if not ca:
                    continue
                cods_detalle.add(ca)
                importe_por_cod[ca] = importe_por_cod.get(ca, 0.0) + float(getattr(d, "importe_obs", 0) or 0)

            # -------------------------
            # counts por codebar (EAN13)
            # -------------------------
            counts: Dict[str, int] = {}
            for cod in (scan.troqueles or []):
                cod = self._norm_str(cod)
                if not cod:
                    continue
                counts[cod] = counts.get(cod, 0) + 1

            # -------------------------
            # A/V/R (sin cache): consulto directo a la API
            # A = 404 (dto None)
            # V = dto existe y code_alfabeta coincide con cod_medic
            # R = dto existe y NO coincide
            # -------------------------
            estado_por_codebar: Dict[str, EstadoTroquelEnum] = {}
            dto_por_codebar: Dict[str, MedicamentoDTO] = {}

            if counts:
                for codebar in counts.keys():
                    if codebar in med_cache:
                        dto = med_cache[codebar]
                    else:
                        dto = self._client.get_by_codebar(codebar)  # 404 => None
                        med_cache[codebar] = dto

                    if dto is None:
                        estado_por_codebar[codebar] = EstadoTroquelEnum.A
                        continue

                    dto_por_codebar[codebar] = dto

                    ca = str(dto.code_alfabeta or "").strip()
                    if ca and ca in cods_detalle:
                        estado_por_codebar[codebar] = EstadoTroquelEnum.V
                    else:
                        estado_por_codebar[codebar] = EstadoTroquelEnum.R

            # -------------------------
            # Render a BYTES (sin disco)
            # -------------------------
            try:
                estado_render: Dict[str, Literal["V", "A", "R"]] = {
                    k: cast(Literal["V", "A", "R"], v.value) for k, v in estado_por_codebar.items()
                }
                files = self._tif.render_bytes(
                    tiff_path=tiff_path,
                    scan=scan,
                    pages=pages,
                    estado_por_codebar=estado_render,
                )
            except Exception as e:
                resumen.errores.append(f"{file_name}: render error: {e}")
                files = {"front_bytes": None, "back_bytes": None}

            front_bytes = files.get("front_bytes")
            back_bytes = files.get("back_bytes")

            # -------------------------
            # Keys S3: {imed}/{yyyy}/{mm}/{base}_f|_d.jpg
            # base = nombre tif sin extensión (respeta pami/apross/etc)
            # -------------------------
            base_name = self._base_from_tif_path(tiff_path)  # ej "pami_20260202155525044"
            yyyy, mm = self._year_month_from_basename_or_fallback(base_name, archivo, tiff_path)

            front_key, back_key = self._build_s3_keys(
                prestador_imed=prestador_imed,
                yyyy=yyyy,
                mm=mm,
                base_name=base_name,
            )

            # -------------------------
            # Subir S3
            # -------------------------
            try:
                if front_bytes:
                    self._storage.put_jpg(front_key, front_bytes)
                if back_bytes:
                    self._storage.put_jpg(back_key, back_bytes)
            except Exception as e:
                resumen.errores.append(f"{file_name}: S3 upload error: {e}")
                continue

            # -------------------------
            # Crear receta (guardando KEYS)
            # -------------------------
            nro_receta = self._norm_str(getattr(archivo, "nro_receta", None)) or "-"

            receta = Recetas(
                recepcion_id=int(recepcion_id),
                nro_receta=nro_receta,
                ubicacion_frente=front_key if front_bytes else None,
                ubicacion_dorso=back_key if back_bytes else None,
                fecha_prescripcion=None,
                observacion=None,
                usuario_id=usuario_id,
                estado_receta_id=2,
                creado_en=datetime.now(),
                vigente=True,
            )
            s.add(receta)
            s.flush()

            # asociar (vigente)
            asoc_to_add.append(
                Asociacion(
                    receta_id=receta.receta_id,
                    archivo_id=archivo_id,
                    vigente=True,
                )
            )

            # debito vencido
            if esta_vencido:
                exists = (
                    s.execute(
                        select(Debitos.debito_id)
                        .where(
                            Debitos.receta_id == receta.receta_id,
                            Debitos.motivo_debito_id == MOTIVO_DEBITO_VENCIDO_60_ID,
                        )
                        .limit(1)
                    ).scalar_one_or_none()
                )
                if exists is None:
                    s.add(
                        Debitos(
                            receta_id=receta.receta_id,
                            motivo_debito_id=MOTIVO_DEBITO_VENCIDO_60_ID,
                            detalle="Vencido por 60 días (auto)",
                        )
                    )

            # troqueles (usa dto_por_codebar + estado_por_codebar)
            if counts:
                for codebar, qty in counts.items():
                    estado = estado_por_codebar.get(codebar, EstadoTroquelEnum.A)
                    dto = dto_por_codebar.get(codebar)  # None si A

                    droga_concat = dto.drogas_concat if dto else None
                    presentacion = dto.presentacion if dto else None
                    code_alfabeta = int(dto.code_alfabeta or 0) if dto else 0

                    monto = 0.0
                    if estado == EstadoTroquelEnum.V and code_alfabeta:
                        monto = float(importe_por_cod.get(str(code_alfabeta), 0.0))

                    troqueles_to_add.append(
                        Troqueles(
                            receta_id=receta.receta_id,
                            codigo_barra=codebar,
                            droga=droga_concat,
                            presentacion=presentacion,
                            code_alfabeta=code_alfabeta,
                            monto=monto,
                            cantidad=qty,
                            estado=estado,
                        )
                    )

            resumen.ok += 1

        if asoc_to_add:
            s.add_all(asoc_to_add)
        if troqueles_to_add:
            s.add_all(troqueles_to_add)

        return resumen

