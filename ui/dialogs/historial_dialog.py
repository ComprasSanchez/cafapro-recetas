from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QSplitter,
    QLabel, QPushButton, QFrame, QScrollArea,
    QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox
)

from app.db.session import session_scope
from ui.label.image_view_label import ImageViewer
from ui.usecase.auditoria_usecase import AuditoriaUseCase
from app.service.recetas.historial_receta_service import HistorialRecetaService


@dataclass(frozen=True)
class HistRow:
    receta_id: int
    vigente: bool
    auditor_username: Optional[str]
    estado_receta: Optional[str]
    auditado_en: Optional[str]
    cantidad_debitos: int


class HistorialDialog(QDialog):

    def __init__(self, *, archivo_id_actual: int, parent=None):
        super().__init__(parent)

        self._archivo_id_actual = int(archivo_id_actual)
        self._hist_rows: list[HistRow] = []
        self._current = None

        self.setWindowTitle("Historial de Auditorías")
        self.setMinimumSize(1000, 650)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        root.addWidget(self._build_body(), 1)
        root.addWidget(self._build_footer(), 0)

        self._load()

    # =========================================================
    # UI
    # =========================================================

    def _build_body(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)

        split = QSplitter(Qt.Horizontal)
        lay.addWidget(split, 1)

        split.addWidget(self._build_left())
        split.addWidget(self._build_right())

        split.setStretchFactor(0, 5)
        split.setStretchFactor(1, 4)
        return w

    def _build_left(self):
        box = QFrame()
        box.setObjectName("card")
        lay = QVBoxLayout(box)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)

        title = QLabel("Receta actual")
        title.setProperty("role", "subtitle")
        lay.addWidget(title)

        split = QSplitter(Qt.Horizontal)
        lay.addWidget(split, 1)

        self.img_frente = ImageViewer()
        self.img_frente.setText("Sin imagen (frente)")
        self.scroll_frente = QScrollArea()
        self.scroll_frente.setWidgetResizable(True)
        self.scroll_frente.setWidget(self.img_frente)
        split.addWidget(self.scroll_frente)

        self.img_dorso = ImageViewer()
        self.img_dorso.setText("Sin imagen (dorso)")
        self.scroll_dorso = QScrollArea()
        self.scroll_dorso.setWidgetResizable(True)
        self.scroll_dorso.setWidget(self.img_dorso)
        split.addWidget(self.scroll_dorso)

        return box

    def _build_right(self):
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        lay.addWidget(self._build_historial_block(), 2)
        lay.addWidget(self._build_detalle_block(), 3)

        return box

    def _build_historial_block(self):
        box = QFrame()
        box.setObjectName("card")
        lay = QVBoxLayout(box)
        lay.setContentsMargins(10, 10, 10, 10)

        title = QLabel("Auditorías")
        title.setProperty("role", "subtitle")
        lay.addWidget(title)

        self.tbl_hist = QTableWidget()
        self.tbl_hist.setColumnCount(4)
        self.tbl_hist.setHorizontalHeaderLabels(
            ["Fecha", "Auditor", "Estado", "Débitos"]
        )
        self.tbl_hist.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_hist.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_hist.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl_hist.verticalHeader().setVisible(False)
        self.tbl_hist.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tbl_hist.horizontalHeader().setStretchLastSection(True)

        self.tbl_hist.itemSelectionChanged.connect(self._on_selected)

        lay.addWidget(self.tbl_hist, 1)
        return box

    def _build_detalle_block(self):
        box = QFrame()
        box.setObjectName("card")
        lay = QVBoxLayout(box)
        lay.setContentsMargins(10, 10, 10, 10)

        title = QLabel("Detalle de auditoría")
        title.setProperty("role", "subtitle")
        lay.addWidget(title)

        self.lb_info = QLabel("—")
        self.lb_info.setWordWrap(True)
        lay.addWidget(self.lb_info)

        self.tbl_debitos = QTableWidget()
        self.tbl_debitos.setColumnCount(2)
        self.tbl_debitos.setHorizontalHeaderLabels(["Motivo", "Detalle"])
        self.tbl_debitos.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_debitos.verticalHeader().setVisible(False)
        self.tbl_debitos.horizontalHeader().setStretchLastSection(True)

        lay.addWidget(self.tbl_debitos, 1)
        return box

    def _build_footer(self):
        box = QFrame()
        lay = QVBoxLayout(box)
        btn = QPushButton("Cerrar")
        btn.clicked.connect(self.accept)
        lay.addWidget(btn)
        return box

    # =========================================================
    # LOAD
    # =========================================================

    def _load(self):
        try:
            with session_scope() as s:
                self._current = HistorialRecetaService.load_current_snapshot(
                    s, archivo_id=self._archivo_id_actual
                )

                rows = HistorialRecetaService.list_historial(
                    s, archivo_id=self._archivo_id_actual
                )

                self._hist_rows = [HistRow(**r) for r in rows]

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self._render_snapshot()
        self._render_historial()

        if self._hist_rows:
            self.tbl_hist.selectRow(0)
            self._apply_selected(self._hist_rows[0])

    # =========================================================
    # RENDER
    # =========================================================

    def _render_snapshot(self):
        if not self._current:
            return

        if self._current.frente_path:
            self._set_preview(self.img_frente, self.scroll_frente, self._current.frente_path)

        if self._current.dorso_path:
            self._set_preview(self.img_dorso, self.scroll_dorso, self._current.dorso_path)

    def _render_historial(self):
        self.tbl_hist.setRowCount(len(self._hist_rows))
        for i, r in enumerate(self._hist_rows):
            self.tbl_hist.setItem(i, 0, QTableWidgetItem(r.auditado_en or ""))
            self.tbl_hist.setItem(i, 1, QTableWidgetItem(r.auditor_username or ""))
            self.tbl_hist.setItem(i, 2, QTableWidgetItem(r.estado_receta or ""))
            self.tbl_hist.setItem(i, 3, QTableWidgetItem(str(r.cantidad_debitos)))

    def _on_selected(self):
        row = self.tbl_hist.currentRow()
        if row < 0:
            return
        self._apply_selected(self._hist_rows[row])

    def _apply_selected(self, r: HistRow):
        self.lb_info.setText(
            f"Auditor: {r.auditor_username or '-'}\n"
            f"Fecha: {r.auditado_en or '-'}\n"
            f"Estado: {r.estado_receta or '-'}"
        )

        with session_scope() as s:
            debs = HistorialRecetaService.list_debitos_for_receta(
                s, receta_id=r.receta_id
            )

        self.tbl_debitos.setRowCount(len(debs))
        for i, d in enumerate(debs):
            self.tbl_debitos.setItem(i, 0, QTableWidgetItem(d["motivo"]))
            self.tbl_debitos.setItem(i, 1, QTableWidgetItem(d["detalle"]))

    # =========================================================
    # PREVIEW
    # =========================================================

    def _set_preview(self, viewer, scroll, path):
        out = AuditoriaUseCase.load_preview_bytes(path=path, vw=800, vh=800)
        if not out.img_bytes:
            return

        pix = QPixmap()
        pix.loadFromData(out.img_bytes)
        viewer.set_pixmap(pix)
        QTimer.singleShot(0, lambda: viewer.fit_to(scroll.viewport().size()))