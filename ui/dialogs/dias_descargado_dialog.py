from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, QDate, Signal, QRect
from PySide6.QtGui import QPainter, QPen, QColor, QBrush

from ui.theme.row_colors import ok_bg, ok_fg
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QCalendarWidget, QWidget
)


MESES_ES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}


def _add_months(anchor: QDate, delta_months: int) -> QDate:
    d = QDate(anchor.year(), anchor.month(), 1)
    return d.addMonths(delta_months)


def _month_title_es(qd_first_day: QDate) -> str:
    return f"{MESES_ES.get(qd_first_day.month(), str(qd_first_day.month()))} {qd_first_day.year()}"


class BorderCalendar(QCalendarWidget):
    """
    Calendario fijo:
    - Qt pinta fondos (setDateTextFormat)
    - Borde SOLO al día de hoy
    - Navegación bloqueada (sin barra, sin wheel, sin teclas)
    - Días fuera del mes: tachados + “gris” y no seleccionables
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        self._today = QDate.currentDate()
        self._pen_today = QPen(ok_bg())
        self._pen_today.setWidth(2)

        # mes “lockeado” (se setea en lock_to_month)
        self._locked_year = self._today.year()
        self._locked_month = self._today.month()

        # fechas descargadas (set para paintCell)
        self._ok_dates: set[QDate] = set()
        self._ok_brush = QBrush(ok_bg())

        # Bloquear UI default
        self.setNavigationBarVisible(False)
        self.setGridVisible(True)
        self.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.setHorizontalHeaderFormat(QCalendarWidget.HorizontalHeaderFormat.ShortDayNames)

    def set_ok_dates(self, dates: set[QDate]) -> None:
        self._ok_dates = dates
        self._ok_brush = QBrush(ok_bg())
        self.updateCells()

    def refresh_today(self) -> None:
        self._today = QDate.currentDate()
        self.updateCells()

    def lock_to_month(self, first_day_of_month: QDate) -> None:
        """Fija el calendario a ese mes y deshabilita seleccionar días fuera del mes."""
        y = first_day_of_month.year()
        m = first_day_of_month.month()

        # lock interno
        self._locked_year = y
        self._locked_month = m

        # fija la página
        self.setCurrentPage(y, m)

        # rango: solo ese mes (esto evita clicks fuera del mes)
        last_day = QDate(y, m, QDate(y, m, 1).daysInMonth())
        self.setMinimumDate(first_day_of_month)
        self.setMaximumDate(last_day)

        # selección por defecto
        self.setSelectedDate(first_day_of_month)

    # ---- bloquear navegación ----
    def wheelEvent(self, e):
        e.ignore()
        return

    def keyPressEvent(self, e):
        if e.key() in (
            Qt.Key.Key_PageUp,
            Qt.Key.Key_PageDown,
            Qt.Key.Key_Home,
            Qt.Key.Key_End,
        ):
            e.ignore()
            return
        super().keyPressEvent(e)

    def mouseDoubleClickEvent(self, e):
        e.ignore()
        return

    def paintCell(self, painter: QPainter, rect: QRect, qdate: QDate) -> None:
        is_in_month = (qdate.year() == self._locked_year and qdate.month() == self._locked_month)
        is_ok = is_in_month and (qdate in self._ok_dates)

        if is_ok:
            # Pintado propio para evitar que el QSS sobreescriba setDateTextFormat
            painter.save()
            painter.fillRect(rect, self._ok_brush)
            painter.setPen(QPen(ok_fg()))
            painter.setFont(self.font())
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(qdate.day()))
            painter.restore()
        else:
            super().paintCell(painter, rect, qdate)

        # Días fuera del mes lockeado: tachado + gris
        if not is_in_month:
            painter.save()
            painter.setPen(QPen(QColor(150, 150, 150)))
            r = rect.adjusted(4, 4, -4, -4)
            painter.drawLine(r.topLeft(), r.bottomRight())
            painter.restore()
            return

        # Borde SOLO al día de hoy (si pertenece al mes)
        if qdate == self._today:
            painter.save()
            painter.setPen(self._pen_today)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            r = rect.adjusted(2, 2, -2, -2)
            painter.drawRoundedRect(r, 3, 3)
            painter.restore()


class DiasDescargadosDialog(QDialog):
    """
    3 meses fijo en horizontal:
    ORDEN (izq->der): mes actual | mes -1 | mes -2
    - Fondo verde: días descargados
    - Borde: hoy
    - Click día: emite dateSelected(date) y cierra
    """
    dateSelected = Signal(object)  # date

    def __init__(self, *, recepcion_id: int, fechas_descargadas: list[date], parent=None):
        super().__init__(parent)
        self.recepcion_id = int(recepcion_id)
        self._fechas = set(fechas_descargadas)

        self.setWindowTitle(f"Días descargados - Recepción {self.recepcion_id}")
        self.setMinimumSize(980, 460)
        self.setModal(True)

        # Anchor = mes actual (1er día)
        a = QDate.currentDate()
        self._anchor = QDate(a.year(), a.month(), 1)

        self._build_ui()
        self._apply_three_months()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        top = QHBoxLayout()
        self.lb_info = QLabel("")
        self.lb_info.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.btn_close = QPushButton("Cerrar")
        self.btn_close.setProperty("variant", "ghost")
        self.btn_close.setProperty("size", "md")
        self.btn_close.clicked.connect(self.reject)

        top.addWidget(self.lb_info, 1)
        top.addWidget(self.btn_close, 0)
        root.addLayout(top)

        # Contenedor horizontal (3 columnas)
        row = QHBoxLayout()
        row.setSpacing(12)

        self.w_curr = self._make_month_column()  # mes actual
        self.w_m1 = self._make_month_column()    # mes -1
        self.w_m2 = self._make_month_column()    # mes -2

        # ORDEN: actual | -1 | -2
        row.addWidget(self.w_curr, 1)
        row.addWidget(self.w_m1, 1)
        row.addWidget(self.w_m2, 1)

        root.addLayout(row, 1)

    def _make_month_column(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        title = QLabel("")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        title.setProperty("role", "subtitle")

        cal = BorderCalendar()
        cal.clicked.connect(self._on_clicked_day)

        lay.addWidget(title, 0)
        lay.addWidget(cal, 1)

        w._title = title  # type: ignore[attr-defined]
        w._cal = cal      # type: ignore[attr-defined]
        return w

    def _apply_three_months(self) -> None:
        self.lb_info.setText(f"Días descargados: {len(self._fechas)}")

        d_curr = _add_months(self._anchor, 0)    # actual
        d_m1 = _add_months(self._anchor, -1)     # -1
        d_m2 = _add_months(self._anchor, -2)     # -2

        self._set_month(self.w_curr, d_curr)
        self._set_month(self.w_m1, d_m1)
        self._set_month(self.w_m2, d_m2)

        # borde hoy (en los 3)
        self.w_curr._cal.refresh_today()  # type: ignore[attr-defined]
        self.w_m1._cal.refresh_today()    # type: ignore[attr-defined]
        self.w_m2._cal.refresh_today()    # type: ignore[attr-defined]

    def _set_month(self, col: QWidget, first_day: QDate) -> None:
        title: QLabel = col._title  # type: ignore[attr-defined]
        cal: BorderCalendar = col._cal  # type: ignore[attr-defined]

        title.setText(_month_title_es(first_day))
        cal.lock_to_month(first_day)
        self._render_month(cal, first_day)

    def _render_month(self, cal: BorderCalendar, month_first_day: QDate) -> None:
        year = month_first_day.year()
        month = month_first_day.month()

        ok_dates = {
            QDate(fd.year, fd.month, fd.day)
            for fd in self._fechas
            if fd.year == year and fd.month == month
        }
        cal.set_ok_dates(ok_dates)

    def _on_clicked_day(self, qd: QDate):
        d = date(qd.year(), qd.month(), qd.day())
        self.dateSelected.emit(d)
        self.accept()
