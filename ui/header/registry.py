from ui.header.actions import HeaderAction
from ui.windows.periodo_window import PeriodosWindow
from ui.windows.recepcion_window import RecepcionesWindow
from ui.windows.usuario_window import UsuariosWindow


def build_header_actions(main_window) -> dict[str, list[HeaderAction]]:
    return {
        "Recepción": [
            HeaderAction(
                key="recepcion_window",
                text="Listado",
                kind="window",
                window_factory=lambda: RecepcionesWindow(main_window),
            ),
            HeaderAction(
                key="tab_resumen_recepcion",
                text="Resumen",
                kind="tab",
                tab_key="resumen_recepcion",
            ),
        ],
        "Periodo": [
            HeaderAction(
                key="periodo_window",
                text="Listado Periodos",
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
        "Auditoria": [
            HeaderAction(
                key="lotes_temporales_tab",
                text="Lotes Temporales",
                kind="tab",
                tab_key="lotes-temporales-handler",
            )
        ]
    }
