from __future__ import annotations

import httpx

from app.config.settings import settings


def _url(recepcion_id: int) -> str:
    return f"{settings.API_CAFAPRO.rstrip('/')}/recepciones/{recepcion_id}/arrastrar-excluidos"


class ArrastreExcluidosService:
    """
    Ejecuta el arrastre de excluidos NO vencidos desde la recepción anterior inmediata
    (mismo prestador+obra social) hacia la recepción actual, renumerando orden_lote 1..K.

    Importante:
    - Solo corre si la recepción actual está vacía.
    - Filtra vencidas usando fecha_presentacion_actual - 60 días.
    """

    @staticmethod
    def run(*, recepcion_id: int) -> int:
        resp = httpx.post(_url(int(recepcion_id)), timeout=600)
        if resp.status_code == 404:
            raise ValueError(f"No existe la recepción {recepcion_id}")
        resp.raise_for_status()
        try:
            return int(resp.json().get("moved") or 0)
        except Exception:
            return 0
