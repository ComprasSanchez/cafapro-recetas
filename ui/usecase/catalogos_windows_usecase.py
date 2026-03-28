from __future__ import annotations

from app.application.catalogos_application import CatalogosApplication


class CatalogosWindowsUseCase:
    @staticmethod
    def list_usuarios() -> list:
        return CatalogosApplication.list_usuarios()

    @staticmethod
    def delete_usuario(*, usuario_id: int) -> None:
        CatalogosApplication.delete_usuario(usuario_id=int(usuario_id))

    @staticmethod
    def list_vendedores(*, solo_activos: bool = False) -> list:
        return CatalogosApplication.list_vendedores(solo_activos=solo_activos)

    @staticmethod
    def create_vendedor(*, codigo: str, descripcion: str) -> None:
        CatalogosApplication.create_vendedor(
            codigo=codigo,
            descripcion=descripcion,
        )

    @staticmethod
    def update_vendedor(*, vendedor_id: int, codigo: str, descripcion: str) -> None:
        CatalogosApplication.update_vendedor(
            vendedor_id=int(vendedor_id),
            codigo=codigo,
            descripcion=descripcion,
        )

    @staticmethod
    def set_vendedor_activo(*, vendedor_id: int, activo: bool) -> None:
        CatalogosApplication.set_vendedor_activo(
            vendedor_id=int(vendedor_id),
            activo=activo,
        )

    @staticmethod
    def list_prestadores(*, solo_activos: bool = False) -> list:
        return CatalogosApplication.list_prestadores(solo_activos=solo_activos)

    @staticmethod
    def create_prestador(*, codigo: str, nombre: str, imed: str) -> None:
        CatalogosApplication.create_prestador(
            codigo=codigo,
            nombre=nombre,
            imed=imed,
        )

    @staticmethod
    def update_prestador(*, prestador_id: int, codigo: str, nombre: str, imed: str) -> None:
        CatalogosApplication.update_prestador(
            prestador_id=int(prestador_id),
            codigo=codigo,
            nombre=nombre,
            imed=imed,
        )

    @staticmethod
    def set_prestador_activo(*, prestador_id: int, activo: bool) -> None:
        CatalogosApplication.set_prestador_activo(
            prestador_id=int(prestador_id),
            activo=activo,
        )

    @staticmethod
    def list_periodos(*, solo_activos: bool = False) -> list:
        return CatalogosApplication.list_periodos(solo_activos=solo_activos)

    @staticmethod
    def create_periodo(*, anio: int, mes: int, quincena: int) -> None:
        CatalogosApplication.create_periodo(
            anio=int(anio),
            mes=int(mes),
            quincena=int(quincena),
        )

    @staticmethod
    def set_periodo_activo(*, periodo_id: int, activo: bool) -> None:
        CatalogosApplication.set_periodo_activo(
            periodo_id=int(periodo_id),
            activo=activo,
        )

    @staticmethod
    def list_obras_sociales(*, solo_activas: bool = False) -> list:
        return CatalogosApplication.list_obras_sociales(solo_activas=solo_activas)

    @staticmethod
    def create_obra_social(
        *,
        codigo: str,
        nombre: str,
        validador: str,
        dias_vencimiento: int | str | None,
        codigo_financiador: int | str | None,
    ) -> None:
        CatalogosApplication.create_obra_social(
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
        CatalogosApplication.update_obra_social(
            obra_social_id=int(obra_social_id),
            codigo=codigo,
            nombre=nombre,
            validador=validador,
            dias_vencimiento=dias_vencimiento,
            codigo_financiador=codigo_financiador,
        )

    @staticmethod
    def set_obra_social_activa(*, obra_social_id: int, activo: bool) -> None:
        CatalogosApplication.set_obra_social_activa(
            obra_social_id=int(obra_social_id),
            activo=activo,
        )

    @staticmethod
    def list_planes(*, solo_activos: bool = False) -> list:
        return CatalogosApplication.list_planes(solo_activos=solo_activos)

    @staticmethod
    def create_plan(*, obra_social_id: int, codigo: str | None, nombre: str | None) -> None:
        CatalogosApplication.create_plan(
            obra_social_id=int(obra_social_id),
            codigo=codigo,
            nombre=nombre,
        )

    @staticmethod
    def update_plan(*, plan_id: int, obra_social_id: int, codigo: str | None, nombre: str | None) -> None:
        CatalogosApplication.update_plan(
            plan_id=int(plan_id),
            obra_social_id=int(obra_social_id),
            codigo=codigo,
            nombre=nombre,
        )

    @staticmethod
    def set_plan_activo(*, plan_id: int, activo: bool) -> None:
        CatalogosApplication.set_plan_activo(
            plan_id=int(plan_id),
            activo=activo,
        )
