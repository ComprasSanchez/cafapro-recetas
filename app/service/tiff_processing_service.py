from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from core.process_tif import TiffProcessor


@dataclass(frozen=True)
class TiffResult:
    referencias: List[str]          # headers
    troqueles: List[str]            # EAN13
    frente_jpg: Optional[str]
    dorso_jpg: Optional[str]


class TiffProcessingService:
    def __init__(self):
        self._processor = TiffProcessor()

    def process(self, tiff_path: str, output_dir: str | None = None) -> TiffResult:
        out = self._processor.process(tiff_path, output_dir=output_dir)

        headers = [str(x).strip() for x in (out.get("headers") or []) if x]
        troq = [str(x).strip() for x in (out.get("troqueles") or []) if x]

        files = out.get("files") or {}
        return TiffResult(
            referencias=headers,
            troqueles=troq,
            frente_jpg=files.get("front_jpg"),
            dorso_jpg=files.get("back_jpg"),
        )
