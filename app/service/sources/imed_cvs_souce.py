from __future__ import annotations

from core.imed_cvs_handler import ImedCvsHandler
from .recetas_source import RecetasSource


class ImedCsvSource(RecetasSource):

    def __init__(self):
        self._cvs = ImedCvsHandler()

    def fetch_recetas(self, *, imed: str, fecha_str: str, obs: str):
        recetas, detalles = self._cvs.read_cvs_by_imed_and_date(
            imed=imed,
            date=fecha_str,
            obs=obs,
        )

        return recetas or {}, detalles or {}