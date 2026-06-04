from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.config.settings import settings


@dataclass(frozen=True)
class ExcluidoItem:
    recepcion_id: int
    nro_referencia: str | None
    nro_receta: str | None
    fecha: object
    hora: object
    importe_bruto: object
    importe_cobertura: object
    importe_afiliado: object


def _url(recepcion_id: int) -> str:
    return f"{settings.API_CAFAPRO.rstrip('/')}/recepciones/{recepcion_id}/excluidos"


class ExcluidosService:
    @staticmethod
    def list_by_recepcion(recepcion_id: int) -> list[ExcluidoItem]:
        resp = httpx.get(_url(int(recepcion_id)), timeout=15)
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        return [
            ExcluidoItem(
                recepcion_id=e["recepcionId"],
                nro_referencia=e.get("nroReferencia"),
                nro_receta=e.get("nroReceta"),
                fecha=e.get("fecha"),
                hora=e.get("hora"),
                importe_bruto=e.get("importeBruto") or 0,
                importe_cobertura=e.get("importeCobertura") or 0,
                importe_afiliado=e.get("importeAfiliado") or 0,
            )
            for e in resp.json()
        ]
