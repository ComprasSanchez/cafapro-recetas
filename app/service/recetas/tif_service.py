from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set, Literal, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.process_tif import TiffProcessor, ScanOut
from app.db.models import (
    Archivo,
    ArchivoDetalle,
    Recetas,
    Asociacion,
    Troqueles,
    EstadoTroquelEnum,
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

    def __post_init__(self):
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
    ):
        self._tif = tif or TiffProcessor()
        self._enrich = troquel_enrich or TroquelEnrichmentService()

    @staticmethod
    def _scan_dt_from_name(path: str) -> datetime:
        name = Path(path).stem  # "pami_20260127121247004_f"
        ts = name.split("_")[1]  # "20260127121247004"
        dt = datetime.strptime(ts[:14], "%Y%m%d%H%M%S")
        ms = int(ts[14:17])
        return dt.replace(microsecond=ms * 1000)

    @staticmethod
    def _norm_str(x) -> str:
        return str(x).strip() if x is not None else ""

    @staticmethod
    def _match_all_refs(s: Session, refs: List[str]) -> _MatchResult:
        """
        Match masivo:
        - ref_to_archivo[ref] = Archivo si ref es único
        - ref_to_archivo[ref] = None si falta o es duplicado
        """
        refs_norm = [str(r).strip() for r in refs if r and str(r).strip()]
        refs_set = set(refs_norm)
        if not refs_set:
            return _MatchResult(ref_to_archivo={}, duplicated_refs=set(), missing_refs=set())

        rows = (
            s.execute(select(Archivo).where(Archivo.nro_referencia.in_(list(refs_set))))
            .scalars()
            .all()
        )

        by_ref: Dict[str, List[Archivo]] = {}
        for a in rows:
            by_ref.setdefault(str(a.nro_referencia).strip(), []).append(a)

        duplicated = {ref for ref, arr in by_ref.items() if len(arr) > 1}
        missing = {ref for ref in refs_set if ref not in by_ref}

        ref_to_archivo: Dict[str, Optional[Archivo]] = {}
        for ref in refs_set:
            if ref in duplicated:
                ref_to_archivo[ref] = None
            elif ref in by_ref:
                ref_to_archivo[ref] = by_ref[ref][0]
            else:
                ref_to_archivo[ref] = None

        return _MatchResult(
            ref_to_archivo=ref_to_archivo,
            duplicated_refs=duplicated,
            missing_refs=missing,
        )

    def procesar(
        self,
        s: Session,
        recepcion_id: int,
        usuario_id: int,  # Recetas.usuario_id es NOT NULL
        items: List[ProcesarItemIn],
        output_dir: str,
    ) -> ProcesarResumen:
        resumen = ProcesarResumen()

        # cache por corrida: codebar -> enrichment
        enrich_cache: Dict[str, TroquelEnrichment] = {}

        # =========
        # 1) Scan de TIFFs (sin render)
        # =========
        scanned: List[Tuple[ProcesarItemIn, ScanOut]] = []
        all_refs: List[str] = []

        for it in items:
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
        match = self._match_all_refs(s, all_refs)

        # =========
        # 3) Elegir 1 Archivo por TIFF
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

            # asignar recepcion si cambia
            if archivo.recepcion_id != recepcion_id:
                archivo.recepcion_id = recepcion_id

            work.append((archivo.archivo_id, scan, it.full_path, it.file_name))

        if not work:
            return resumen

        archivo_ids = [aid for aid, _, _, _ in work]

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
        # 4.1) Detectar ya asociados (bulk)
        # =========
        asociados_archivo_ids = set(
            s.execute(
                select(Asociacion.archivo_id).where(Asociacion.archivo_id.in_(archivo_ids))
            )
            .scalars()
            .all()
        )

        # =========
        # 5) Persistencia
        # =========
        troqueles_to_add: List[Troqueles] = []
        asoc_to_add: List[Asociacion] = []

        for archivo_id, scan, tiff_path, file_name in work:
            if archivo_id in asociados_archivo_ids:
                resumen.ya_asociado += 1
                continue

            archivo = archivo_by_id.get(archivo_id)
            if not archivo:
                resumen.errores.append(f"{file_name}: archivo_id {archivo_id} no existe en DB")
                continue

            dets = detalles_by_archivo.get(archivo_id, [])

            # -------------------------
            # OPTIMIZACIÓN 1:
            # - armamos una sola vez:
            #   - cods_detalle (para match)
            #   - importe_por_cod (para monto)
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
            # OPTIMIZACIÓN 2:
            # - una sola pasada por scan.troqueles:
            #   counts y de ahí keys = codebars
            # -------------------------
            counts: Dict[str, int] = {}
            for cod in (scan.troqueles or []):
                cod = self._norm_str(cod)
                if not cod:
                    continue
                counts[cod] = counts.get(cod, 0) + 1

            if not counts:
                resumen.sin_match += 1
                continue

            estado_por_codebar: Dict[str, EstadoTroquelEnum] = {}
            enrich_por_codebar: Dict[str, TroquelEnrichment] = {}

            # 5.1) endpoint + estado (V/A/R)
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
                estado_por_codebar[codebar] = EstadoTroquelEnum.V if (ca and ca in cods_detalle) else EstadoTroquelEnum.R

            # 5.2) render (tu render espera dict[str, Literal["V","A","R"]])
            try:
                estado_render: Dict[str, Literal["V", "A", "R"]] = {
                    k: cast(Literal["V", "A", "R"], v.value) for k, v in estado_por_codebar.items()
                }
                files = self._tif.render(
                    tiff_path=tiff_path,
                    scan=scan,
                    output_dir=output_dir,
                    estado_por_codebar=estado_render,
                )
            except Exception as e:
                resumen.errores.append(f"{file_name}: render error: {e}")
                files = {"front_jpg": None, "back_jpg": None}

            frente_jpg = files.get("front_jpg")
            dorso_jpg = files.get("back_jpg")

            # 5.3) crear Receta (SIN UPSERT)
            nro_receta = self._norm_str(archivo.nro_receta) or "-"
            receta = Recetas(
                recepcion_id=recepcion_id,
                nro_receta=nro_receta,
                ubicacion_frente=frente_jpg,
                ubicacion_dorso=dorso_jpg,
                fecha_prescripcion=None,
                observacion=None,
                usuario_id=usuario_id,
                estado_receta_id=2,
                creado_en=self._scan_dt_from_name(frente_jpg),
            )
            s.add(receta)
            s.flush()  # receta_id

            # 5.4) asociar
            asoc_to_add.append(Asociacion(receta_id=receta.receta_id, archivo_id=archivo_id))

            # 5.5) crear troqueles (1 fila por receta+codebar)
            for codebar, qty in counts.items():
                enr = enrich_por_codebar[codebar]
                estado = estado_por_codebar.get(codebar, EstadoTroquelEnum.A)

                # ✅ monto SOLO si estado es VERDE (EstadoTroquelEnum.V)
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
                        monto=monto,  # ✅ Numeric: pasamos float
                        cantidad=qty,
                        estado=estado,  # Enum V/A/R
                    )
                )

            resumen.ok += 1

        if asoc_to_add:
            s.add_all(asoc_to_add)
        if troqueles_to_add:
            s.add_all(troqueles_to_add)

        return resumen
