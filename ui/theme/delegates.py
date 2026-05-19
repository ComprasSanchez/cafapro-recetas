"""
BackgroundPriorityDelegate
--------------------------
Qt's QStyleSheetStyle overrides QTableWidgetItem.setBackground() when the
global QSS defines any background/alternate-background-color on the view.
This delegate intercepts paint(), draws the BackgroundRole brush first,
then delegates text/icon painting with the background cleared so it does
not double-paint.  Apply it (or a subclass) to any table that needs
programmatic cell coloring to survive QSS.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush
from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem


class BackgroundPriorityDelegate(QStyledItemDelegate):

    def paint(self, painter, option, index) -> None:
        bg = index.data(Qt.ItemDataRole.BackgroundRole)

        if bg is not None:
            brush = bg if isinstance(bg, QBrush) else QBrush(bg)
            if brush.style() != Qt.BrushStyle.NoBrush:
                painter.save()
                painter.fillRect(option.rect, brush)
                painter.restore()

                opt = QStyleOptionViewItem(option)
                opt.backgroundBrush = QBrush()   # prevent base class re-painting bg
                super().paint(painter, opt, index)
                return

        super().paint(painter, option, index)
