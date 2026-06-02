from __future__ import annotations

import httpx

from app.config.settings import settings


def _asociaciones_url() -> str:
    return f"{settings.API_CAFAPRO.rstrip('/')}/asociaciones"


def _recetas_url(receta_id: int, path: str = "") -> str:
    return f"{settings.API_CAFAPRO.rstrip('/')}/recetas/{receta_id}{path}"


class AsociacionService:
    @staticmethod
    def ejecutar(*, receta_id: int, archivo_id: int) -> None:
        resp = httpx.post(
            _asociaciones_url(),
            json={"recetaId": int(receta_id), "archivoId": int(archivo_id)},
            timeout=15,
        )
        if resp.status_code == 404:
            raise RuntimeError(resp.json().get("message", "Receta o archivo no encontrado"))
        resp.raise_for_status()

    @staticmethod
    def reasociar(*, receta_id: int, archivo_id: int) -> None:
        resp = httpx.patch(
            _recetas_url(int(receta_id), "/reasociar"),
            json={"archivoId": int(archivo_id)},
            timeout=15,
        )
        if resp.status_code == 404:
            raise RuntimeError(resp.json().get("message", "Receta o archivo no encontrado"))
        if resp.status_code == 400:
            raise RuntimeError(resp.json().get("message", "Error de validación"))
        resp.raise_for_status()

    @staticmethod
    def desasociar(*, receta_id: int) -> None:
        resp = httpx.patch(_recetas_url(int(receta_id), "/desasociar"), timeout=15)
        if resp.status_code == 404:
            raise RuntimeError(resp.json().get("message", "Receta no encontrada"))
        resp.raise_for_status()
