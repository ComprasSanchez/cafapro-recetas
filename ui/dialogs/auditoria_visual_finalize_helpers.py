from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ui.dialogs.auditoria_visual_helpers import parse_ddmmyyyy


@dataclass(frozen=True)
class FinalizarPayload:
    receta_id: int
    fecha_prescripcion: date | None
    fecha_emision: date | None
    fecha_venta: date
    debitos_inputs: list[tuple[int, str | None]]


@dataclass(frozen=True)
class FinalizarValidationError:
    level: str
    title: str
    message: str


def build_finalizar_payload(
    *,
    data,
    state,
    prescripcion_text: str,
    emision_text: str,
    venta_text: str,
) -> tuple[FinalizarPayload | None, FinalizarValidationError | None]:
    receta_id = int(getattr(getattr(data, "receta", None), "receta_id", 0) or 0)
    if not receta_id:
        return None, FinalizarValidationError(
            level="critical",
            title="Error",
            message="No se pudo determinar la receta.",
        )

    fecha_prescripcion = parse_ddmmyyyy(prescripcion_text)
    fecha_emision = parse_ddmmyyyy(emision_text)
    fecha_venta = parse_ddmmyyyy(venta_text)

    if not fecha_venta:
        return None, FinalizarValidationError(
            level="warning",
            title="Falta fecha",
            message="Tenés que cargar la fecha de Venta (dd/MM/yyyy).",
        )

    fecha_autorizacion = getattr(getattr(data, "archivo", None), "fecha", None)
    if fecha_autorizacion and fecha_venta and fecha_autorizacion != fecha_venta:
        return None, FinalizarValidationError(
            level="warning",
            title="Fechas no coinciden",
            message="La fecha de Autorización y la fecha de Venta deben coincidir.",
        )

    if state.debitos and not state.vendedor_id:
        return None, FinalizarValidationError(
            level="warning",
            title="Falta vendedor",
            message="Si seleccionás algún débito, tenés que cargar un vendedor.",
        )

    debitos_inputs = [(mid, det) for mid, det in state.debitos.items()]

    return FinalizarPayload(
        receta_id=receta_id,
        fecha_prescripcion=fecha_prescripcion,
        fecha_emision=fecha_emision,
        fecha_venta=fecha_venta,
        debitos_inputs=debitos_inputs,
    ), None
