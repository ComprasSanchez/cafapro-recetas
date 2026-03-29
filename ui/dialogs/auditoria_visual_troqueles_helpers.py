from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt


@dataclass(frozen=True)
class TroquelRowData:
    troquel_id: int
    codigo: str
    cantidad: int
    estado: str


def read_troquel_row(tbl, row: int) -> TroquelRowData | None:
    if row < 0:
        return None

    item_codigo = tbl.item(row, 0)
    if not item_codigo:
        return None

    troquel_id = int(item_codigo.data(Qt.ItemDataRole.UserRole) or 0)
    codigo = (item_codigo.text() or "").strip()

    item_cantidad = tbl.item(row, 2)
    cantidad_text = (item_cantidad.text() if item_cantidad else "1").strip()
    try:
        cantidad = int(cantidad_text)
    except Exception:
        cantidad = 1

    item_estado = tbl.item(row, 6)
    estado = (item_estado.text() if item_estado else "").strip()

    return TroquelRowData(
        troquel_id=troquel_id,
        codigo=codigo,
        cantidad=cantidad,
        estado=estado,
    )


def estado_permite_eliminar(*, estado: str, estado_amarillo: str, estado_rojo: str) -> bool:
    return estado in (estado_amarillo, estado_rojo)


def estado_es_rechazado(*, estado: str, estado_rojo: str) -> bool:
    return estado == estado_rojo
