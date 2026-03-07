from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class AuditoriaState:

    vendedor_id: int | None = None

    fecha_prescripcion: date | None = None
    fecha_emision: date | None = None
    fecha_venta: date | None = None

    debitos: dict[int, str | None] = field(default_factory=dict)

    def has_debitos(self) -> bool:
        return bool(self.debitos)