from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, QTimer, QThreadPool
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.label.image_view_label import ImageViewer
from ui.usecase.auditoria_usecase import AuditoriaUseCase
from ui.utils.worker import Worker


@dataclass(frozen=True)
class SearchHistRow:
    receta_id: int
    nro_receta: str
    nro_referencia: str
    recepcion_numero: str
    vigente: bool
    auditor_username: str
    estado_receta: str
    auditado_en: str
    cantidad_debitos: int


class HistorialSearchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(2)

        self._preview_cache: dict[tuple[str, int, int], bytes] = {}
        self._preview_req_id: dict[str, int] = {"F": 0, "D": 0}
        self._last_preview_path: dict[str, str | None] = {"F": None, "D": None}

        self._rows: list[SearchHistRow] = []

        self.setWindowTitle("Buscar receta")
        self.setMinimumSize(1280, 760)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        root.addWidget(self._build_search_bar(), 0)
        root.addWidget(self._build_body(), 1)
        root.addWidget(self._build_footer(), 0)

        self.showMaximized()

    def _build_search_bar(self) -> QWidget:
        box = QFrame()
        box.setObjectName("card")
        lay = QHBoxLayout(box)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)

        lay.addWidget(QLabel("N° receta:"), 0)
        self.in_receta = QLineEdit()
        self.in_receta.setPlaceholderText("Ej: 123456")
        self.in_receta.returnPressed.connect(self._search_by_receta)
        lay.addWidget(self.in_receta, 1)

        self.btn_search_receta = QPushButton("Buscar receta")
        self.btn_search_receta.setProperty("variant", "primary")
        self.btn_search_receta.setProperty("size", "md")
        self.btn_search_receta.clicked.connect(self._search_by_receta)
        lay.addWidget(self.btn_search_receta, 0)

        lay.addSpacing(14)

        lay.addWidget(QLabel("N° referencia:"), 0)
        self.in_referencia = QLineEdit()
        self.in_referencia.setPlaceholderText("Ej: 987654")
        self.in_referencia.returnPressed.connect(self._search_by_referencia)
        lay.addWidget(self.in_referencia, 1)

        self.btn_search_ref = QPushButton("Buscar referencia")
        self.btn_search_ref.setProperty("variant", "primary")
        self.btn_search_ref.setProperty("size", "md")
        self.btn_search_ref.clicked.connect(self._search_by_referencia)
        lay.addWidget(self.btn_search_ref, 0)

        return box

    def _build_body(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        self.lb_status = QLabel("Buscá por número de receta o número de referencia.")
        self.lb_status.setObjectName("muted")
        lay.addWidget(self.lb_status, 0)

        split = QSplitter(Qt.Horizontal)
        split.setChildrenCollapsible(False)
        lay.addWidget(split, 1)

        split.addWidget(self._build_left())
        split.addWidget(self._build_right())
        split.setStretchFactor(0, 5)
        split.setStretchFactor(1, 5)
        QTimer.singleShot(0, lambda: split.setSizes([1, 1]))

        return w

    def _build_left(self) -> QWidget:
        box = QFrame()
        box.setObjectName("card")
        lay = QVBoxLayout(box)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)

        title = QLabel("Resultados")
        title.setProperty("role", "subtitle")
        lay.addWidget(title)

        self.tbl_results = QTableWidget(0, 8)
        self.tbl_results.setHorizontalHeaderLabels(
            [
                "Recepción",
                "N° receta",
                "N° referencia",
                "Fecha",
                "Auditor",
                "Estado",
                "Débitos",
                "Vigente",
            ]
        )
        self.tbl_results.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_results.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_results.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_results.verticalHeader().setVisible(False)
        self.tbl_results.horizontalHeader().setStretchLastSection(True)
        self.tbl_results.itemSelectionChanged.connect(self._on_selected)
        lay.addWidget(self.tbl_results, 1)

        return box

    def _build_right(self) -> QWidget:
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        lay.addWidget(self._build_detalle_block(), 2)
        lay.addWidget(self._build_images_block(), 3)

        return box

    def _build_detalle_block(self) -> QWidget:
        box = QFrame()
        box.setObjectName("card")
        lay = QVBoxLayout(box)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)

        title = QLabel("Detalle de auditoría")
        title.setProperty("role", "subtitle")
        lay.addWidget(title)

        self.lb_info = QLabel("—")
        self.lb_info.setWordWrap(True)
        lay.addWidget(self.lb_info)

        self.tbl_debitos = QTableWidget(0, 5)
        self.tbl_debitos.setColumnCount(5)
        self.tbl_debitos.setHorizontalHeaderLabels(
            ["Motivo", "Detalle", "Reportó", "Vendedor", "Marcado en"]
        )
        self.tbl_debitos.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_debitos.verticalHeader().setVisible(False)
        self.tbl_debitos.horizontalHeader().setStretchLastSection(True)
        lay.addWidget(self.tbl_debitos, 1)

        return box

    def _build_images_block(self) -> QWidget:
        box = QFrame()
        box.setObjectName("card")
        lay = QVBoxLayout(box)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)

        title = QLabel("Imágenes")
        title.setProperty("role", "subtitle")
        lay.addWidget(title)

        split = QSplitter(Qt.Horizontal)
        split.setChildrenCollapsible(False)
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

    def _build_footer(self) -> QWidget:
        box = QFrame()
        lay = QHBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addStretch(1)

        btn_close = QPushButton("Cerrar")
        btn_close.setProperty("variant", "ghost")
        btn_close.setProperty("size", "md")
        btn_close.clicked.connect(self.accept)
        lay.addWidget(btn_close)
        return box

    def _search_by_receta(self) -> None:
        term = str(self.in_receta.text() or "").strip()
        if not term:
            QMessageBox.warning(self, "Atención", "Debés ingresar un número de receta.")
            return

        try:
            rows = AuditoriaUseCase.search_historial_by_numero_receta(nro_receta=term)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self._apply_search_results(rows=rows, mode="receta", term=term)

    def _search_by_referencia(self) -> None:
        term = str(self.in_referencia.text() or "").strip()
        if not term:
            QMessageBox.warning(self, "Atención", "Debés ingresar un número de referencia.")
            return

        try:
            rows = AuditoriaUseCase.search_historial_by_numero_referencia(nro_referencia=term)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self._apply_search_results(rows=rows, mode="referencia", term=term)

    def _apply_search_results(self, *, rows: list[dict], mode: str, term: str) -> None:
        self._rows = [
            SearchHistRow(
                receta_id=int(r.get("receta_id") or 0),
                nro_receta=str(r.get("nro_receta") or ""),
                nro_referencia=str(r.get("nro_referencia") or ""),
                recepcion_numero=str(r.get("recepcion_numero") or "-"),
                vigente=bool(r.get("vigente", False)),
                auditor_username=str(r.get("auditor_username") or ""),
                estado_receta=str(r.get("estado_receta") or ""),
                auditado_en=str(r.get("auditado_en") or ""),
                cantidad_debitos=int(r.get("cantidad_debitos") or 0),
            )
            for r in rows
            if int(r.get("receta_id") or 0) > 0
        ]

        label = "receta" if mode == "receta" else "referencia"
        self.lb_status.setText(f"Se encontraron {len(self._rows)} resultados para {label} {term}.")
        self._render_results()

        if self._rows:
            self.tbl_results.blockSignals(True)
            self.tbl_results.selectRow(0)
            self.tbl_results.blockSignals(False)
            self._apply_selected(self._rows[0])
        else:
            self.tbl_debitos.setRowCount(0)
            self.lb_info.setText("Sin resultados.")
            self._reset_images()

    def _render_results(self) -> None:
        self.tbl_results.setRowCount(len(self._rows))
        for i, r in enumerate(self._rows):
            self.tbl_results.setItem(i, 0, QTableWidgetItem(r.recepcion_numero))
            self.tbl_results.setItem(i, 1, QTableWidgetItem(r.nro_receta))
            self.tbl_results.setItem(i, 2, QTableWidgetItem(r.nro_referencia))
            self.tbl_results.setItem(i, 3, QTableWidgetItem(r.auditado_en))
            self.tbl_results.setItem(i, 4, QTableWidgetItem(r.auditor_username))
            self.tbl_results.setItem(i, 5, QTableWidgetItem(r.estado_receta))
            self.tbl_results.setItem(i, 6, QTableWidgetItem(str(r.cantidad_debitos)))
            self.tbl_results.setItem(i, 7, QTableWidgetItem("Sí" if r.vigente else "No"))

    def _on_selected(self) -> None:
        row = self.tbl_results.currentRow()
        if row < 0 or row >= len(self._rows):
            return
        self._apply_selected(self._rows[row])

    def _apply_selected(self, r: SearchHistRow) -> None:
        self.lb_info.setText(
            f"Recepción: {r.recepcion_numero}\n"
            f"N° receta: {r.nro_receta or '-'}\n"
            f"N° referencia: {r.nro_referencia or '-'}\n"
            f"Auditor: {r.auditor_username or '-'}\n"
            f"Fecha: {r.auditado_en or '-'}\n"
            f"Estado: {r.estado_receta or '-'}"
        )

        try:
            debs, imgs = AuditoriaUseCase.load_historial_detail(receta_id=r.receta_id)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self.tbl_debitos.setRowCount(len(debs))
        for i, d in enumerate(debs):
            self.tbl_debitos.setItem(i, 0, QTableWidgetItem(str(d.get("motivo") or "")))
            self.tbl_debitos.setItem(i, 1, QTableWidgetItem(str(d.get("detalle") or "")))
            self.tbl_debitos.setItem(i, 2, QTableWidgetItem(str(d.get("reportado_por") or "-")))
            self.tbl_debitos.setItem(i, 3, QTableWidgetItem(str(d.get("vendedor") or "-")))
            self.tbl_debitos.setItem(i, 4, QTableWidgetItem(str(d.get("marcado_en") or "-")))

        if imgs.get("frente"):
            self._set_preview("F", self.img_frente, self.scroll_frente, str(imgs["frente"]))
        else:
            self.img_frente.setText("Sin imagen (frente)")
            self.img_frente.set_pixmap(None)

        if imgs.get("dorso"):
            self._set_preview("D", self.img_dorso, self.scroll_dorso, str(imgs["dorso"]))
        else:
            self.img_dorso.setText("Sin imagen (dorso)")
            self.img_dorso.set_pixmap(None)

    def _set_preview(self, lado: str, viewer: ImageViewer, scroll: QScrollArea, path: str) -> None:
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

        self._preview_req_id[lado] += 1
        req_id = self._preview_req_id[lado]

        viewer.setText("Cargando…")
        viewer.set_pixmap(None)

        worker = Worker(
            self._load_preview_worker,
            lado=lado,
            raw=raw,
            vw=vw,
            vh=vh,
            req_id=req_id,
        )
        worker.signals.finished.connect(self._apply_preview_worker)
        worker.signals.error.connect(lambda err: self._on_preview_error(lado, err))
        self._pool.start(worker)

    def _load_preview_worker(self, *, lado: str, raw: str, vw: int, vh: int, req_id: int) -> dict:
        out = AuditoriaUseCase.load_preview_bytes(path=raw, vw=vw, vh=vh)
        return {
            "lado": lado,
            "png_bytes": out.img_bytes,
            "req_id": req_id,
            "raw": raw,
            "vw": vw,
            "vh": vh,
        }

    def _apply_preview_worker(self, out: dict) -> None:
        lado = out["lado"]
        req_id = int(out["req_id"])
        raw = str(out["raw"])
        vw = int(out["vw"])
        vh = int(out["vh"])

        if req_id != self._preview_req_id.get(lado):
            return

        if self._last_preview_path.get(lado) != raw:
            return

        png_bytes = out.get("png_bytes")
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

    def _on_preview_error(self, lado: str, err_text: str) -> None:
        viewer = self.img_frente if lado == "F" else self.img_dorso
        viewer.set_pixmap(None)
        viewer.setText("No se pudo cargar la imagen")

    def _reset_images(self) -> None:
        self._last_preview_path["F"] = None
        self._last_preview_path["D"] = None
        self.img_frente.set_pixmap(None)
        self.img_frente.setText("Sin imagen (frente)")
        self.img_dorso.set_pixmap(None)
        self.img_dorso.setText("Sin imagen (dorso)")
