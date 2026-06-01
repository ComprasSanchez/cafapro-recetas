from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.config.settings import settings


@dataclass(frozen=True)
class ResumenRecepcionItem:
    cantidad_recetas: int
    total_bruto: object
    total_cobertura: object
    total_afiliado: object


@dataclass(frozen=True)
class PrestadorResumenItem:
    prestador_id: int
    prestador: str
    total_bruto: object
    total_cobertura: object
    total_afiliado: object


def _url(path: str = "") -> str:
    return f"{settings.API_CAFAPRO.rstrip('/')}/recepciones{path}"


class ViewResumenRecepcionService:
    @staticmethod
    def get_resumen_recepcion(*, recepcion_id: int) -> ResumenRecepcionItem | None:
        resp = httpx.get(_url(f"/{recepcion_id}/resumen"), timeout=15)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        r = resp.json()
        return ResumenRecepcionItem(
            cantidad_recetas=int(r.get("cantidadRecetas") or 0),
            total_bruto=r.get("totalBruto") or 0,
            total_cobertura=r.get("totalCobertura") or 0,
            total_afiliado=r.get("totalAfiliado") or 0,
        )

    @staticmethod
    def list_prestadores_resumen(*, periodo_id: int) -> list[PrestadorResumenItem]:
        resp = httpx.get(
            _url("/totales-por-prestador"),
            params={"periodoId": int(periodo_id)},
            timeout=15,
        )
        resp.raise_for_status()
        return [
            PrestadorResumenItem(
                prestador_id=int(p["prestadorId"]),
                prestador=p.get("prestador") or "(sin nombre)",
                total_bruto=p.get("totalBruto") or 0,
                total_cobertura=p.get("totalCobertura") or 0,
                total_afiliado=p.get("totalAfiliado") or 0,
            )
            for p in resp.json()
        ]
