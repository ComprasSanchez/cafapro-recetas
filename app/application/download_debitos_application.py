from __future__ import annotations

from dataclasses import dataclass

from app.infra.storage import s3_storage
from app.service.debitos.view_debitos import ViewDebitos


@dataclass(frozen=True)
class DownloadDebitosIn:
    rows: list
    folder: str


@dataclass(frozen=True)
class DownloadDebitosOut:
    total: int


class DownloadDebitosApplication:
    @staticmethod
    def run(data: DownloadDebitosIn) -> DownloadDebitosOut:
        total = ViewDebitos.download_wrong_debitos(
            rows=data.rows,
            folder=data.folder,
            s3=s3_storage,
        )

        return DownloadDebitosOut(total=total)
