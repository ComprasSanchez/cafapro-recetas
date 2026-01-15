from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

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
from app.service.troquel_enrichment_service import TroquelEnrichmentService, TroquelEnrichment


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
    duplicated_refs: set[str]
    missing_refs: set[str]


class TiffService:
    def __init__(
        self,
        tif: Optional[TiffProcessor] = None,
        troquel_enrich: Optional[TroquelEnrichmentService] = None,
    ):
        self._tif = tif or TiffProcessor()
        self._enrich = troquel_enrich or TroquelEnrichmentService()

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

        return _MatchResult(ref_to_archivo=ref_to_archivo, duplicated_refs=duplicated, missing_refs=missing)

    def procesar(
        self,
        s: Session,
        recepcion_id: int,
        usuario_id: int,        # Recetas.usuario_id es NOT NULL
        items: List[ProcesarItemIn],
        output_dir: str,
    ) -> ProcesarResumen:
        resumen = ProcesarResumen()

        # cache de endpoint por corrida (codebar -> enrichment)
        enrich_cache: Dict[str, TroquelEnrichment] = {}

        # =========
        # 1) Scan de TIFFs (sin render)
        # =========
        scanned: list[tuple[ProcesarItemIn, ScanOut]] = []
        all_refs: list[str] = []

        for it in items:
            try:
                scan = self._tif.scan(it.full_path)
                scanned.append((it, scan))
                all_refs.extend(scan.headers)  # referencias
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
        work: list[tuple[int, ScanOut, str, str]] = []  # (archivo_id, scan, tiff_path, file_name)

        for it, scan in scanned:
            refs = [self._norm_str(x) for x in scan.headers if self._norm_str(x)]

            if not refs:
                resumen.sin_match += 1
                continue

            if any(ref in match.duplicated_refs for ref in refs):
                resumen.duplicados += 1
                continue

            archivo = None
            for ref in refs:
                archivo = match.ref_to_archivo.get(ref)
                if archivo is not None:
                    break

            if archivo is None:
                resumen.sin_match += 1
                continue

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
        # 5) Persistencia
        # =========
        troqueles_to_add: list[Troqueles] = []
        asoc_to_add: list[Asociacion] = []

        for archivo_id, scan, tiff_path, file_name in work:
            archivo = archivo_by_id.get(archivo_id)
            if not archivo:
                resumen.errores.append(f"{file_name}: archivo_id {archivo_id} no existe en DB")
                continue

            dets = detalles_by_archivo.get(archivo_id, [])

            # cod_medic es string, code_alfabeta es int => comparamos por string normalizado
            cods_detalle = {self._norm_str(d.cod_medic) for d in dets if self._norm_str(d.cod_medic)}
            codebars = {self._norm_str(c) for c in scan.troqueles if self._norm_str(c)}

            estado_por_codebar: Dict[str, str] = {}  # "V"/"A"/"R"
            enrich_por_codebar: Dict[str, TroquelEnrichment] = {}

            # 5.1) endpoint + estado
            for codebar in codebars:
                if codebar in enrich_cache:
                    enr = enrich_cache[codebar]
                else:
                    enr = self._enrich.enrich_by_codebar(codebar)
                    enrich_cache[codebar] = enr

                enrich_por_codebar[codebar] = enr

                if enr.estado == EstadoTroquelEnum.A:
                    estado_por_codebar[codebar] = "A"
                else:
                    ca = self._norm_str(enr.code_alfabeta)  # int -> str
                    estado_por_codebar[codebar] = "V" if (ca and ca in cods_detalle) else "R"

            # 5.2) render (dibuja por estado V/A/R)
            try:
                files = self._tif.render(
                    tiff_path=tiff_path,
                    scan=scan,
                    output_dir=output_dir,
                    estado_por_codebar=estado_por_codebar,
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
                estado_receta_id=2
            )
            s.add(receta)
            s.flush()  # receta_id

            # 5.4) asociar
            asoc_to_add.append(Asociacion(receta_id=receta.receta_id, archivo_id=archivo_id))

            # 5.5) contar troqueles (1 fila por receta+codebar)
            counts: Dict[str, int] = {}
            for cod in scan.troqueles:
                cod = self._norm_str(cod)
                if not cod:
                    continue
                counts[cod] = counts.get(cod, 0) + 1

            # 5.6) crear troqueles
            for codebar, qty in counts.items():
                enr = enrich_por_codebar.get(codebar) or enrich_cache.get(codebar) or self._enrich.enrich_by_codebar(codebar)
                estado = estado_por_codebar.get(codebar, "A")

                monto = 0
                if estado == "V":
                    ca = self._norm_str(enr.code_alfabeta)
                    monto = sum((d.importe_obs or 0) for d in dets if self._norm_str(d.cod_medic) == ca)

                troqueles_to_add.append(
                    Troqueles(
                        receta_id=receta.receta_id,
                        codigo_barra=codebar,
                        droga=enr.droga_concat,
                        presentacion=enr.presentacion,
                        code_alfabeta=int(enr.code_alfabeta or 0),
                        monto=monto,
                        cantidad=qty,
                        estado=EstadoTroquelEnum(estado),  # V/A/R
                    )
                )

            resumen.ok += 1

        if asoc_to_add:
            s.add_all(asoc_to_add)
        if troqueles_to_add:
            s.add_all(troqueles_to_add)

        return resumen
