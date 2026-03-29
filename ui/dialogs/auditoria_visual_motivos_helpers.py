from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QListWidget, QListWidgetItem


def merge_unique_sorted_motivos(*, motivos_frente, motivos_dorso):
    motivos = (motivos_frente or []) + (motivos_dorso or [])

    unique: dict[int, object] = {}
    for m in motivos:
        unique[int(m.motivo_debito_id)] = m

    out = list(unique.values())
    out.sort(key=lambda m: (m.descripcion or "").lower())
    return out


def motivo_item_text(descripcion: str, detalle: str | None) -> str:
    if detalle:
        return f"{descripcion}  ({detalle})"
    return descripcion


def motivo_base_desc(item: QListWidgetItem) -> str:
    desc = item.data(Qt.ItemDataRole.UserRole + 1)
    if desc is None:
        txt = item.text() or ""
        idx = txt.find("  (")
        return txt[:idx] if idx >= 0 else txt
    return str(desc)


def set_motivo_item_text(item: QListWidgetItem, detalle: str | None) -> None:
    base = motivo_base_desc(item)
    item.setText(motivo_item_text(base, detalle))


def render_motivos_list(
    list_widget: QListWidget,
    *,
    motivos_frente,
    motivos_dorso,
    selected_debitos: dict[int, str | None],
) -> None:
    list_widget.blockSignals(True)
    list_widget.clear()

    motivos = merge_unique_sorted_motivos(
        motivos_frente=motivos_frente,
        motivos_dorso=motivos_dorso,
    )

    for m in motivos:
        motivo_id = int(m.motivo_debito_id)
        descripcion = m.descripcion
        activo = bool(getattr(m, "activo", True))
        seleccionado = motivo_id in selected_debitos

        if not activo and not seleccionado:
            continue

        detalle = selected_debitos.get(motivo_id) if seleccionado else None
        text = motivo_item_text(descripcion, detalle)

        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, motivo_id)
        item.setData(Qt.ItemDataRole.UserRole + 1, descripcion)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(
            Qt.CheckState.Checked if seleccionado else Qt.CheckState.Unchecked
        )

        if not activo:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            item.setForeground(QBrush(QColor(150, 150, 150)))

        list_widget.addItem(item)

    list_widget.blockSignals(False)
