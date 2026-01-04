from ui.header.actions import HeaderAction
from ui.windows.periodo_window import PeriodosWindow
from ui.windows.recepcion_window import RecepcionDialog

def build_header_actions(main_window) -> dict[str, list[HeaderAction]]:
    return {
        "Recepción": [
            HeaderAction(
                key="recepcion_window",
                text="Recepción",
                kind="window",
                window_factory=lambda: RecepcionDialog(main_window),
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
        ]
    }
