from __future__ import annotations

from datetime import date

import httpx

from app.config.settings import settings


def _url(path: str = "") -> str:
    return f"{settings.API_CAFAPRO.rstrip('/')}/recetas{path}"


class RecetaService:
    @staticmethod
    def upsert_receta(
        recepcion_id: int,
        archivo_id: int,
        nro_receta: str,
        usuario_id: int | None,
        ubicacion_frente: str | None,
        ubicacion_dorso: str | None,
        troqueles: list[str],
    ) -> tuple[int, bool]:
        payload = {
            "recepcionId": int(recepcion_id),
            "archivoId": int(archivo_id),
            "nroReceta": str(nro_receta),
            "usuarioId": usuario_id,
            "ubicacionFrente": ubicacion_frente,
            "ubicacionDorso": ubicacion_dorso,
            "troqueles": [str(t).strip() for t in troqueles if str(t).strip()],
        }
        resp = httpx.post(_url("/upsert"), json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return int(data["recetaId"]), bool(data["created"])

    @staticmethod
    def update_auditoria(
        receta_id: int,
        vendedor_id: int | None,
        estado_seguimiento_id: int | None,
        fecha_prescripcion: date | None,
        fecha_emision: date | None,
        fecha_venta: date,
        estado_receta_id: int = 1,
        usuario_id: int | None = None,
        debitos: list[dict] | None = None,
    ) -> None:
        payload: dict = {"fechaVenta": fecha_venta.isoformat()}
        if vendedor_id is not None:
            payload["vendedorId"] = int(vendedor_id)
        if estado_seguimiento_id is not None:
            payload["estadoSeguimientoId"] = int(estado_seguimiento_id)
        if fecha_prescripcion is not None:
            payload["fechaPrescripcion"] = fecha_prescripcion.isoformat()
        if fecha_emision is not None:
            payload["fechaEmision"] = fecha_emision.isoformat()
        if usuario_id is not None:
            payload["usuarioId"] = int(usuario_id)
        if debitos is not None:
            payload["debitos"] = debitos
        resp = httpx.patch(_url(f"/{int(receta_id)}/finalizar-auditoria"), json=payload, timeout=15)
        if resp.status_code == 404:
            raise ValueError(f"Receta {receta_id} no existe")
        resp.raise_for_status()

    @staticmethod
    def update_estado_seguimiento(receta_id: int, estado_seguimiento_id: int | None) -> None:
        resp = httpx.patch(
            _url(f"/{int(receta_id)}/estado-seguimiento"),
            json={"estadoSeguimientoId": estado_seguimiento_id},
            timeout=10,
        )
        if resp.status_code == 404:
            raise ValueError(f"No existe receta_id={receta_id}")
        resp.raise_for_status()

    @staticmethod
    def anular_receta(receta_id: int, nro_receta: str) -> None:
        resp = httpx.patch(
            _url(f"/{int(receta_id)}/anular"),
            json={"nroReceta": str(nro_receta)},
            timeout=10,
        )
        if resp.status_code == 404:
            raise RuntimeError("Receta no encontrada")
        resp.raise_for_status()

    @staticmethod
    def duplicar_receta(receta_id: int, nro_receta: str) -> None:
        resp = httpx.patch(
            _url(f"/{int(receta_id)}/duplicar"),
            json={"nroReceta": str(nro_receta)},
            timeout=10,
        )
        if resp.status_code == 404:
            raise RuntimeError("Receta no encontrada")
        resp.raise_for_status()

    @staticmethod
    def eliminar_sobrante(*, receta_id: int) -> None:
        resp = httpx.delete(_url(f"/{int(receta_id)}"), timeout=15)
        if resp.status_code == 404:
            raise RuntimeError("Receta no encontrada")
        if resp.status_code == 400:
            raise RuntimeError(resp.json().get("message", "Solo se pueden eliminar recetas en revisión"))
        resp.raise_for_status()

    @staticmethod
    def eliminar_sobrantes_bulk(*, receta_ids: list[int]) -> dict:
        ids = list({int(r) for r in (receta_ids or []) if int(r or 0) > 0})
        resp = httpx.request("DELETE", _url("/bulk"), json={"recetaIds": ids}, timeout=30)
        resp.raise_for_status()
        return resp.json()
