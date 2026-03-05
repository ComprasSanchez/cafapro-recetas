from __future__ import annotations

from .recetas_source import RecetasSource


class PreserfarApiSource(RecetasSource):

    def fetch_recetas(self, *, imed: str, fecha_str: str, obs: str):
        raise NotImplementedError("Preserfar API aún no implementado")