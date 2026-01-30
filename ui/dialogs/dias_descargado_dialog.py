from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, QDate, Signal, QRect
from PySide6.QtGui import (
    QPainter, QPen, QColor,
    QTextCharFormat, QBrush
)
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QCalendarWidget
)


def to_qdate(d: date) -> QDate:
    return QDate(d.year, d.month, d.day)


class BorderCalendar(QCalendarWidget):
    """
    Calendario que:
    - deja que Qt pinte los fondos (setDateTextFormat)
    - agrega BORDE SOLO al día de HOY
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._today = QDate.currentDate()
        self._pen_today = QPen(QColor(30, 160, 30))
        self._pen_today.setWidth(2)

    def refresh_today(self) -> None:
        self._today = QDate.currentDate()
        self.updateCells()

    def paintCell(self, painter: QPainter, rect: QRect, qdate: QDate) -> None:
        super().paintCell(painter, rect, qdate)

        if qdate == self._today:
            painter.save()
            painter.setPen(self._pen_today)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            r = rect.adjusted(2, 2, -2, -2)
            painter.drawRoundedRect(r, 3, 3)
            painter.restore()


class DiasDescargadosDialog(QDialog):
    """
    - Fondo verde: días descargados (fechas_descargadas)
    - Borde: día de hoy (aunque no esté descargado)
    - Click en día: emite dateSelected(date) y cierra
    """
    dateSelected = Signal(object)  # date

    def __init__(self, *, recepcion_id: int, fechas_descargadas: list[date], parent=None):
        super().__init__(parent)
        self.recepcion_id = int(recepcion_id)
        self._fechas = set(fechas_descargadas)

        self.setWindowTitle(f"Días descargados - Recepción {self.recepcion_id}")
        self.setMinimumSize(520, 420)
        self.setModal(True)

        # formatos
        self._fmt_clear = QTextCharFormat()

        self._fmt_ok = QTextCharFormat()
        self._fmt_ok.setBackground(QBrush(QColor(190, 245, 190)))  # fondo verde suave
        self._fmt_ok.setToolTip("Descargado")

        self._build_ui()
        self._apply_data()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        top = QHBoxLayout()
        self.lb_info = QLabel("")
        self.lb_info.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.btn_close = QPushButton("Cerrar")
        self.btn_close.clicked.connect(self.reject)

        top.addWidget(self.lb_info, 1)
        top.addWidget(self.btn_close, 0)
        root.addLayout(top)

        self.cal = BorderCalendar()
        self.cal.setGridVisible(True)
        self.cal.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.cal.clicked.connect(self._on_clicked_day)

        # si cambiás de mes, re-aplicamos formatos (porque solo limpiamos el mes visible)
        self.cal.currentPageChanged.connect(self._render_visible_month)

        root.addWidget(self.cal, 1)

    def _apply_data(self):
        self.lb_info.setText(f"Días descargados: {len(self._fechas)}")

        # ir al primer día descargado
        if self._fechas:
            self.cal.showSelectedDate()

        self._render_visible_month()
        self.cal.refresh_today()

    def _render_visible_month(self):
        """
        Limpia y aplica formatos SOLO para el mes visible.
        (Es rápido y no rompe otros meses.)
        """
        year = self.cal.yearShown()
        month = self.cal.monthShown()

        days = QDate(year, month, 1).daysInMonth()

        # limpiar mes visible
        for d in range(1, days + 1):
            self.cal.setDateTextFormat(QDate(year, month, d), self._fmt_clear)

        # aplicar fondo verde a los descargados dentro del mes visible
        for fd in self._fechas:
            if fd.year == year and fd.month == month:
                self.cal.setDateTextFormat(QDate(fd.year, fd.month, fd.day), self._fmt_ok)

        # repintar borde de hoy
        self.cal.refresh_today()

    def _on_clicked_day(self, qd: QDate):
        d = date(qd.year(), qd.month(), qd.day())
        self.dateSelected.emit(d)
        self.accept()

