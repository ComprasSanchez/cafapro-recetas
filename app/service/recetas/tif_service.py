from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Set, Literal, Iterable
import os

from sqlalchemy.orm import Session

from app.adapters.sqlalchemy.tif_repository import TifRepository
from core.process_tif import TiffProcessor
from app.db.models import (
    Archivo,
    ArchivoDetalle,
    Recetas,
    Asociacion,
    Troqueles,
    EstadoTroquelEnum,
    Debitos,
)
from app.infra.s3_storage import S3Storage
from app.service.integraciones.medicamento_client import MedicamentoClient
from app.dto.medicamentos_dto import MedicamentoDTO
from app.service.recetas.tif_logic import (
    archivo_ts,
    base_from_tif_path,
    build_detalle_context,
    esta_vencido,
    evaluate_revision_troqueles,
    evaluate_troqueles,
    is_valesalud,
    match_all_refs,
    norm_str,
    to_render_states,
    warm_medicamento_cache,
)
from app.service.recetas.tif_parallel import parallel_render_upload, parallel_scan
from app.service.recetas.tif_types import (
    ProcesarItemIn,
    ProcesarResumen,
    _DetalleContext,
    _MatchResult,
    _ScannedItem,
    _TroquelEval,
    _UploadResult,
    _WorkItem,
)


# -------------------------
# Helpers
# -------------------------
def _chunks(lst: List, size: int) -> Iterable[List]:
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


