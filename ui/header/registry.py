from ui.header.actions import HeaderAction
from ui.windows.excluidos_window import ExcluidosWindow
from ui.windows.listado_debitos_window import ListadoDebitosWindow
from ui.windows.mal_entrego_excel_window import MalEntregoExcelWindow
from ui.windows.motivos_debitos_window import MotivosDebitosWindow
from ui.windows.obra_social_window import ObrasSocialesWindow
from ui.windows.periodo_window import PeriodosWindow
from ui.windows.plan_window import PlanWindow
from ui.windows.prestador_window import PrestadoresWindow
from ui.windows.recepcion_window import RecepcionesWindow
from ui.windows.resumen_recepcion_window import ResumenRecepcionWindow
from ui.windows.usuario_window import UsuariosWindow
from ui.windows.vendedor_window import VendedoresWindow
from ui.security.permissions import can_access_header_action


def build_header_actions(main_window, current_user) -> dict[str, list[HeaderAction]]:
    actions_by_group = {
        "Recepción": [
            HeaderAction(
                key="recepcion_window",
                text="Listado de recepciones",
                kind="window",
                window_factory=lambda: RecepcionesWindow(main_window, creado_por_usuario_id=current_user.usuario_id),
            ),
            HeaderAction(
                key="carga_recepcion_tab",
                text="Carga de recepción",
                kind="tab",
                tab_key="carga-recepcion-handler",
            ),
            HeaderAction(
                key="listado_debitos_window",
                text="Listado de débitos",
                kind="window",
                window_factory=lambda: ListadoDebitosWindow(main_window),
            ),
            HeaderAction(
                key="mal_entrego_excel_window",
                text="Bajar Mal Entregado General",
                kind="window",
                window_factory=lambda: MalEntregoExcelWindow(main_window),
            ),
            HeaderAction(
                key="exluidos_window",
                text="Excluidos",
                kind="window",
                window_factory=lambda: ExcluidosWindow(main_window)
            ),
            HeaderAction(
                key="resumen_recepcion_window",
                text="Resumen de recepción",
                kind="window",
                window_factory=lambda: ResumenRecepcionWindow(main_window),
            )
        ],
        "Período": [
            HeaderAction(
                key="periodo_window",
                text="Listado de períodos",
                kind="window",
                window_factory=lambda: PeriodosWindow(main_window),
            )
        ],
        "Usuario": [
            HeaderAction(
                key="usuario_window",
                text="Listado Usuarios",
                kind="window",
                window_factory=lambda: UsuariosWindow(main_window),
            )
        ],
        "Auditoría": [
            HeaderAction(
                key="tab_auditoria",
                text="Auditoría",
                kind="tab",
                tab_key="auditoria",
            )
        ],
        "Archivo": [
            HeaderAction(
                key="archivo_cvs_tab",
                text="Carga de CSV",
                kind="tab",
                tab_key="archivo-cvs",
            )
        ],
        "Configuraciones": [
            HeaderAction(
                key="Obras Sociales",
                text="Obras Sociales",
                kind="window",
                window_factory= lambda: ObrasSocialesWindow(main_window),
            ),
            HeaderAction(
                key="Planes",
                text="Planes",
                kind="window",
                window_factory=lambda: PlanWindow(main_window),
            ),
            HeaderAction(
                key="Vendedores",
                text="Vendedores",
                kind="window",
                window_factory=lambda: VendedoresWindow(main_window),
            ),
            HeaderAction(
                key="Prestadores",
                text="Prestadores",
                kind="window",
                window_factory=lambda: PrestadoresWindow(main_window),
            ),
            HeaderAction(
                key="Motivos Debitos",
                text="Motivos de débitos",
                kind="window",
                window_factory=lambda: MotivosDebitosWindow(main_window),
            )
        ]
    }

    filtered: dict[str, list[HeaderAction]] = {}
    for group, actions in actions_by_group.items():
        allowed = [
            action
            for action in actions
            if can_access_header_action(
                user=current_user,
                action_key=action.key,
                kind=action.kind,
                tab_key=action.tab_key,
            )
        ]
        if allowed:
            filtered[group] = allowed

    return filtered
