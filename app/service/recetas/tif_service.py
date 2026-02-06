from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set, Literal, cast

from sqlalchemy import select, update, or_, and_
from sqlalchemy.orm import Session

from core.process_tif import TiffProcessor, ScanOut
from app.db.models import (
    Archivo,
    ArchivoDetalle,
    Recetas,
    Asociacion,
    Troqueles,
    EstadoTroquelEnum, Recepcion, Debitos,
)
from app.service.recetas.troquel_enrichment_service import TroquelEnrichmentService, TroquelEnrichment


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
        tif: Optional[TiffProcessor] = None,
        troquel_enrich: Optional[TroquelEnrichmentService] = None,
    ) -> None:
        self._tif = tif or TiffProcessor()
        self._enrich = troquel_enrich or TroquelEnrichmentService()

    # -------------------------
    # Helpers
    # -------------------------
    @staticmethod
    def _scan_dt_from_name(path: str) -> datetime:
        """
        ejemplo: "pami_20260127121247004_f.jpg" / "pami_20260127125654006_d.jpg"
        """
        name = Path(path).stem
        parts = name.split("_")
        ts = parts[1]  # YYYYMMDDHHMMSSmmm
        dt = datetime.strptime(ts[:14], "%Y%m%d%H%M%S")
        ms = int(ts[14:17])
        return dt.replace(microsecond=ms * 1000)

    @staticmethod
    def _norm_str(x) -> str:
        return str(x).strip() if x is not None else ""

    @staticmethod
    def _extract_token_from_tif_path(full_path: str) -> Optional[str]:
        """
        Entrada real:
            C:\\...\\pami_20260127125654006.tif
        Devuelve:
            20260127125654006
        """
        stem = Path(full_path).stem  # "pami_20260127125654006"
        if not stem.startswith("pami_"):
            return None
        token = stem.replace("pami_", "", 1).strip()
        return token or None

    @staticmethod
    def _exists_processed_token_in_recepcion(s: Session, recepcion_id: int, token: str) -> bool:
        """
        SKIP TOTAL SOLO dentro de la misma recepción.
        Evita reprocesar 2 veces la misma imagen en la misma recepción (ahorro CPU),
        pero permite que el mismo token se procese en otra recepción.
        """
        like_pat = f"%pami_{token}_%"
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
        # fecha y hora siempre vienen (según vos)
        return datetime.combine(a.fecha, a.hora)

    @staticmethod
    def _esta_vencido(archivo_ts: datetime, fecha_presentacion: datetime) -> bool:
        cutoff = fecha_presentacion - timedelta(days=60)
        return archivo_ts < cutoff

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

        # token -> [Archivo...]
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

        return _MatchResult(
            ref_to_archivo=ref_to_archivo,
            duplicated_refs=duplicated,
            missing_refs=missing,
        )

    # -------------------------
    # Main
    # -------------------------
    def procesar(
            self,
            s: Session,
            recepcion_id: int,
            usuario_id: int,  # Recetas.usuario_id es NOT NULL
            items: List[ProcesarItemIn],
            output_dir: str,
        ) -> ProcesarResumen:
        resumen = ProcesarResumen()
        rec = (s.execute(select(Recepcion).where(Recepcion.recepcion_id == recepcion_id)).scalar_one_or_none())
        if not rec:
            raise RuntimeError(f"No existe la recepción {recepcion_id}")

        fecha_presentacion = rec.fecha_presentacion
        MOTIVO_DEBITO_VENCIDO_60_ID = 11

        # cache por corrida: codebar -> enrichment
        enrich_cache: Dict[str, TroquelEnrichment] = {}

        # =========
        # 0) PRE-CHECK: idempotencia por imagen/origen SOLO dentro de la misma recepción
        # =========
        items_filtrados: List[ProcesarItemIn] = []
        for it in items:
            token = self._extract_token_from_tif_path(it.full_path)
            if token and self._exists_processed_token_in_recepcion(s, recepcion_id, token):
                resumen.ya_asociado += 1
                continue
            items_filtrados.append(it)

        if not items_filtrados:
            return resumen

        # =========
        # 1) Scan de TIFFs (sin render)
        # =========
        scanned: List[Tuple[ProcesarItemIn, ScanOut]] = []
        all_refs: List[str] = []

        for it in items_filtrados:
            try:
                scan = self._tif.scan(it.full_path)
                scanned.append((it, scan))
                all_refs.extend(scan.headers or [])
            except Exception as e:
                resumen.errores.append(f"{it.file_name}: scan error: {e}")

        if not scanned:
            return resumen

        # =========
        # 2) Match masivo por referencias
        # =========
        match = self._match_all_refs(s, refs=all_refs)

        # =========
        # 3) Elegir 1 Archivo por TIFF (match por referencia)
        # =========
        work: List[Tuple[int, ScanOut, str, str]] = []  # (archivo_id, scan, tiff_path, file_name)

        for it, scan in scanned:
            refs = [self._norm_str(x) for x in (scan.headers or []) if self._norm_str(x)]

            if not refs:
                resumen.sin_match += 1
                continue

            # si alguna ref está duplicada, no sabemos cuál elegir => cuenta como duplicado
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

            work.append((archivo.archivo_id, scan, it.full_path, it.file_name))

        if not work:
            return resumen

        archivo_ids = [aid for aid, _, _, _ in work]

        # ✅ GARANTÍA: todos los Archivos de esta corrida quedan asignados a la recepción actual
        s.execute(
            update(Archivo)
            .where(Archivo.archivo_id.in_(archivo_ids))
            .values(recepcion_id=int(recepcion_id))
        )
        s.flush()

        # =========
        # 4) Cargar Archivos + Detalles (bulk)
        # =========
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

        # =========
        # 4.1) Buscar asociaciones vigentes por nro_referencia (bulk)
        # =========
        refs_set: Set[str] = set()
        for aid in archivo_ids:
            ar = archivo_by_id.get(aid)
            ref = self._norm_str(getattr(ar, "nro_referencia", None))
            if ref:
                refs_set.add(ref)

        vigente_por_ref: Dict[str, List[Tuple[int, int]]] = {}  # ref -> [(asociacion_id, receta_id)]
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
                if not ref:
                    continue
                vigente_por_ref.setdefault(ref, []).append((int(asoc_id), int(receta_id)))

        # =========
        # 5) Persistencia
        # =========
        troqueles_to_add: List[Troqueles] = []
        asoc_to_add: List[Asociacion] = []
        refs_desactivados: Set[str] = set()

        for archivo_id, scan, tiff_path, file_name in work:
            archivo = archivo_by_id.get(archivo_id)
            if not archivo:
                resumen.errores.append(f"{file_name}: archivo_id {archivo_id} no existe en DB")
                continue

            ref = self._norm_str(getattr(archivo, "nro_referencia", None))

            archivo_ts = self._archivo_ts(archivo)
            esta_vencido = self._esta_vencido(archivo_ts, fecha_presentacion)

            if getattr(archivo, "vencido", False) != esta_vencido:
                archivo.vencido = esta_vencido

            # 5.0) versionado por ref si había vigente
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

            # ✅ IMPORTANTE:
            # Si no hay troqueles detectados, NO es "sin_match" del archivo.
            # El match del archivo ya fue por referencia (Archivo <-> TIFF).
            estado_por_codebar: Dict[str, EstadoTroquelEnum] = {}
            enrich_por_codebar: Dict[str, TroquelEnrichment] = {}

            # 5.1) endpoint + estado (V/A/R) (solo si hay troqueles detectados)
            if counts:
                for codebar in counts.keys():
                    enr = enrich_cache.get(codebar)
                    if enr is None:
                        enr = self._enrich.enrich_by_codebar(codebar)
                        enrich_cache[codebar] = enr

                    enrich_por_codebar[codebar] = enr

                    # Amarillo si el endpoint dice A
                    if enr.estado == EstadoTroquelEnum.A:
                        estado_por_codebar[codebar] = EstadoTroquelEnum.A
                        continue

                    # Verde si code_alfabeta matchea con cod_medic, sino Rojo
                    ca = self._norm_str(enr.code_alfabeta)
                    estado_por_codebar[codebar] = (
                        EstadoTroquelEnum.V if (ca and ca in cods_detalle) else EstadoTroquelEnum.R
                    )

            # 5.2) render (usa SOLO detections del scan nuevo)
            try:
                estado_render: Dict[str, Literal["V", "A", "R"]] = {
                    k: cast(Literal["V", "A", "R"], v.value) for k, v in estado_por_codebar.items()
                }
                files = self._tif.render(
                    tiff_path=tiff_path,
                    scan=scan,
                    output_dir=output_dir,
                    estado_por_codebar=estado_render,  # puede ser {}
                )
            except Exception as e:
                resumen.errores.append(f"{file_name}: render error: {e}")
                files = {"front_jpg": None, "back_jpg": None}

            frente_jpg = files.get("front_jpg")
            dorso_jpg = files.get("back_jpg")

            # 5.3) crear Receta NUEVA (vigente) en la recepción actual
            nro_receta = self._norm_str(getattr(archivo, "nro_receta", None)) or "-"
            creado_en = self._scan_dt_from_name(frente_jpg) if frente_jpg else None

            receta = Recetas(
                recepcion_id=int(recepcion_id),
                nro_receta=nro_receta,
                ubicacion_frente=frente_jpg,
                ubicacion_dorso=dorso_jpg,
                fecha_prescripcion=None,
                observacion=None,
                usuario_id=usuario_id,
                estado_receta_id=2,
                creado_en=creado_en,
                vigente=True,
            )
            s.add(receta)
            s.flush()  # receta_id

            # 5.4) asociar (vigente)
            asoc_to_add.append(
                Asociacion(
                    receta_id=receta.receta_id,
                    archivo_id=archivo_id,
                    vigente=True,
                )
            )

            debitos_to_add: List[Debitos] = []
            if esta_vencido:
                # evitar duplicado si el proceso corre dos veces
                exists = (
                    s.execute(
                        select(Debitos.debito_id).where(
                            Debitos.receta_id == receta.receta_id,
                            Debitos.motivo_debito_id == MOTIVO_DEBITO_VENCIDO_60_ID,
                        ).limit(1)
                    ).scalar_one_or_none()
                )
                if exists is None:
                    debitos_to_add.append(
                        Debitos(
                            receta_id=receta.receta_id,
                            motivo_debito_id=MOTIVO_DEBITO_VENCIDO_60_ID,
                            detalle="Vencido por 60 días (auto)",
                        )
                    )

            # 5.5) crear troqueles (solo si hubo detección)
            if counts:
                for codebar, qty in counts.items():
                    enr = enrich_por_codebar[codebar]
                    estado = estado_por_codebar.get(codebar, EstadoTroquelEnum.A)

                    # monto SOLO si estado es VERDE
                    monto = 0.0
                    if estado == EstadoTroquelEnum.V:
                        ca = self._norm_str(enr.code_alfabeta)
                        monto = float(importe_por_cod.get(ca, 0.0)) if ca else 0.0

                    troqueles_to_add.append(
                        Troqueles(
                            receta_id=receta.receta_id,
                            codigo_barra=codebar,
                            droga=enr.droga_concat,
                            presentacion=enr.presentacion,
                            code_alfabeta=int(enr.code_alfabeta or 0),
                            monto=monto,
                            cantidad=qty,
                            estado=estado,
                        )
                    )

            if debitos_to_add:
                s.add_all(debitos_to_add)

            resumen.ok += 1

        if asoc_to_add:
            s.add_all(asoc_to_add)
        if troqueles_to_add:
            s.add_all(troqueles_to_add)

        return resumen