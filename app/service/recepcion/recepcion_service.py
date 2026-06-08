from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

import httpx

from app.config.settings import settings


@dataclass(frozen=True)
class RecepcionListItem:
    recepcion_id: int
    numero: int
    obra_social: str
    periodo: str
    prestador: str
    estado: str
    fecha_presentacion: object
    creado_en: Optional[object]
    imed: str
    validador: str
    dias_vencimiento: int | None
    codigo_financiador: int | None


@dataclass(frozen=True)
class PrestadorConRecepcionesItem:
    prestador_id: int
    nombre: str
    codigo: str
    imed: str
    cantidad_recepciones: int


@dataclass(frozen=True)
class RecepcionRowItem:
    recepcion_id: int
    numero: int
    obra_social: str
    fecha_presentacion: Optional[date]


def _url(path: str = "") -> str:
    return f"{settings.API_CAFAPRO.rstrip('/')}/recepciones{path}"


def _to_list_item(r: dict) -> RecepcionListItem:
    return RecepcionListItem(
        recepcion_id=r["recepcionId"],
        numero=int(r["numero"]),
        obra_social=r.get("obraSocial") or "",
        periodo=r.get("periodo") or "",
        prestador=r.get("prestador") or "",
        estado=r.get("estado") or "",
        fecha_presentacion=r.get("fechaPresentacion"),
        creado_en=r.get("creadoEn"),
        imed=r.get("imed") or "",
        validador=r.get("validador") or "imed",
        dias_vencimiento=r.get("diasVencimiento"),
        codigo_financiador=r.get("codigoFinanciador"),
    )


def _to_row_item(r: dict) -> RecepcionRowItem:
    return RecepcionRowItem(
        recepcion_id=r["recepcionId"],
        numero=int(r["numero"]),
        obra_social=r.get("obraSocial") or "",
        fecha_presentacion=r.get("fechaPresentacion"),
    )


def _to_prestador_item(p: dict) -> PrestadorConRecepcionesItem:
    return PrestadorConRecepcionesItem(
        prestador_id=p["prestadorId"],
        nombre=p.get("nombre") or "(sin nombre)",
        codigo=p.get("codigo") or "",
        imed=p.get("imed") or "",
        cantidad_recepciones=int(p.get("cantidadRecepciones") or 0),
    )


class RecepcionService:
    @staticmethod
    def list(*, all: bool = True) -> list[RecepcionListItem]:
        resp = httpx.get(_url(), params={"includeClosed": "true" if all else "false"}, timeout=600)
        resp.raise_for_status()
        return [_to_list_item(r) for r in resp.json()]

    @staticmethod
    def get(recepcion_id: int) -> RecepcionListItem | None:
        resp = httpx.get(_url(f"/{recepcion_id}"), timeout=600)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return _to_list_item(resp.json())

    @staticmethod
    def list_recepciones(*, periodo_id: int, prestador_id: int) -> list[RecepcionRowItem]:
        resp = httpx.get(
            _url("/lista"),
            params={"periodoId": int(periodo_id), "prestadorId": int(prestador_id)},
            timeout=600,
        )
        resp.raise_for_status()
        return [_to_row_item(r) for r in resp.json()]

    @staticmethod
    def list_prestadores_con_recepcion(*, periodo_id: int) -> list[PrestadorConRecepcionesItem]:
        resp = httpx.get(
            _url("/prestadores-con-recepcion"),
            params={"periodoId": int(periodo_id)},
            timeout=600,
        )
        resp.raise_for_status()
        return [_to_prestador_item(p) for p in resp.json()]

    @staticmethod
    def has_debitos_sin_estado(recepcion_id: int) -> bool:
        resp = httpx.get(_url(f"/{recepcion_id}/has-debitos-sin-estado"), timeout=600)
        if resp.status_code == 404:
            raise ValueError(f"No existe la recepción {recepcion_id}")
        resp.raise_for_status()
        return bool(resp.json().get("hasSinEstado", False))

    @staticmethod
    def create(
        *,
        obra_social_id: int,
        periodo_id: int,
        prestador_id: int,
        estado_recepcion_id: int,
        fecha_presentacion,
        observaciones: str | None = None,
        creado_por_usuario_id: int | None = None,
    ) -> RecepcionListItem:
        payload = {
            "obraSocialId": int(obra_social_id),
            "periodoId": int(periodo_id),
            "prestadorId": int(prestador_id),
            "estadoRecepcionId": int(estado_recepcion_id),
            "fechaPresentacion": (
                fecha_presentacion.isoformat()
                if hasattr(fecha_presentacion, "isoformat")
                else str(fecha_presentacion)
            ),
            "observaciones": observaciones,
            "creadoPorUsuarioId": creado_por_usuario_id,
        }
        resp = httpx.post(_url(), json=payload, timeout=600)
        if resp.status_code == 409:
            raise RuntimeError(resp.json().get("message", "Conflicto al crear recepción."))
        if resp.status_code == 404:
            raise RuntimeError(resp.json().get("message", "Referencia no encontrada."))
        resp.raise_for_status()
        return _to_list_item(resp.json())

    @staticmethod
    def delete(recepcion_id: int) -> None:
        resp = httpx.delete(_url(f"/{recepcion_id}"), timeout=600)
        if resp.status_code == 404:
            raise ValueError("La recepción no existe.")
        resp.raise_for_status()

    @staticmethod
    def cerrar_recepcion(recepcion_id: int) -> None:
        resp = httpx.patch(_url(f"/{recepcion_id}/cerrar"), timeout=600)
        if resp.status_code == 404:
            raise RuntimeError(f"No existe la recepción {recepcion_id}")
        resp.raise_for_status()
