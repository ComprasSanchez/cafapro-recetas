from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import httpx

from app.config.settings import settings
from app.exceptions.domain_errors import AuditoriaValidationError
from app.service.auditoria.auditoria_visual_service import AuditoriaVisualService
from app.service.catalogos.vendedores_service import VendedoresService
from app.service.recetas.troqueles_service import TroquelesService


@dataclass(frozen=True)
class VendedorInfoOut:
    vendedor_id: int
    descripcion: str
    codigo: str


@dataclass(frozen=True)
class VendedorPickItemOut:
    vendedor_id: int
    codigo: str
    descripcion: str


def _recetas_url(receta_id: int) -> str:
    return f"{settings.API_CAFAPRO.rstrip('/')}/recetas/{receta_id}/finalizar-auditoria"


class AuditoriaVisualApplication:
    @staticmethod
    def load_auditoria(asociacion_id: int):
        return AuditoriaVisualService.load_by_asociacion_id(asociacion_id)

    @staticmethod
    def finalizar_auditoria(
        *,
        receta_id: int,
        vendedor_id: int | None,
        estado_seguimiento_id: int | None,
        fecha_prescripcion: date | None,
        fecha_emision: date | None,
        fecha_venta: date,
        usuario_id: int,
        debitos_inputs: list[tuple[int, str | None]],
    ):
        def _iso(d) -> str | None:
            if d is None:
                return None
            return d.isoformat() if hasattr(d, "isoformat") else str(d)

        payload = {
            "vendedorId": vendedor_id,
            "estadoSeguimientoId": estado_seguimiento_id,
            "fechaPrescripcion": _iso(fecha_prescripcion),
            "fechaEmision": _iso(fecha_emision),
            "fechaVenta": _iso(fecha_venta),
            "usuarioId": usuario_id,
            "debitos": [
                {"motivoDebitoId": int(motivo_id), "detalle": detalle or None}
                for motivo_id, detalle in (debitos_inputs or [])
            ],
        }

        resp = httpx.patch(_recetas_url(int(receta_id)), json=payload, timeout=15)
        if resp.status_code == 404:
            raise ValueError(f"Receta {receta_id} no existe")
        if resp.status_code == 400:
            detail = resp.json().get("message", resp.text)
            raise ValueError(f"Error de validación: {detail}")
        resp.raise_for_status()
        return True

    @staticmethod
    def validar_auditoria(*, fecha_autorizacion, fecha_venta, vendedor_id, debitos):
        from datetime import date as dt_date

        if not fecha_venta:
            raise AuditoriaValidationError("Tenes que cargar la fecha de Venta.")

        def _to_date(v):
            if isinstance(v, dt_date):
                return v
            if v is None:
                return None
            s = str(v).strip()
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
                try:
                    from datetime import datetime
                    return datetime.strptime(s[:10], fmt).date()
                except ValueError:
                    continue
            return None

        if fecha_autorizacion and fecha_venta:
            fa = _to_date(fecha_autorizacion)
            fv = _to_date(fecha_venta)
            if fa and fv and fa != fv:
                raise AuditoriaValidationError(
                    "La fecha de Autorizacion y la fecha de Venta deben coincidir."
                )

        if debitos and not vendedor_id:
            raise AuditoriaValidationError(
                "Si seleccionas debitos tenes que cargar un vendedor."
            )

    @staticmethod
    def get_vendedor_info(*, vendedor_id: int) -> VendedorInfoOut | None:
        vendedor = VendedoresService.get(int(vendedor_id))

        if not vendedor:
            return None

        return VendedorInfoOut(
            vendedor_id=int(vendedor.vendedor_id),
            descripcion=str(vendedor.descripcion or ""),
            codigo=str(vendedor.codigo or ""),
        )

    @staticmethod
    def delete_troquel(*, troquel_id: int) -> None:
        TroquelesService.delete(int(troquel_id))

    @staticmethod
    def list_vendedores_activos() -> list[VendedorPickItemOut]:
        rows = VendedoresService.list(solo_activos=True)

        return [
            VendedorPickItemOut(
                vendedor_id=int(r.vendedor_id),
                codigo=str(r.codigo or ""),
                descripcion=str(r.descripcion or ""),
            )
            for r in rows
        ]

    @staticmethod
    def create_troquel(*, asociacion_id: int, codigo_barra: str, cantidad: int) -> int:
        troquel = TroquelesService.create(
            asociacion_id=int(asociacion_id),
            codigo_barra=str(codigo_barra or "").strip(),
            cantidad=int(cantidad),
        )
        return int(troquel.troquel_id)

    @staticmethod
    def update_troquel(*, troquel_id: int, cantidad: int) -> None:
        TroquelesService.update(
            troquel_id=int(troquel_id),
            cantidad=int(cantidad),
        )
