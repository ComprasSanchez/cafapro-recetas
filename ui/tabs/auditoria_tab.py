from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QSplitter, QScrollArea
)

from pathlib import Path

from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtGui import QPixmap


from app.db.session import session_scope
from app.service.recepcion_service import RecepcionService
from app.service.view_auditoria import ViewAuditoriaService
from ui.dialogs.recepcion_pick_dialog import RecepcionPickDialog
from ui.dialogs.auditoria_visual_dialog import AuditoriaVisualDialog


class AuditoriaTab(QWidget):
    def __init__(self, parent=None, creado_por_usuario_id: int | None = None):
        super().__init__(parent)
        self.creado_por_usuario_id = creado_por_usuario_id

        self._recepcion_id: int | None = None
        self._rows_view = []  # cache rows de la view

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        root.addWidget(self._build_header())
        root.addWidget(self._build_body(), 1)

    # -------------------------
    # HEADER (solo recepción)
    # -------------------------
    @staticmethod
    def _ro_line(text: str = "-") -> QLineEdit:
        le = QLineEdit(text)
        le.setReadOnly(True)
        le.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        le.setMinimumHeight(26)
        le.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return le

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("card")
        header.setMaximumHeight(70)

        grid = QGridLayout(header)
        grid.setContentsMargins(12, 10, 12, 10)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        lb_num = QLabel("N° Recepción:")
        self.in_numero = self._ro_line("-")
        self.in_numero.setFixedWidth(140)

        self.btn_pick_recepcion = QPushButton("…")
        self.btn_pick_recepcion.setFixedSize(32, 26)
        self.btn_pick_recepcion.clicked.connect(self._on_pick_recepcion)

        self.btn_visual = QPushButton("Auditoría visual")
        self.btn_visual.setFixedHeight(26)
        self.btn_visual.setEnabled(False)
        self.btn_visual.clicked.connect(self._on_open_auditoria_visual)

        # bloque compacto: input + botón
        num_box = QWidget()
        num_l = QHBoxLayout(num_box)
        num_l.setContentsMargins(0, 0, 0, 0)
        num_l.setSpacing(4)
        num_l.addWidget(self.in_numero, 1)
        num_l.addWidget(self.btn_pick_recepcion, 0)

        grid.addWidget(lb_num, 0, 0, Qt.AlignmentFlag.AlignRight)
        grid.addWidget(num_box, 0, 1)
        grid.addWidget(self.btn_visual, 0, 2, Qt.AlignmentFlag.AlignLeft)
        grid.setColumnStretch(3, 1)  # aire a la derecha

        return header

    def _on_pick_recepcion(self) -> None:
        dlg = RecepcionPickDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        rid = dlg.selected_recepcion_id()
        if rid:
            self._load_recepcion(rid)

    # -------------------------
    # BODY (tabla + panel lateral)
    # -------------------------
    def _build_body(self) -> QFrame:
        body = QFrame()
        body.setObjectName("card")

        lay = QVBoxLayout(body)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        self.lb_status = QLabel("Seleccioná una recepción para cargar la auditoría.")
        self.lb_status.setObjectName("muted")
        lay.addWidget(self.lb_status)

        # Split: izquierda tabla, derecha preview
        split = QSplitter(Qt.Orientation.Horizontal)
        lay.addWidget(split, 1)

        # -------- IZQUIERDA: TABLA --------
        left = QWidget()
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(0, 0, 0, 0)

        self.tbl = QTableWidget()
        self.tbl.setColumnCount(8)
        self.tbl.setHorizontalHeaderLabels([
            "Receta",
            "Referencia",
            "Lote",
            "Receta OK",
            "Archivo OK",
            "Reconocido",
            "Oficial",
            "Estado",
        ])
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSortingEnabled(True)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        # click por celda
        self.tbl.itemClicked.connect(self._on_item_clicked)
        self.tbl.itemSelectionChanged.connect(self._sync_visual_button_state)

        left_l.addWidget(self.tbl, 1)
        split.addWidget(left)

        # -------- DERECHA: PREVIEW (ANGOSTO + SCROLL) --------
        self.right_panel = QFrame()
        self.right_panel.setObjectName("card")
        rp_l = QVBoxLayout(self.right_panel)
        rp_l.setContentsMargins(8, 8, 8, 8)
        rp_l.setSpacing(8)

        title = QLabel("Vista previa")
        rp_l.addWidget(title)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)  # el contenido puede crecer
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.img_preview = QLabel("Sin imagen")
        self.img_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_preview.setScaledContents(False)  # IMPORTANTÍSIMO: no estirar/zoom automático

        self.scroll.setWidget(self.img_preview)
        rp_l.addWidget(self.scroll, 1)

        # Hacemos el panel derecho más angosto
        self.right_panel.setFixedWidth(500)  # ajustá a gusto
        split.addWidget(self.right_panel)

        # Proporción inicial (tabla grande, preview chico)
        split.setStretchFactor(0, 5)
        split.setStretchFactor(1, 1)
        self.img_preview.setScaledContents(False)
        self.scroll.setWidgetResizable(True)

        return body

    def _refresh_auditoria_table(self) -> None:
        if not self._recepcion_id:
            self.tbl.setRowCount(0)
            self.lb_status.setText("Seleccioná una recepción para cargar la auditoría.")
            return

        try:
            with session_scope() as s:
                self._rows_view = list(ViewAuditoriaService.list(s, self._recepcion_id))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar la auditoría:\n{e}")
            return

        self.lb_status.setText(f"Auditoría cargada: {len(self._rows_view)} registros")
        self._render_table(self._rows_view)

    def _render_table(self, rows: list) -> None:
        self.tbl.setSortingEnabled(False)
        self.tbl.setRowCount(len(rows))

        for i, r in enumerate(rows):
            # Estos nombres tienen que existir en tu view/model
            asociacion_id = getattr(r, "asociacion_id", None)
            recepcion_id = getattr(r, "recepcion_id", None)

            # Datos “visibles”
            numero_receta = getattr(r, "numero_receta", "") or ""
            numero_referencia = getattr(r, "numero_referencia", "") or ""
            nro_lote = getattr(r, "nro_lote", "") or ""

            # Flags
            existe_archivo = bool(getattr(r, "existe_archivo", False))
            existe_receta = bool(getattr(r, "existe_receta", False))

            # Importes
            importe_reconocido = getattr(r, "importe_reconocido", 0) or 0
            importe_oficial = getattr(r, "importe_oficial", 0) or 0

            # Estado receta (id + descripción)
            estado_receta_id = getattr(r, "estado_receta_id", None)
            estado_receta = getattr(r, "estado_receta", "") or ""

            frente_jpg = getattr(r, "frente_jpg", "")


            self._set_item(i, 0, str(numero_receta))
            self._set_item(i, 1, str(numero_referencia))
            self._set_item(i, 2, str(nro_lote))
            self._set_item(i, 3, "SI" if existe_receta else "NO")
            self._set_item(i, 4, "SI" if existe_archivo else "NO")
            self._set_item(i, 5, f"{float(importe_reconocido):.2f}")
            self._set_item(i, 6, f"{float(importe_oficial):.2f}")
            self._set_item(i, 7, str(estado_receta))

            # guardo archivo_id en la fila (celda 0)
            self.tbl.item(i, 0).setData(Qt.ItemDataRole.UserRole, asociacion_id)
            self.tbl.item(i, 0).setData(Qt.ItemDataRole.UserRole + 1, frente_jpg)

        self.tbl.setSortingEnabled(True)
        if rows:
            QTimer.singleShot(0, self._select_first_row)

    def _set_item(self, row: int, col: int, text: str) -> None:
        it = QTableWidgetItem(text)
        it.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.tbl.setItem(row, col, it)

    def _select_first_row(self) -> None:
        if self.tbl.rowCount() == 0:
            return

        self.tbl.setFocus()
        self.tbl.setCurrentCell(0, 0)
        self.tbl.selectRow(0)

        it = self.tbl.item(0, 0)
        if it:
            self.tbl.scrollToItem(it, QAbstractItemView.ScrollHint.PositionAtTop)

        self._on_item_clicked(self.tbl.item(0, 0))


    # -------------------------
    # click => panel derecho
    # -------------------------
    def _on_item_clicked(self, item: QTableWidgetItem) -> None:
        row = item.row()
        c0 = self.tbl.item(row, 0)

        asociacion_id = c0.data(Qt.ItemDataRole.UserRole)
        frente_jpg = (c0.data(Qt.ItemDataRole.UserRole + 1) or "").strip()

        if frente_jpg:
            self._set_preview_from_file(frente_jpg)
        else:
            self._show_preview_default()

        self.lb_status.setText(f"Seleccionado asociacion_id={asociacion_id}")
        self._sync_visual_button_state()

    def _show_preview_default(self) -> None:
        path = r"C:\Users\Usuario\Documents\Proyectos\cafapro-recetas\output\recepciones\5\pami_20260105132054010_f.jpg"
        self._set_preview_from_file(path)

    def _set_preview_from_file(self, path: str) -> None:
        try:
            p = Path(path)
            if not p.exists():
                raise FileNotFoundError(f"No existe: {p}")

            pil_img = Image.open(p).convert("RGB")

            vw = max(200, self.scroll.viewport().width() - 10)
            vh = max(200, self.scroll.viewport().height() - 10)

            # ✅ escala para que ENTRE (por ancho o por alto) pero sin deformar
            scale = min(vw / pil_img.width, vh / pil_img.height)

            # ✅ si querés que NO quede tan chica, poné un mínimo (ej 0.85)
            scale = max(scale, 0.30)

            new_w = int(pil_img.width * scale)
            new_h = int(pil_img.height * scale)
            pil_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            qimg = ImageQt(pil_img)
            pix = QPixmap.fromImage(qimg)

            self.img_preview.setPixmap(pix)
            self.img_preview.resize(pix.size())  # scroll toma tamaño real
            self.img_preview.setText("")
            self._last_preview_path = str(p)

        except Exception as e:
            self.img_preview.setPixmap(QPixmap())
            self.img_preview.setText(f"No se pudo cargar la imagen.\n{e}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if getattr(self, "_last_preview_path", None):
            self._set_preview_from_file(self._last_preview_path)
    # -------------------------
    # cargar recepción + refresh
    # -------------------------
    def _load_recepcion(self, recepcion_id: int) -> None:
        try:
            with session_scope() as s:
                rows = RecepcionService.list(s)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar la recepción:\n{e}")
            return

        rec = next((x for x in rows if x.recepcion_id == recepcion_id), None)
        if not rec:
            QMessageBox.warning(self, "Atención", "No se encontró la recepción seleccionada.")
            return

        self._recepcion_id = rec.recepcion_id
        self.in_numero.setText(str(rec.numero))

        self._refresh_auditoria_table()

    def _sync_visual_button_state(self) -> None:
        it = self.tbl.currentItem()
        if not it:
            self.btn_visual.setEnabled(False)
            return

        row = it.row()
        c0 = self.tbl.item(row, 0)
        if not c0:
            self.btn_visual.setEnabled(False)
            return

        asociacion_id = c0.data(Qt.ItemDataRole.UserRole)
        self.btn_visual.setEnabled(bool(asociacion_id))

    def _on_open_auditoria_visual(self) -> None:
        it = self.tbl.currentItem()
        if not it:
            return
        row = it.row()
        c0 = self.tbl.item(row, 0)
        asociacion_id = c0.data(Qt.ItemDataRole.UserRole) if c0 else None
        if not asociacion_id:
            return

        dlg = AuditoriaVisualDialog(asociacion_id=int(asociacion_id), parent=self)
        dlg.exec()


