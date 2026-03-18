from __future__ import annotations

from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView
)

from app.db.session import session_scope
from app.service.auditoria.excluidos_service import ExcluidosService
from ui.dialogs.recepcion_pick_dialog import RecepcionPickDialog


class ExcluidosWindow(QDialog):
    def __init__(
        self,
        parent=None,
        recepcion_id: int | None = None,
        recepcion_numero: str | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Archivos Excluidos")
        self.setMinimumSize(950, 520)

        self._recepcion_id: int | None = int(recepcion_id) if recepcion_id is not None else None
        self._recepcion_numero = str(recepcion_numero or "").strip()
        self._recepcion_fija = recepcion_id is not None

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # Header
        head = QHBoxLayout()
        self.lb_recepcion = QLabel("Recepción: —")
        self.lb_recepcion.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        head.addWidget(self.lb_recepcion, 1)

        self.btn_pick = QPushButton("Elegir recepción…")
        self.btn_pick.clicked.connect(self._pick_recepcion)
        head.addWidget(self.btn_pick, 0)

        self.btn_reload = QPushButton("Refrescar")
        self.btn_reload.setEnabled(False)
        self.btn_reload.clicked.connect(self._load)
        head.addWidget(self.btn_reload, 0)

        root.addLayout(head)

        # Table
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Referencia", "Receta", "Fecha", "Hora", "Importe Neto", "A cargo entidad"
        ])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        hh.setStretchLastSection(True)
        hh.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

        root.addWidget(self.table, 1)

        # Actions
        actions = QHBoxLayout()

        self.btn_copy = QPushButton("Copiar tabla")
        self.btn_copy.setEnabled(False)
        self.btn_copy.clicked.connect(self._copy_table_to_clipboard)
        actions.addWidget(self.btn_copy)

        actions.addStretch(1)

        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.reject)
        actions.addWidget(btn_close)

        root.addLayout(actions)

        if self._recepcion_id:
            self._set_recepcion_label(self._recepcion_numero or str(self._recepcion_id))
            self.btn_reload.setEnabled(True)

            if self._recepcion_fija:
                self.btn_pick.setVisible(False)
                self.btn_pick.setEnabled(False)

            self._load()

    def _pick_recepcion(self) -> None:
        dlg = RecepcionPickDialog(self, show_closed=False, enable_filter=False)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        rid, numero = dlg.selected()
        if not rid:
            return

        self._recepcion_id = int(rid)
        self._set_recepcion_label(numero)
        self.btn_reload.setEnabled(True)

        self._load()

    def _set_recepcion_label(self, numero: str) -> None:
        value = str(numero or "").strip()
        self.lb_recepcion.setText(f"Recepción: {value or '—'}")

    def _load(self) -> None:
        if not self._recepcion_id:
            return

        try:
            with session_scope() as s:
                rows = ExcluidosService.list_by_recepcion(s, self._recepcion_id)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar excluidos:\n{e}")
            return

        self.table.setRowCount(0)

        for r in rows:
            i = self.table.rowCount()
            self.table.insertRow(i)

            self._set(i, 0, str(getattr(r, "nro_referencia", "") or ""))
            self._set(i, 1, str(getattr(r, "nro_receta", "") or ""))
            self._set(i, 2, str(getattr(r, "fecha", "") or ""))
            self._set(i, 3, str(getattr(r, "hora", "") or ""))

            imp_obs = Decimal(str(getattr(r, "importe_obs", 0) or 0))
            a_cargo = Decimal(str(getattr(r, "a_cargo_entidad", 0) or 0))

            self._set(i, 4, self._fmt_ar(imp_obs), align_center=True)
            self._set(i, 5, self._fmt_ar(a_cargo), align_center=True)

        self.btn_copy.setEnabled(self.table.rowCount() > 0)

    def _copy_table_to_clipboard(self) -> None:
        # Formato: TAB separated (ideal para pegar en Excel/Sheets)
        # Encabezados pedidos (sin "Etiqueta")
        headers = ["Nº Referencia", "Nº Receta", "Fecha", "Hora", "Neto"]

        lines: list[str] = []
        lines.append("\t".join(headers))

        # Tomamos: ref(0) receta(1) fecha(2) hora(3) neto(4)
        for r in range(self.table.rowCount()):
            ref = self._item_text(r, 0)
            rec = self._item_text(r, 1)
            fecha = self._item_text(r, 2)
            hora = self._item_text(r, 3)
            neto = self._item_text(r, 4)
            lines.append("\t".join([ref, rec, fecha, hora, neto]))

        QGuiApplication.clipboard().setText("\n".join(lines))
        QMessageBox.information(self, "Copiado", "La tabla se copió al portapapeles.")

    def _item_text(self, row: int, col: int) -> str:
        it = self.table.item(row, col)
        return (it.text() if it else "").strip()

    @staticmethod
    def _fmt_ar(v: Decimal) -> str:
        # 69671,08 (coma decimal) como en tu ejemplo
        s = f"{Decimal(v):.2f}"
        return s.replace(".", ",")

    def _set(self, row: int, col: int, text: str, align_center: bool = False) -> None:
        it = QTableWidgetItem(text)
        it.setTextAlignment(
            (Qt.AlignmentFlag.AlignCenter if align_center else Qt.AlignmentFlag.AlignLeft)
            | Qt.AlignmentFlag.AlignVCenter
        )
        self.table.setItem(row, col, it)
