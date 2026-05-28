from __future__ import annotations

from app.service.catalogos.obra_social_service import ObraSocialService
from app.service.catalogos.periodo_service import PeriodoService
from app.service.catalogos.plan_service import PlanService
from app.service.catalogos.prestador_service import PrestadorService
from app.service.catalogos.rol_service import RolesService
from app.service.catalogos.usuario_service import UsuariosService
from app.service.catalogos.vendedores_service import VendedoresService


class CatalogosApplication:
    @staticmethod
    def list_roles() -> list:
        return RolesService.list()

    @staticmethod
    def create_user(*, username: str, password: str, rol_id: int) -> None:
        UsuariosService.create(username=username, password=password, rol_id=int(rol_id))

    @staticmethod
    def list_usuarios() -> list:
        return UsuariosService.list()

    @staticmethod
    def set_usuario_activo(*, usuario_id: int, activo: bool) -> None:
        if activo:
            UsuariosService.restore(int(usuario_id))
        else:
            UsuariosService.delete_logico(int(usuario_id))

    @staticmethod
    def list_vendedores(*, solo_activos: bool = False) -> list:
        return VendedoresService.list(solo_activos=solo_activos)

    @staticmethod
    def create_vendedor(*, codigo: str, descripcion: str) -> None:
        VendedoresService.create(codigo=codigo, descripcion=descripcion)

    @staticmethod
    def update_vendedor(*, vendedor_id: int, codigo: str, descripcion: str) -> None:
        VendedoresService.update(
            vendedor_id=int(vendedor_id),
            codigo=codigo,
            descripcion=descripcion,
        )

    @staticmethod
    def set_vendedor_activo(*, vendedor_id: int, activo: bool) -> None:
        if activo:
            VendedoresService.restore(int(vendedor_id))
        else:
            VendedoresService.delete_logico(int(vendedor_id))

    @staticmethod
    def list_prestadores(*, solo_activos: bool = False) -> list:
        return PrestadorService.list(solo_activos=solo_activos)

    @staticmethod
    def create_prestador(*, codigo: str, nombre: str, imed: str) -> None:
        PrestadorService.create(codigo=codigo, nombre=nombre, imed=imed)

    @staticmethod
    def update_prestador(*, prestador_id: int, codigo: str, nombre: str, imed: str) -> None:
        PrestadorService.update(
            prestador_id=int(prestador_id),
            codigo=codigo,
            nombre=nombre,
            imed=imed,
        )

    @staticmethod
    def set_prestador_activo(*, prestador_id: int, activo: bool) -> None:
        if activo:
            PrestadorService.restore(int(prestador_id))
        else:
            PrestadorService.delete_logico(int(prestador_id))

    @staticmethod
    def list_periodos(*, solo_activos: bool = False) -> list:
        return PeriodoService.list(solo_activos=solo_activos)

    @staticmethod
    def create_periodo(*, anio: int, mes: int, quincena: int) -> None:
        PeriodoService.create(
            anio=int(anio),
            mes=int(mes),
            quincena=int(quincena),
        )

    @staticmethod
    def set_periodo_activo(*, periodo_id: int, activo: bool) -> None:
        if activo:
            PeriodoService.restore(int(periodo_id))
        else:
            PeriodoService.delete_logico(int(periodo_id))

    @staticmethod
    def list_obras_sociales(*, solo_activas: bool = False) -> list:
        return ObraSocialService.list(solo_activas=solo_activas)

    @staticmethod
    def create_obra_social(
        *,
        codigo: str,
        nombre: str,
        validador: str,
        dias_vencimiento: int | str | None,
        codigo_financiador: int | str | None,
    ) -> None:
        ObraSocialService.create(
            codigo=codigo,
            nombre=nombre,
            validador=validador,
            dias_vencimiento=dias_vencimiento,
            codigo_financiador=codigo_financiador,
        )

    @staticmethod
    def update_obra_social(
        *,
        obra_social_id: int,
        codigo: str,
        nombre: str,
        validador: str,
        dias_vencimiento: int | str | None,
        codigo_financiador: int | str | None,
    ) -> None:
        ObraSocialService.update(
            obra_social_id=int(obra_social_id),
            codigo=codigo,
            nombre=nombre,
            validador=validador,
            dias_vencimiento=dias_vencimiento,
            codigo_financiador=codigo_financiador,
        )

    @staticmethod
    def set_obra_social_activa(*, obra_social_id: int, activo: bool) -> None:
        if activo:
            ObraSocialService.restore(int(obra_social_id))
        else:
            ObraSocialService.delete_logico(int(obra_social_id))

    @staticmethod
    def list_planes(*, solo_activos: bool = False) -> list:
        return PlanService.list(solo_activos=solo_activos)

    @staticmethod
    def create_plan(*, obra_social_id: int, codigo: str | None, nombre: str | None) -> None:
        PlanService.create(obra_social_id=int(obra_social_id), codigo=codigo, nombre=nombre)

    @staticmethod
    def update_plan(*, plan_id: int, obra_social_id: int, codigo: str | None, nombre: str | None) -> None:
        PlanService.update(
            plan_id=int(plan_id),
            obra_social_id=int(obra_social_id),
            codigo=codigo,
            nombre=nombre,
        )

    @staticmethod
    def set_plan_activo(*, plan_id: int, activo: bool) -> None:
        if activo:
            PlanService.restore(int(plan_id))
        else:
            PlanService.delete_logico(int(plan_id))
