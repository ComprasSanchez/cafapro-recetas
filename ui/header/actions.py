from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Optional, Literal

ActionKind = Literal["tab", "window", "callback"]

@dataclass(frozen=True)
class HeaderAction:
    key: str                 
    text: str                # texto en el menú
    kind: ActionKind         # "tab" | "window" | "callback"
    tab_key: Optional[str] = None
    window_factory: Optional[Callable[[], object]] = None  # devuelve QWidget/QDialog
    callback: Optional[Callable[[], None]] = None