class TiffService:
    def __init__(
        self,
        *,
        storage: S3Storage,
        tif: Optional[TiffProcessor] = None,
        client: Optional[MedicamentoClient] = None,
        chunk_size: int = 75,
        scan_workers: Optional[int] = None,
        upload_workers: int = 32,
    ) -> None:
        self._storage = storage
        self._tif = tif or TiffProcessor()
        self._client = client or MedicamentoClient()

        cpu = os.cpu_count() or 4
        self._chunk_size = int(chunk_size)
        self._scan_workers = int(scan_workers or min(cpu, 6))
        self._upload_workers = int(upload_workers)

    # -------------------------
    # Helpers (idénticos a los tuyos)
    # -------------------------
    @staticmethod
    def _norm_str(x) -> str:
        return norm_str(x)

    @staticmethod
    def _exists_processed_base_in_recepcion(s: Session, recepcion_id: int, base_name: str) -> bool:
        return TifRepository.exists_processed_base_in_recepcion(
            s,
            recepcion_id=int(recepcion_id),
            base_name=base_name,
        )

    @staticmethod
    def _archivo_ts(a: Archivo) -> datetime:
        return archivo_ts(a)

    @staticmethod
    def _esta_vencido(archivo_ts: datetime, fecha_presentacion: datetime, dias_vencimiento: int | None) -> bool:
        return esta_vencido(archivo_ts, fecha_presentacion, dias_vencimiento)

    @staticmethod
    def _base_from_tif_path(full_path: str) -> str:
        return base_from_tif_path(full_path)

    @staticmethod
    def _match_all_refs(
        s: Session,
        recepcion_id: int,
        refs: List[str],
        *,
        only_referencia: bool = False,
    ) -> _MatchResult:
        return match_all_refs(
            s,
            recepcion_id=int(recepcion_id),
            refs=refs,
            only_referencia=only_referencia,
        )

    def _warm_medicamento_cache(
        self,
        med_cache: Dict[str, Optional[MedicamentoDTO]],
        codebars: Set[str],
    ) -> None:
        warm_medicamento_cache(
            self._client,
            med_cache,
            codebars,
        )

    @staticmethod
    def _build_detalle_context(dets: List[ArchivoDetalle]) -> _DetalleContext:
        return build_detalle_context(dets)

    @staticmethod
    def _evaluate_troqueles(
        scan_troqueles: List[str],
        detalle: _DetalleContext,
        med_cache: Dict[str, Optional[MedicamentoDTO]],
    ) -> List[_TroquelEval]:
        return evaluate_troqueles(
            scan_troqueles=scan_troqueles,
            detalle=detalle,
            med_cache=med_cache,
        )

    @staticmethod
    def _evaluate_revision_troqueles(
        scan_troqueles: List[str],
        med_cache: Dict[str, Optional[MedicamentoDTO]],
    ) -> List[_TroquelEval]:
        return evaluate_revision_troqueles(
            scan_troqueles=scan_troqueles,
            med_cache=med_cache,
        )

    @staticmethod
    def _to_render_states(evals: List[_TroquelEval]) -> Dict[str, Literal["V", "A", "R"]]:
        return to_render_states(evals)

    # -------------------------
    # Paralelos
    # -------------------------
    def _parallel_scan(self, items: List[ProcesarItemIn], resumen: ProcesarResumen) -> List[_ScannedItem]:
        return parallel_scan(
            tif=self._tif,
            items=items,
            scan_workers=self._scan_workers,
            resumen=resumen,
        )

    def _parallel_render_upload(
            self,
            work_items: List[_WorkItem],
            *,
            archivo_by_id: Dict[int, Archivo],
            prestador_imed: str,
            estado_render_by_work: Dict[int, Dict[str, Literal["V", "A", "R"]]],
            headers_render_by_work_id: Dict[int, Set[str]],
            resumen: ProcesarResumen,
    ) -> List[_UploadResult]:
        return parallel_render_upload(
            storage=self._storage,
            tif=self._tif,
            work_items=work_items,
            archivo_by_id=archivo_by_id,
            prestador_imed=prestador_imed,
            estado_render_by_work=estado_render_by_work,
            headers_render_by_work_id=headers_render_by_work_id,
            upload_workers=self._upload_workers,
            resumen=resumen,
        )

    @staticmethod
    def _archivo_ya_asociado(s: Session, recepcion_id: int, archivo_id: int) -> bool:
        return TifRepository.is_archivo_ya_asociado(
            s,
            recepcion_id=int(recepcion_id),
            archivo_id=int(archivo_id),
        )

    @staticmethod
    def _is_valesalud(obra_social_nombre: str | None) -> bool:
        return is_valesalud(obra_social_nombre)

    # -------------------------
    # MAIN (por tandas)
    # -------------------------
    def procesar(
        self,
        s: Session,
        recepcion_id: int,
        usuario_id: int,
        items: List[ProcesarItemIn],
    ) -> ProcesarResumen:

        total = ProcesarResumen()
        med_cache: Dict[str, Optional[MedicamentoDTO]] = {}
        seen_recetas: Set[str] = set()
        seen_refs: Set[str] = set()

        revision_counter = 1

        # 0) recepcion + prestador.imed
        rec = TifRepository.get_recepcion(s, recepcion_id=int(recepcion_id))
        if not rec:
            raise RuntimeError(f"No existe la recepción {recepcion_id}")

        pr_row = TifRepository.get_prestador(s, prestador_id=int(rec.prestador_id))
        if not pr_row:
            raise RuntimeError("No existe el Prestador asociado a la recepción.")

        prestador_imed = (getattr(pr_row, "imed", "") or "").strip()
        if not prestador_imed:
            raise RuntimeError("Prestador.imed está vacío; no se puede armar key S3.")

        fecha_presentacion = rec.fecha_presentacion
        if isinstance(fecha_presentacion, datetime):
            fecha_presentacion_dt = fecha_presentacion
        else:
            fecha_presentacion_dt = datetime.fromisoformat(str(fecha_presentacion))
        os_row = TifRepository.get_obra_social_context(s, obra_social_id=int(rec.obra_social_id))
        os_nombre = (os_row[0] if os_row else None)
        dias_vencimiento_raw = (os_row[1] if os_row else None)
        dias_vencimiento = int(dias_vencimiento_raw) if dias_vencimiento_raw is not None else None
        only_ref_match = self._is_valesalud(os_nombre)
        MOTIVO_DEBITO_RECETA_VENCIDA_ID = 11

        # 1) Idempotencia (se mantiene)
        items_filtrados: List[ProcesarItemIn] = []
        for it in items:
            base_name = self._base_from_tif_path(it.full_path)
            if base_name and self._exists_processed_base_in_recepcion(s, recepcion_id, base_name):
                total.ya_asociado += 1
                continue
            items_filtrados.append(it)

        if not items_filtrados:
            return total

        # 2) Procesar por tandas
        for chunk in _chunks(items_filtrados, self._chunk_size):

            resumen = ProcesarResumen()

            # 2.1) scan paralelo (solo ScanOut)
            scanned = self._parallel_scan(chunk, resumen)
            if not scanned:
                total.merge(resumen)
                continue

            # 2.2) juntar refs y match masivo (DB)
            all_refs: List[str] = []
            for x in scanned:
                all_refs.extend(x.scan.headers or [])
            match = self._match_all_refs(
                s,
                recepcion_id,
                all_refs,
                only_referencia=only_ref_match,
            )

            # 2.3) elegir work (archivo_id por tiff)
            work: List[_WorkItem] = []
            archivo_ids: List[int] = []
            revision_items: List[_ScannedItem] = []
            headers_render_by_work_id: Dict[int, Set[str]] = {}

            for x in scanned:
                refs = [self._norm_str(r) for r in (x.scan.headers or []) if self._norm_str(r)]

                if not refs:
                    resumen.sin_match += 1
                    revision_items.append(x)
                    continue

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
                    revision_items.append(x)
                    continue

                if self._archivo_ya_asociado(s, recepcion_id, archivo.archivo_id):
                    revision_items.append(x)
                    continue

                nro_rec = self._norm_str(getattr(archivo, "nro_receta", None))
                nro_ref = self._norm_str(getattr(archivo, "nro_referencia", None))

                # 🔥 duplicado en esta corrida
                if only_ref_match:
                    if nro_ref and nro_ref in seen_refs:
                        revision_items.append(x)
                        continue
                else:
                    if (nro_rec and nro_rec in seen_recetas) or (nro_ref and nro_ref in seen_refs):
                        revision_items.append(x)
                        continue

                # marcar como vistos
                if not only_ref_match and nro_rec:
                    seen_recetas.add(nro_rec)

                if nro_ref:
                    seen_refs.add(nro_ref)

                matched_refs_for_archivo: Set[str] = set()
                for ref in refs:
                    a = match.ref_to_archivo.get(ref)
                    if a is None:
                        continue
                    if int(a.archivo_id) == int(archivo.archivo_id):
                        matched_refs_for_archivo.add(ref)

                w_item = _WorkItem(it=x.it, scan=x.scan, archivo_id=int(archivo.archivo_id))
                work.append(w_item)
                headers_render_by_work_id[id(w_item)] = matched_refs_for_archivo
                archivo_ids.append(int(archivo.archivo_id))

            if not work and not revision_items:
                total.merge(resumen)
                continue

            # 2.4) bulk load Archivos + Detalles
            archivos = TifRepository.get_archivos_by_ids(
                s,
                archivo_ids=archivo_ids,
            )
            archivo_by_id: Dict[int, Archivo] = {a.archivo_id: a for a in archivos}

            detalles = TifRepository.get_detalles_by_archivo_ids(
                s,
                archivo_ids=archivo_ids,
            )
            detalles_by_archivo: Dict[int, List[ArchivoDetalle]] = {}
            for d in detalles:
                detalles_by_archivo.setdefault(d.archivo_id, []).append(d)

            # 2.6) precomputar estados + troqueles + vencido (SIN render ni S3 todavía)
            estado_render_by_archivo_id: Dict[int, Dict[str, Literal["V","A","R"]]] = {}
            troquel_evals_by_archivo_id: Dict[int, List[_TroquelEval]] = {}
            troquel_evals_by_work_id: Dict[int, List[_TroquelEval]] = {}

            revision_work: List[_WorkItem] = []
            for x in revision_items:
                w_item = _WorkItem(
                    it=x.it,
                    scan=x.scan,
                    archivo_id=0,
                )
                revision_work.append(w_item)
                headers_render_by_work_id[id(w_item)] = set()

            all_codebars: set[str] = set()

            for w in work:
                for cb in (w.scan.troqueles or []):
                    cb = self._norm_str(cb)
                    if cb:
                        all_codebars.add(cb)

            for w in revision_work:
                for cb in (w.scan.troqueles or []):
                    cb = self._norm_str(cb)
                    if cb:
                        all_codebars.add(cb)

            self._warm_medicamento_cache(med_cache, all_codebars)

            # además juntamos data para persistencia después del upload
            recetas_to_add: List[Recetas] = []
            asoc_to_add: List[Asociacion] = []
            troqueles_to_add: List[Troqueles] = []

            # OJO: acá todavía no creamos recetas; primero subimos S3.
            # Pero para render necesitamos el estado_render_por_codebar, lo armamos por archivo_id.
            for w in work:
                archivo = archivo_by_id.get(w.archivo_id)
                if not archivo:
                    resumen.errores.append(f"{w.it.file_name}: archivo_id {w.archivo_id} no existe en DB")
                    continue

                archivo_ts = self._archivo_ts(archivo)
                esta_vencido = self._esta_vencido(archivo_ts, fecha_presentacion_dt, dias_vencimiento)
                if getattr(archivo, "vencido", False) != esta_vencido:
                    archivo.vencido = esta_vencido

                dets = detalles_by_archivo.get(w.archivo_id, [])
                detalle_ctx = self._build_detalle_context(dets)

                evals = self._evaluate_troqueles(
                    scan_troqueles=(w.scan.troqueles or []),
                    detalle=detalle_ctx,
                    med_cache=med_cache,
                )

                troquel_evals_by_archivo_id[w.archivo_id] = evals
                troquel_evals_by_work_id[id(w)] = evals
                estado_render_by_archivo_id[w.archivo_id] = self._to_render_states(evals)

            for w in revision_work:
                evals = self._evaluate_revision_troqueles(
                    scan_troqueles=(w.scan.troqueles or []),
                    med_cache=med_cache,
                )
                troquel_evals_by_work_id[id(w)] = evals

            # 2.7) render+upload en paralelo (usa scan + estado_render)
            uploaded = self._parallel_render_upload(
                work_items=work + revision_work,
                archivo_by_id=archivo_by_id,
                prestador_imed=prestador_imed,
                estado_render_by_work=estado_render_by_archivo_id,
                headers_render_by_work_id=headers_render_by_work_id,
                resumen=resumen,
            )

            # 2.8) persistencia DB (bulk, 1 flush)
            # armamos recetas SOLO para los que realmente subieron algo
            valid_uploaded: List[_UploadResult] = []
            for u in uploaded:
                if not u.front_key and not u.back_key:
                    resumen.errores.append(f"{u.work.it.file_name}: no se subió frente ni dorso")
                    continue
                valid_uploaded.append(u)

            if not valid_uploaded:
                total.merge(resumen)
                continue

            # crear recetas en memoria
            receta_by_archivo_id: Dict[int, Recetas] = {}
            receta_by_work_id: Dict[int, Recetas] = {}
            for u in valid_uploaded:

                if u.work.archivo_id == 0:
                    nro_receta = "-"

                    receta = Recetas(
                        recepcion_id=int(recepcion_id),
                        nro_receta=nro_receta,
                        ubicacion_frente=u.front_key,
                        ubicacion_dorso=u.back_key,
                        fecha_prescripcion=None,
                        observacion=None,
                        usuario_id=usuario_id,
                        estado_receta_id=3,
                        creado_en=datetime.now(),
                        vigente=True,
                    )

                    recetas_to_add.append(receta)
                    receta_by_work_id[id(u.work)] = receta
                    continue

                archivo = archivo_by_id[u.work.archivo_id]
                nro_receta = self._norm_str(getattr(archivo, "nro_receta", None)) or f"REV-{revision_counter}"

                receta = Recetas(
                    recepcion_id=int(recepcion_id),
                    nro_receta=nro_receta,
                    ubicacion_frente=u.front_key,
                    ubicacion_dorso=u.back_key,
                    fecha_prescripcion=None,
                    observacion=None,
                    usuario_id=usuario_id,
                    estado_receta_id=2,
                    creado_en=datetime.now(),
                    vigente=True,
                )
                recetas_to_add.append(receta)
                receta_by_archivo_id[u.work.archivo_id] = receta
                receta_by_work_id[id(u.work)] = receta

            s.add_all(recetas_to_add)
            s.flush()  # 1 flush por tanda

            # asociaciones + troqueles + debitos vencido
            recetas_vencidas_ids: List[int] = []

            for u in valid_uploaded:
                w = u.work

                if w.archivo_id == 0:
                    receta = receta_by_work_id.get(id(w))
                    if receta is None:
                        continue

                    evals = troquel_evals_by_work_id.get(id(w), [])
                    for e in evals:
                        troqueles_to_add.append(
                            Troqueles(
                                receta_id=receta.receta_id,
                                codigo_barra=e.codebar,
                                droga=e.droga_concat,
                                presentacion=e.presentacion,
                                code_alfabeta=e.code_alfabeta,
                                monto=e.monto,
                                cantidad=e.cantidad_scan,
                                estado=EstadoTroquelEnum.A,
                            )
                        )
                    continue

                archivo = archivo_by_id[w.archivo_id]
                receta = receta_by_archivo_id[w.archivo_id]

                # asociacion
                asoc_to_add.append(Asociacion(receta_id=receta.receta_id, archivo_id=w.archivo_id, vigente=True))

                # vencido
                esta_vencido = bool(getattr(archivo, "vencido", False))
                if esta_vencido:
                    recetas_vencidas_ids.append(int(receta.receta_id))

                evals = troquel_evals_by_work_id.get(id(w), troquel_evals_by_archivo_id.get(w.archivo_id, []))
                for e in evals:
                    troqueles_to_add.append(
                        Troqueles(
                            receta_id=receta.receta_id,
                            codigo_barra=e.codebar,
                            droga=e.droga_concat,
                            presentacion=e.presentacion,
                            code_alfabeta=e.code_alfabeta,
                            monto=e.monto,
                            cantidad=e.cantidad_scan,
                            estado=e.estado,
                        )
                    )

            if asoc_to_add:
                s.add_all(asoc_to_add)
            if troqueles_to_add:
                s.add_all(troqueles_to_add)


            # Debitos vencido bulk
            if recetas_vencidas_ids:
                ya_tienen = TifRepository.get_recetas_with_motivo(
                    s,
                    receta_ids=recetas_vencidas_ids,
                    motivo_id=MOTIVO_DEBITO_RECETA_VENCIDA_ID,
                )
                for rid in recetas_vencidas_ids:
                    if rid in ya_tienen:
                        continue
                    s.add(
                        Debitos(
                            receta_id=rid,
                            motivo_debito_id=MOTIVO_DEBITO_RECETA_VENCIDA_ID,
                            detalle=(
                                f"Vencido por {dias_vencimiento} dias (auto)"
                                if dias_vencimiento is not None
                                else "Vencido (auto)"
                            ),
                        )
                    )

            resumen.ok += len(valid_uploaded)

            total.merge(resumen)

        return total
