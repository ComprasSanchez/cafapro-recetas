from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import Qt, QTimer, QThreadPool
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QSplitter,
    QLabel, QPushButton, QFrame, QScrollArea,
    QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox
)

from ui.label.image_view_label import ImageViewer
from ui.usecase.auditoria_usecase import AuditoriaUseCase
from ui.utils.worker import Worker


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

        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(2)

        self._preview_cache: dict[tuple[str, int, int], bytes] = {}
        self._preview_req_id: dict[str, int] = {"F": 0, "D": 0}
        self._last_preview_path: dict[str, str | None] = {"F": None, "D": None}

        self._archivo_id_actual = int(archivo_id_actual)
        self._hist_rows: list[HistRow] = []
        self._current = None

        self.setWindowTitle("Historial de Auditorías")
        self.setMinimumSize(1000, 650)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        root.addWidget(self._build_body(), 1)
        root.addWidget(self._build_footer(), 0)

        self.showMaximized()

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
        self.tbl_hist.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_hist.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_hist.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_hist.verticalHeader().setVisible(False)
        self.tbl_hist.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
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
        self.tbl_debitos.setColumnCount(5)
        self.tbl_debitos.setHorizontalHeaderLabels(
            ["Motivo", "Detalle", "Reportó", "Vendedor", "Marcado en"]
        )
        self.tbl_debitos.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_debitos.verticalHeader().setVisible(False)
        self.tbl_debitos.horizontalHeader().setStretchLastSection(True)

        lay.addWidget(self.tbl_debitos, 1)
        return box

    def _build_footer(self):
        box = QFrame()
        lay = QVBoxLayout(box)
        btn = QPushButton("Cerrar")
        btn.setProperty("variant", "ghost")
        btn.setProperty("size", "md")
        btn.clicked.connect(self.accept)
        lay.addWidget(btn)
        return box

    # =========================================================
    # LOAD
    # =========================================================

    def _load(self):
        try:
            self._current = AuditoriaUseCase.load_historial_snapshot(
                archivo_id=self._archivo_id_actual,
            )

            rows = AuditoriaUseCase.load_historial_rows(
                archivo_id=self._archivo_id_actual,
            )

            self._hist_rows = [HistRow(**r) for r in rows]

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self._render_snapshot()
        self._render_historial()

        if self._hist_rows:
            self.tbl_hist.blockSignals(True)
            self.tbl_hist.selectRow(0)
            self.tbl_hist.blockSignals(False)
            self._apply_selected(self._hist_rows[0])

    # =========================================================
    # RENDER
    # =========================================================

    def _render_snapshot(self):
        if not self._current:
            return

        if self._current.frente_path:
            self._set_preview(
                "F",
                self.img_frente,
                self.scroll_frente,
                self._current.frente_path
            )
        else:
            self.img_frente.setText("Sin imagen (frente)")
            self.img_frente.set_pixmap(None)

        if self._current.dorso_path:
            self._set_preview(
                "D",
                self.img_dorso,
                self.scroll_dorso,
                self._current.dorso_path
            )
        else:
            self.img_dorso.setText("Sin imagen (dorso)")
            self.img_dorso.set_pixmap(None)

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

        debs, imgs = AuditoriaUseCase.load_historial_detail(receta_id=r.receta_id)

        # 🔹 Render débitos
        self.tbl_debitos.setRowCount(len(debs))
        for i, d in enumerate(debs):
            self.tbl_debitos.setItem(i, 0, QTableWidgetItem(str(d.get("motivo") or "")))
            self.tbl_debitos.setItem(i, 1, QTableWidgetItem(str(d.get("detalle") or "")))
            self.tbl_debitos.setItem(i, 2, QTableWidgetItem(str(d.get("reportado_por") or "-")))
            self.tbl_debitos.setItem(i, 3, QTableWidgetItem(str(d.get("vendedor") or "-")))
            self.tbl_debitos.setItem(i, 4, QTableWidgetItem(str(d.get("marcado_en") or "-")))

        # 🔹 Render imágenes async
        if imgs.get("frente"):
            self._set_preview("F", self.img_frente, self.scroll_frente, imgs["frente"])
        else:
            self.img_frente.setText("Sin imagen (frente)")
            self.img_frente.set_pixmap(None)

        if imgs.get("dorso"):
            self._set_preview("D", self.img_dorso, self.scroll_dorso, imgs["dorso"])
        else:
            self.img_dorso.setText("Sin imagen (dorso)")
            self.img_dorso.set_pixmap(None)

    # =========================================================
    # PREVIEW
    # =========================================================

    def _set_preview(self, lado: str, viewer, scroll, path: str):

        raw = (path or "").strip()
        if not raw:
            viewer.set_pixmap(None)
            viewer.setText("Sin imagen")
            return

        if self._last_preview_path.get(lado) == raw:
            return

        self._last_preview_path[lado] = raw

        vw = max(200, scroll.viewport().width() - 12)
        vh = max(200, scroll.viewport().height() - 12)

        cache_key = (raw, vw, vh)
        if cache_key in self._preview_cache:
            png_bytes = self._preview_cache[cache_key]
            pix = QPixmap()
            if pix.loadFromData(png_bytes):
                viewer.setText("")
                viewer.set_pixmap(pix)
                QTimer.singleShot(0, lambda: viewer.fit_to(scroll.viewport().size()))
                return

        # 🔥 async
        self._preview_req_id[lado] += 1
        req_id = self._preview_req_id[lado]

        viewer.setText("Cargando…")
        viewer.set_pixmap(None)

        w = Worker(
            self._load_preview_worker,
            lado=lado,
            raw=raw,
            vw=vw,
            vh=vh,
            req_id=req_id
        )
        w.signals.finished.connect(self._apply_preview_worker)
        self._pool.start(w)

    def _load_preview_worker(self, *, lado: str, raw: str, vw: int, vh: int, req_id: int):

        out = AuditoriaUseCase.load_preview_bytes(path=raw, vw=vw, vh=vh)

        return {
            "lado": lado,
            "png_bytes": out.img_bytes,
            "req_id": req_id,
            "raw": raw,
            "vw": vw,
            "vh": vh
        }

    def _apply_preview_worker(self, out: dict):

        lado = out["lado"]
        req_id = out["req_id"]
        raw = out["raw"]
        vw = out["vw"]
        vh = out["vh"]

        if req_id != self._preview_req_id.get(lado):
            return

        if self._last_preview_path.get(lado) != raw:
            return

        png_bytes = out["png_bytes"]
        if not png_bytes:
            return

        self._preview_cache[(raw, vw, vh)] = png_bytes

        viewer = self.img_frente if lado == "F" else self.img_dorso
        scroll = self.scroll_frente if lado == "F" else self.scroll_dorso

        pix = QPixmap()
        if not pix.loadFromData(png_bytes):
            return

        viewer.setText("")
        viewer.set_pixmap(pix)
        QTimer.singleShot(0, lambda: viewer.fit_to(scroll.viewport().size()))

