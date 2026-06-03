from __future__ import annotations

from typing import Callable, List, Optional
import os

from core.process_tif import TiffProcessor
from app.service.integraciones.medicamento_client import MedicamentoClient
from app.service.recetas.tif_context import (
    filter_unprocessed_items,
    load_run_cache,
    load_run_context,
    update_archivos_vencido,
)
from app.service.recetas.tif_workflow import (
    ChunkRuntime,
    process_items_in_chunks,
    process_items_individual_async,
)
from app.service.recetas.tif_types import (
    ProcesarItemIn,
    ProcesarResumen,
)


class TiffService:
    def __init__(
        self,
        *,
        tif: Optional[TiffProcessor] = None,
        client: Optional[MedicamentoClient] = None,
        chunk_size: int = 20,
        scan_workers: Optional[int] = None,
        upload_workers: int = 1,
        chunk_pause_ms: int = 0,
        upload_pause_ms: int = 0,
        pipeline_mode: str = "item",
    ) -> None:
        self._tif = tif or TiffProcessor()
        self._client = client or MedicamentoClient()

        cpu = os.cpu_count() or 4
        self._chunk_size = max(10, min(40, int(chunk_size)))
        self._scan_workers = max(1, min(3, int(scan_workers or min(cpu, 2))))
        self._upload_workers = max(1, min(1, int(upload_workers)))
        self._chunk_pause_ms = max(0, min(250, int(chunk_pause_ms)))
        self._upload_pause_ms = max(0, min(500, int(upload_pause_ms)))
        mode = str(pipeline_mode or "").strip().lower()
        self._pipeline_mode = mode if mode in {"chunk", "item"} else "chunk"

    # -------------------------
    # MAIN (por tandas)
    # -------------------------
    def procesar(
        self,
        recepcion_id: int,
        usuario_id: int,
        items: List[ProcesarItemIn],
        progress_cb: Callable[[int, int, float, str], None] | None = None,
    ) -> ProcesarResumen:

        total = ProcesarResumen()
        run_ctx = load_run_context(recepcion_id=int(recepcion_id))
        run_cache = load_run_cache(recepcion_id=int(recepcion_id))
        items_filtrados, ya_asociado = filter_unprocessed_items(
            items=items,
            run_cache=run_cache,
        )
        total.ya_asociado += ya_asociado

        if not items_filtrados:
            return total

        runtime = ChunkRuntime(
            tif=self._tif,
            client=self._client,
            scan_workers=self._scan_workers,
            upload_workers=self._upload_workers,
            upload_pause_ms=self._upload_pause_ms,
        )

        if self._pipeline_mode == "item":
            processed = process_items_individual_async(
                items_filtrados=items_filtrados,
                run_ctx=run_ctx,
                run_cache=run_cache,
                usuario_id=usuario_id,
                runtime=runtime,
                on_chunk_processed=progress_cb,
                chunk_pause_ms=self._chunk_pause_ms,
            )
        else:
            processed = process_items_in_chunks(
                items_filtrados=items_filtrados,
                run_ctx=run_ctx,
                run_cache=run_cache,
                usuario_id=usuario_id,
                chunk_size=self._chunk_size,
                runtime=runtime,
                on_chunk_processed=progress_cb,
                chunk_pause_ms=self._chunk_pause_ms,
            )

        total.merge(processed)

        update_archivos_vencido(estados_by_archivo_id=run_cache.vencido_updates)

        return total
