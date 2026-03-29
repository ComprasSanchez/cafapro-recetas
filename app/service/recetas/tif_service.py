from __future__ import annotations

from typing import Dict, List, Optional, Set, Iterable
import os

from sqlalchemy.orm import Session

from app.adapters.sqlalchemy.tif_repository import TifRepository
from core.process_tif import TiffProcessor
from app.db.models import (
    Archivo,
)
from app.infra.s3_storage import S3Storage
from app.service.integraciones.medicamento_client import MedicamentoClient
from app.dto.medicamentos_dto import MedicamentoDTO
from app.service.recetas.tif_context import filter_unprocessed_items, load_run_context
from app.service.recetas.tif_logic import (
    match_all_refs,
    warm_medicamento_cache,
)
from app.service.recetas.tif_parallel import parallel_render_upload, parallel_scan
from app.service.recetas.tif_persistence import filter_valid_uploaded, persist_uploaded_chunk
from app.service.recetas.tif_workflow import precompute_render_context, select_work_items
from app.service.recetas.tif_types import (
    ProcesarItemIn,
    ProcesarResumen,
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

        run_ctx = load_run_context(s, recepcion_id=int(recepcion_id))
        items_filtrados, ya_asociado = filter_unprocessed_items(
            s,
            recepcion_id=int(recepcion_id),
            items=items,
        )
        total.ya_asociado += ya_asociado

        if not items_filtrados:
            return total

        # 2) Procesar por tandas
        for chunk in _chunks(items_filtrados, self._chunk_size):

            resumen = ProcesarResumen()

            # 2.1) scan paralelo (solo ScanOut)
            scanned = parallel_scan(
                tif=self._tif,
                items=chunk,
                scan_workers=self._scan_workers,
                resumen=resumen,
            )
            if not scanned:
                total.merge(resumen)
                continue

            # 2.2) juntar refs y match masivo (DB)
            all_refs: List[str] = []
            for x in scanned:
                all_refs.extend(x.scan.headers or [])
            match = match_all_refs(
                s,
                recepcion_id=run_ctx.recepcion_id,
                refs=all_refs,
                only_referencia=run_ctx.only_ref_match,
            )

            # 2.3) elegir work (archivo_id por tiff)
            selection = select_work_items(
                scanned=scanned,
                match=match,
                only_ref_match=run_ctx.only_ref_match,
                seen_recetas=seen_recetas,
                seen_refs=seen_refs,
                resumen=resumen,
                is_archivo_ya_asociado=lambda archivo_id: TifRepository.is_archivo_ya_asociado(
                    s,
                    recepcion_id=run_ctx.recepcion_id,
                    archivo_id=archivo_id,
                ),
            )

            work = selection.work
            archivo_ids = selection.archivo_ids
            revision_items = selection.revision_items
            headers_render_by_work_id = selection.headers_render_by_work_id

            if not work and not revision_items:
                total.merge(resumen)
                continue

            # 2.4) bulk load Archivos + Detalles
            archivo_by_id, detalles_by_archivo = TifRepository.load_archivo_bundle(
                s,
                archivo_ids=archivo_ids,
            )

            precomputed = precompute_render_context(
                work=work,
                revision_items=revision_items,
                headers_render_by_work_id=headers_render_by_work_id,
                archivo_by_id=archivo_by_id,
                detalles_by_archivo=detalles_by_archivo,
                fecha_presentacion_dt=run_ctx.fecha_presentacion_dt,
                dias_vencimiento=run_ctx.dias_vencimiento,
                med_cache=med_cache,
                warm_cache=lambda codebars: warm_medicamento_cache(self._client, med_cache, codebars),
                resumen=resumen,
            )

            revision_work = precomputed.revision_work
            estado_render_by_archivo_id = precomputed.estado_render_by_archivo_id
            troquel_evals_by_archivo_id = precomputed.troquel_evals_by_archivo_id
            troquel_evals_by_work_id = precomputed.troquel_evals_by_work_id

            # 2.7) render+upload en paralelo (usa scan + estado_render)
            uploaded = parallel_render_upload(
                storage=self._storage,
                tif=self._tif,
                work_items=work + revision_work,
                archivo_by_id=archivo_by_id,
                prestador_imed=run_ctx.prestador_imed,
                estado_render_by_work=estado_render_by_archivo_id,
                headers_render_by_work_id=headers_render_by_work_id,
                upload_workers=self._upload_workers,
                resumen=resumen,
            )

            # 2.8) persistencia DB (bulk, 1 flush)
            valid_uploaded = filter_valid_uploaded(uploaded, resumen)
            if not valid_uploaded:
                total.merge(resumen)
                continue

            resumen.ok += persist_uploaded_chunk(
                s,
                recepcion_id=run_ctx.recepcion_id,
                usuario_id=int(usuario_id),
                valid_uploaded=valid_uploaded,
                archivo_by_id=archivo_by_id,
                troquel_evals_by_work_id=troquel_evals_by_work_id,
                troquel_evals_by_archivo_id=troquel_evals_by_archivo_id,
                dias_vencimiento=run_ctx.dias_vencimiento,
                motivo_debito_receta_vencida_id=run_ctx.motivo_debito_receta_vencida_id,
                revision_counter=revision_counter,
            )

            total.merge(resumen)

        return total
