from __future__ import annotations

from typing import Callable, List, Optional
import os

from sqlalchemy.orm import Session

from core.process_tif import TiffProcessor
from app.infra.s3_storage import S3Storage
from app.service.integraciones.medicamento_client import MedicamentoClient
from app.service.recetas.tif_context import filter_unprocessed_items, load_run_context
from app.service.recetas.tif_workflow import ChunkRuntime, process_items_in_chunks
from app.service.recetas.tif_types import (
    ProcesarItemIn,
    ProcesarResumen,
)


class TiffService:
    def __init__(
        self,
        *,
        storage: S3Storage,
        tif: Optional[TiffProcessor] = None,
        client: Optional[MedicamentoClient] = None,
        chunk_size: int = 20,
        scan_workers: Optional[int] = None,
        upload_workers: int = 1,
        chunk_pause_ms: int = 80,
        upload_pause_ms: int = 80,
    ) -> None:
        self._storage = storage
        self._tif = tif or TiffProcessor()
        self._client = client or MedicamentoClient()

        cpu = os.cpu_count() or 4
        self._chunk_size = max(10, min(40, int(chunk_size)))
        self._scan_workers = max(1, min(3, int(scan_workers or min(cpu, 1))))
        self._upload_workers = max(1, min(1, int(upload_workers)))
        self._chunk_pause_ms = max(0, min(500, int(chunk_pause_ms)))
        self._upload_pause_ms = max(0, min(500, int(upload_pause_ms)))

    # -------------------------
    # MAIN (por tandas)
    # -------------------------
    def procesar(
        self,
        s: Session,
        recepcion_id: int,
        usuario_id: int,
        items: List[ProcesarItemIn],
        progress_cb: Callable[[int, int, float], None] | None = None,
    ) -> ProcesarResumen:

        total = ProcesarResumen()
        run_ctx = load_run_context(s, recepcion_id=int(recepcion_id))
        items_filtrados, ya_asociado = filter_unprocessed_items(
            s,
            recepcion_id=int(recepcion_id),
            items=items,
        )
        total.ya_asociado += ya_asociado

        if not items_filtrados:
            return total

        runtime = ChunkRuntime(
            tif=self._tif,
            storage=self._storage,
            client=self._client,
            scan_workers=self._scan_workers,
            upload_workers=self._upload_workers,
            upload_pause_ms=self._upload_pause_ms,
        )

        total_chunks = process_items_in_chunks(
            s,
            items_filtrados=items_filtrados,
            run_ctx=run_ctx,
            usuario_id=usuario_id,
            chunk_size=self._chunk_size,
            runtime=runtime,
            on_chunk_processed=progress_cb,
            chunk_pause_ms=self._chunk_pause_ms,
        )
        total.merge(total_chunks)

        return total
