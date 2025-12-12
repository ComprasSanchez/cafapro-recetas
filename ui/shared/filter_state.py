# ui/shared/filter_state.py
from dataclasses import dataclass

@dataclass
class FilterState:
    recepcion: str = ""
    obra_social: str = "PAMI"
    prestador: str = "S.A"
    presentacion: str = ""
    periodo: str = "12-2025"
    quincena: str = "1"

    filtro_img_fecha: str = ""
    filtro_aut_fecha: str = ""
