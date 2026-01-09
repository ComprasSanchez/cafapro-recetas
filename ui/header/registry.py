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
            HeaderAction(
                key="carga_recepcion_tab",
                text="Carga Recepcion",
                kind="tab",
                tab_key="carga-recepcion-handler",
            )
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
        ],
        "Archivo": [
            HeaderAction(
                key="archivo_cvs_tab",
                text="Carga CVS",
                kind="tab",
                tab_key="archivo-cvs",
            )
        ]
    }
