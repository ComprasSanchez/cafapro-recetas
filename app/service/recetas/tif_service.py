from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set, Literal
from collections import Counter
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
    def _match_all_refs(s: Session, recepcion_id: int, refs: List[str]) -> _MatchResult:
        # 1) normalizar tokens
        refs_set: Set[str] = {str(r).strip() for r in refs if r and str(r).strip()}
        if not refs_set:
            return _MatchResult(ref_to_archivo={}, duplicated_refs=set(), missing_refs=set())

        # 2) query SOLO dentro de la recepción
        rows = (
            s.execute(
                select(Archivo).where(
                    and_(
                        Archivo.recepcion_id == int(recepcion_id),
                        or_(
                            Archivo.nro_referencia.in_(list(refs_set)),
                            Archivo.nro_receta.in_(list(refs_set)),
                        ),
                    )
                )
            )
            .scalars()
            .all()
        )

        # 3) indexar por token (ref o receta)
        by_token: Dict[str, List[Archivo]] = {}
        for a in rows:
            nro_ref = (getattr(a, "nro_referencia", "") or "").strip()
            nro_rec = (getattr(a, "nro_receta", "") or "").strip()

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
            else:
                # único o inexistente
                arr = by_token.get(tok)
                ref_to_archivo[tok] = arr[0] if arr else None

        return _MatchResult(ref_to_archivo=ref_to_archivo, duplicated_refs=duplicated, missing_refs=missing)

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
        match = self._match_all_refs(s, recepcion_id, all_refs)

        # -----------------------------------------
        # 4) Elegir 1 Archivo por TIFF (por ref)
        # -----------------------------------------
        work: List[Tuple[int, ScanOut, List[np.ndarray], str, str]] = []

        for it, scan, pages in scanned:
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
        # 7) Asociaciones vigentes por recepción (bulk, sin IN por refs)
        # -----------------------------------------
        rows_prev = (
            s.execute(
                select(Asociacion.asociacion_id, Asociacion.receta_id, Asociacion.archivo_id)
                .join(Archivo, Archivo.archivo_id == Asociacion.archivo_id)
                .where(
                    Asociacion.vigente.is_(True),
                    Archivo.recepcion_id == int(recepcion_id),
                )
            )
            .all()
        )

        # archivo_id -> [(asoc_id, receta_id)]
        vigente_por_archivo: Dict[int, List[Tuple[int, int]]] = {}
        for asoc_id, receta_id, archivo_id in rows_prev:
            vigente_por_archivo.setdefault(int(archivo_id), []).append((int(asoc_id), int(receta_id)))

        # -----------------------------------------
        # 8) Persistencia
        # -----------------------------------------
        troqueles_to_add: List[Troqueles] = []
        asoc_to_add: List[Asociacion] = []
        recetas_vencidas: List[int] = []

        asoc_ids_to_disable: Set[int] = set()
        receta_ids_to_disable: Set[int] = set()
        for archivo_id, scan, pages, tiff_path, file_name in work:
            archivo = archivo_by_id.get(archivo_id)
            if not archivo:
                resumen.errores.append(f"{file_name}: archivo_id {archivo_id} no existe en DB")
                continue


            # vencido
            archivo_ts = self._archivo_ts(archivo)
            esta_vencido = self._esta_vencido(archivo_ts, fecha_presentacion)

            if getattr(archivo, "vencido", False) != esta_vencido:
                archivo.vencido = esta_vencido

            prev = vigente_por_archivo.get(int(archivo_id), [])
            if prev:
                resumen.ya_asociado += 1
                for a_id, r_id in prev:
                    asoc_ids_to_disable.add(int(a_id))
                    receta_ids_to_disable.add(int(r_id))

            dets = detalles_by_archivo.get(archivo_id, [])

            # -------------------------
            # cods_detalle + importe_por_cod + cant_por_cod
            # -------------------------
            importe_por_cod: Dict[str, float] = {}
            cods_detalle: Set[str] = set()
            cant_por_cod: Dict[str, int] = {}

            for d in dets:
                ca = self._norm_str(getattr(d, "cod_medic", None))
                if not ca:
                    continue

                cods_detalle.add(ca)

                # importes
                importe_por_cod[ca] = importe_por_cod.get(ca, 0.0) + float(getattr(d, "importe_obs", 0) or 0)

                # cantidades esperadas (sumo por cod_medic)
                cant_por_cod[ca] = cant_por_cod.get(ca, 0) + int(getattr(d, "cantidad", 0) or 0)

            # -------------------------
            # counts por codebar (EAN13) (scan)
            # -------------------------
            counts: Dict[str, int] = dict(
                Counter(self._norm_str(c) for c in (scan.troqueles or []) if self._norm_str(c))
            )

            # -------------------------
            # Estados:
            # - UI/Render: V si matchea, independientemente de cantidad
            # - DB:        V si matchea y cantidad ok; R si matchea pero cantidad NO ok
            # - A: API 404
            # - R: API ok pero no matchea
            # -------------------------
            estado_db_por_codebar: Dict[str, EstadoTroquelEnum] = {}
            estado_render_por_codebar: Dict[str, Literal["V", "A", "R"]] = {}
            dto_por_codebar: Dict[str, MedicamentoDTO] = {}

            if counts:
                for codebar, qty_scan in counts.items():
                    if codebar in med_cache:
                        dto = med_cache[codebar]
                    else:
                        dto = self._client.get_by_codebar(codebar)  # 404 => None
                        med_cache[codebar] = dto

                    if dto is None:
                        estado_db_por_codebar[codebar] = EstadoTroquelEnum.A
                        estado_render_por_codebar[codebar] = "A"
                        continue

                    dto_por_codebar[codebar] = dto

                    ca = str(dto.code_alfabeta or "").strip()
                    match_detalle = bool(ca) and (ca in cods_detalle)

                    if not match_detalle:
                        # no matchea => rojo en UI y en DB
                        estado_db_por_codebar[codebar] = EstadoTroquelEnum.R
                        estado_render_por_codebar[codebar] = "R"
                        continue

                    # matchea => verde SIEMPRE en UI
                    estado_render_por_codebar[codebar] = "V"

                    # DB: solo R si cantidad no coincide
                    qty_det = int(cant_por_cod.get(ca, 0))
                    if qty_det != int(qty_scan):
                        estado_db_por_codebar[codebar] = EstadoTroquelEnum.R
                    else:
                        estado_db_por_codebar[codebar] = EstadoTroquelEnum.V

            # -------------------------
            # Render a BYTES (sin disco)
            #   OJO: render usa estado_render_por_codebar (color UI)
            # -------------------------
            try:
                files = self._tif.render_bytes(
                    tiff_path=tiff_path,
                    scan=scan,
                    pages=pages,
                    estado_por_codebar=estado_render_por_codebar,
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
                recetas_vencidas.append(int(receta.receta_id))

            # troqueles (usa dto_por_codebar + estado_db_por_codebar)
            if counts:
                for codebar, qty in counts.items():
                    estado = estado_db_por_codebar.get(codebar, EstadoTroquelEnum.A)
                    dto = dto_por_codebar.get(codebar)  # None si A

                    droga_concat = dto.drogas_concat if dto else None
                    presentacion = dto.presentacion if dto else None
                    code_alfabeta = int(dto.code_alfabeta or 0) if dto else 0

                    monto = 0.0
                    if code_alfabeta and str(code_alfabeta) in cods_detalle:
                        monto = float(importe_por_cod.get(str(code_alfabeta), 0.0))

                    troqueles_to_add.append(
                        Troqueles(
                            receta_id=receta.receta_id,
                            codigo_barra=codebar,
                            droga=droga_concat,
                            presentacion=presentacion,
                            code_alfabeta=code_alfabeta,
                            monto= Decimal(monto),
                            cantidad=int(qty),
                            estado=estado,
                        )
                    )

            resumen.ok += 1

        # Aplicar versionado en batch (1 update por tabla)
        if asoc_ids_to_disable:
            s.execute(
                update(Asociacion)
                .where(Asociacion.asociacion_id.in_(list(asoc_ids_to_disable)))
                .values(vigente=False)
            )

        if receta_ids_to_disable:
            s.execute(
                update(Recetas)
                .where(Recetas.receta_id.in_(list(receta_ids_to_disable)))
                .values(vigente=False)
            )

        if recetas_vencidas:
            ya_tienen = set(
                s.execute(
                    select(Debitos.receta_id).where(
                        Debitos.motivo_debito_id == MOTIVO_DEBITO_VENCIDO_60_ID,
                        Debitos.receta_id.in_(recetas_vencidas),
                    )
                ).scalars().all()
            )

            for rid in recetas_vencidas:
                if rid in ya_tienen:
                    continue
                s.add(
                    Debitos(
                        receta_id=rid,
                        motivo_debito_id=MOTIVO_DEBITO_VENCIDO_60_ID,
                        detalle="Vencido por 60 días (auto)",
                    )
                )

        if asoc_to_add:
            s.add_all(asoc_to_add)
        if troqueles_to_add:
            s.add_all(troqueles_to_add)

        return resumen
