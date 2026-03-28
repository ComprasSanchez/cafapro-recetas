from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.db.session import session_scope
from app.service.auditoria.auditoria_visual_service import AuditoriaVisualService
from app.service.catalogos.vendedores_service import VendedoresService
from app.service.debitos.debitos_service import DebitoInput
from app.service.recetas.recetas_service import RecetaService
from app.service.recetas.troqueles_service import TroquelesService
from app.service.debitos.debitos_service import DebitosService
from app.exceptions.domain_errors import AuditoriaValidationError


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


class AuditoriaVisualUseCase:

    # ----------------------------------------
    # Cargar auditoría
    # ----------------------------------------
    @staticmethod
    def load_auditoria(asociacion_id: int):

        with session_scope() as s:
            data = AuditoriaVisualService.load_by_asociacion_id(
                s,
                asociacion_id
            )

        return data


    # ----------------------------------------
    # Finalizar auditoría
    # ----------------------------------------
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

        debitos = [
            DebitoInput(
                motivo_debito_id=int(motivo_id),
                detalle=detalle,
            )
            for motivo_id, detalle in (debitos_inputs or [])
        ]

        with session_scope() as s:

            DebitosService.replace_for_receta(
                s,
                receta_id=receta_id,
                items=debitos,
            )

            RecetaService.update_auditoria(
                s,
                receta_id=receta_id,
                vendedor_id=vendedor_id,
                estado_seguimiento_id=estado_seguimiento_id,
                estado_receta_id=1,
                fecha_prescripcion=fecha_prescripcion,
                fecha_emision=fecha_emision,
                fecha_venta=fecha_venta,
                usuario_id=usuario_id,
            )

        return True

    @staticmethod
    def validar_auditoria(
            *,
            fecha_autorizacion,
            fecha_venta,
            vendedor_id,
            debitos
    ):

        # venta obligatoria
        if not fecha_venta:
            raise AuditoriaValidationError(
                "Tenés que cargar la fecha de Venta."
            )

        # autorización vs venta
        if fecha_autorizacion and fecha_venta:
            if fecha_autorizacion != fecha_venta:
                raise AuditoriaValidationError(
                    "La fecha de Autorización y la fecha de Venta deben coincidir."
                )

        # vendedor obligatorio si hay débitos
        if debitos and not vendedor_id:
            raise AuditoriaValidationError(
                "Si seleccionás débitos tenés que cargar un vendedor."
            )

    @staticmethod
    def get_vendedor_info(*, vendedor_id: int) -> VendedorInfoOut | None:
        with session_scope() as s:
            vendedor = VendedoresService.get(s, vendedor_id=int(vendedor_id))

        if not vendedor:
            return None

        return VendedorInfoOut(
            vendedor_id=int(vendedor.vendedor_id),
            descripcion=str(getattr(vendedor, "descripcion", "") or ""),
            codigo=str(getattr(vendedor, "codigo", "") or ""),
        )

    @staticmethod
    def delete_troquel(*, troquel_id: int) -> None:
        with session_scope() as s:
            TroquelesService.delete(s, troquel_id=int(troquel_id))

    @staticmethod
    def list_vendedores_activos() -> list[VendedorPickItemOut]:
        with session_scope() as s:
            rows = VendedoresService.list(s, solo_activos=True)

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
        svc = TroquelesService()
        with session_scope() as s:
            troquel = svc.create(
                s,
                asociacion_id=int(asociacion_id),
                codigo_barra=str(codigo_barra or "").strip(),
                cantidad=int(cantidad),
            )
            return int(troquel.troquel_id)

    @staticmethod
    def update_troquel(*, troquel_id: int, cantidad: int) -> None:
        with session_scope() as s:
            TroquelesService.update(
                s,
                troquel_id=int(troquel_id),
                cantidad=int(cantidad),
            )
