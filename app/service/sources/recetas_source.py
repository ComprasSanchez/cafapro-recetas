from __future__ import annotations

from abc import ABC, abstractmethod


class RecetasSource(ABC):

    @abstractmethod
    def fetch_recetas(self, *, imed: str, fecha_str: str, obs: str):
        """
        Debe devolver:
        recetas_por_ref, detalles_por_ref
        """
        raise NotImplementedError