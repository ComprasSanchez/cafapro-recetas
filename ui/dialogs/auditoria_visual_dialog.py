from __future__ import annotations

from datetime import date
from pathlib import Path
from decimal import Decimal

from PySide6.QtCore import Qt, QTimer, QDate
from PySide6.QtGui import QPixmap, QColor, QBrush, QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QSplitter,
    QLabel, QPushButton, QFrame, QScrollArea, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox,
    QWidget, QCheckBox, QInputDialog, QDateEdit
)

from app.db.models import EstadoTroquelEnum
from app.db.session import session_scope
from app.service.auditoria_visual_service import AuditoriaVisualService, AuditoriaVisualData
from app.service.debitos_service import DebitoInput, DebitosService
from app.service.motivos_debito_service import MotivosDebitosService
from app.service.recetas_service import RecetaService
from ui.dialogs.estado_seguimeinto_pick_dialog import EstadoSeguimientoPickDialog
from ui.label.image_view_label import ImageViewer
from ui.label.clickable_label import ClickableLabel
from ui.dialogs.vendedor_pick_dialog import VendedorPickDialog


class AuditoriaVisualDialog(QDialog):
    def __init__(self, asociacion_id: int, parent=None, creado_por_usuario_id=None):
        super().__init__(parent)
        self.asociacion_id = asociacion_id
        self.creado_por_usuario_id = creado_por_usuario_id
        self.data: AuditoriaVisualData | None = None

        self._last_preview_path: str | None = None
        self._current_lado = "F"
        self._vendedor_id: int | None = None
        self._selected_debitos: dict[int, str | None] = {}

        self.setWindowTitle("Auditoría Visual")
        self.setModal(True)
        self.setWindowFlags(
            Qt.Window
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
            | Qt.WindowCloseButtonHint
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        root.addWidget(self._build_body(), 1)

        self._load()

    # -------------------------
    # UI: Body split
    # -------------------------
    def _build_body(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        split = QSplitter(Qt.Orientation.Horizontal)
        lay.addWidget(split, 1)

        # LEFT
        left = QWidget()
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(0, 0, 0, 0)
        left_l.setSpacing(10)

        left_l.addWidget(self._build_image_block(), 5)
        left_l.addWidget(self._build_tables_block(), 2)
        split.addWidget(left)

        # RIGHT
        right = QWidget()
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(0, 0, 0, 0)
        right_l.setSpacing(10)

        right_l.addWidget(self._build_right_header(), 0)
        right_l.addWidget(self._build_vendedor_field(), 0)
        right_l.addWidget(self._build_debitos_block(), 1)
        right_l.addWidget(self._build_resumen_block(), 0)
        right_l.addWidget(self._build_actions_block(), 0)

        split.addWidget(right)

        split.setStretchFactor(0, 6)
        split.setStretchFactor(1, 3)

        return w

    # -------------------------
    # Image block
    # -------------------------
    def _build_image_block(self) -> QFrame:
        box = QFrame()
        box.setObjectName("card")
        lay = QVBoxLayout(box)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        toggle = QHBoxLayout()
        toggle.setContentsMargins(0, 0, 0, 0)
        toggle.setSpacing(6)

        self.btn_frente = QPushButton("Frente")
        self.btn_frente.setCheckable(True)
        self.btn_frente.clicked.connect(lambda: self._show_side("F"))

        self.btn_dorso = QPushButton("Dorso")
        self.btn_dorso.setCheckable(True)
        self.btn_dorso.clicked.connect(lambda: self._show_side("D"))

        toggle.addWidget(self.btn_frente, 0)
        toggle.addWidget(self.btn_dorso, 0)
        toggle.addStretch(1)

        lay.addLayout(toggle)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.img_preview = ImageViewer()
        self.img_preview.setText("Sin imagen")
        self.scroll.setWidget(self.img_preview)

        lay.addWidget(self.scroll, 1)
        return box

    # -------------------------
    # Tables block
    # -------------------------
    def _build_tables_block(self) -> QWidget:
        w = QWidget()
        root = QVBoxLayout(w)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        split = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(split, 1)

        # TROQUELES
        left = QFrame()
        left.setObjectName("card")
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(12, 12, 12, 12)
        left_l.setSpacing(8)

        lb_t = QLabel("Troqueles")
        lb_t.setProperty("role", "subtitle")
        left_l.addWidget(lb_t, 0)

        self.tbl_troqueles = QTableWidget()
        self.tbl_troqueles.setColumnCount(7)  # ✅ FIX: ahora sí hay columna Estado
        self.tbl_troqueles.setHorizontalHeaderLabels([
            "Código barra", "Droga", "Presentación", "Alfabeta", "Monto", "Cant.", "Estado"
        ])
        self._setup_table(self.tbl_troqueles)
        left_l.addWidget(self.tbl_troqueles, 1)

        split.addWidget(left)

        # ARCHIVO DETALLE
        right = QFrame()
        right.setObjectName("card")
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(12, 12, 12, 12)
        right_l.setSpacing(8)

        lb_a = QLabel("Archivo detalle")
        lb_a.setProperty("role", "subtitle")
        right_l.addWidget(lb_a, 0)

        self.tbl_arch_det = QTableWidget()
        self.tbl_arch_det.setColumnCount(9)
        self.tbl_arch_det.setHorizontalHeaderLabels([
            "CodMedic", "Nombre", "Presentación", "Estado", "Nro Aut", "Cant.", "Imp Neto", "Imp OBS", "Desc"
        ])
        self._setup_table(self.tbl_arch_det)
        right_l.addWidget(self.tbl_arch_det, 1)

        split.addWidget(right)

        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 2)

        return w

    @staticmethod
    def _setup_table(tbl: QTableWidget) -> None:
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tbl.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        tbl.setAlternatingRowColors(True)
        tbl.verticalHeader().setVisible(False)

        hh = tbl.horizontalHeader()
        hh.setStretchLastSection(True)
        hh.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        hh.setHighlightSections(False)

    # -------------------------
    # Debitos block
    # -------------------------
    def _build_debitos_block(self) -> QFrame:
        box = QFrame()
        box.setObjectName("card")
        lay = QVBoxLayout(box)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        title = QLabel("Motivos débito")
        title.setProperty("role", "subtitle")
        lay.addWidget(title, 0)

        self.motivos_scroll = QScrollArea()
        self.motivos_scroll.setWidgetResizable(True)

        self.motivos_container = QWidget()
        self.motivos_layout = QVBoxLayout(self.motivos_container)
        self.motivos_layout.setContentsMargins(0, 0, 0, 0)
        self.motivos_layout.setSpacing(6)
        self.motivos_layout.addStretch(1)

        self.motivos_scroll.setWidget(self.motivos_container)
        lay.addWidget(self.motivos_scroll, 1)

        return box

    def _build_right_header(self) -> QFrame:
        box = QFrame()
        box.setObjectName("card")
        lay = QHBoxLayout(box)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(12)

        self.lb_big = QLabel("—")
        self.lb_big.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lb_big.setMinimumWidth(120)
        self.lb_big.setMinimumHeight(70)
        self.lb_big.setFrameShape(QFrame.Shape.StyledPanel)
        lay.addWidget(self.lb_big, 0)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        lb_p = QLabel("Prescripción")
        grid.addWidget(lb_p, 0, 0, alignment=Qt.AlignmentFlag.AlignRight)

        self.in_prescripcion = QDateEdit()
        self.in_prescripcion.setCalendarPopup(True)
        self.in_prescripcion.setDisplayFormat("dd/MM/yyyy")
        self.in_prescripcion.setMinimumHeight(28)
        self.in_prescripcion.setDate(QDate.currentDate())
        grid.addWidget(self.in_prescripcion, 0, 1)

        def mk_row_label(r: int, title: str) -> QLabel:
            lb_t = QLabel(title)
            lb_v = QLabel("—")
            grid.addWidget(lb_t, r, 0, alignment=Qt.AlignmentFlag.AlignRight)
            grid.addWidget(lb_v, r, 1)
            return lb_v

        self.lb_emision_aut = mk_row_label(1, "Emisión Aut")
        self.lb_venta = mk_row_label(2, "Venta")
        self.lb_autorizacion = mk_row_label(3, "Autorización")

        lay.addLayout(grid, 1)
        return box

    def _build_vendedor_field(self) -> QFrame:
        box = QFrame()
        box.setObjectName("card")
        lay = QHBoxLayout(box)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(8)

        lay.addWidget(QLabel("Vendedor:"), 0)

        self.lb_vendedor = ClickableLabel("— Seleccioná —")
        self.lb_vendedor.clicked.connect(self._pick_vendedor)

        self.lb_vendedor.setFrameShape(QFrame.Shape.StyledPanel)
        self.lb_vendedor.setMinimumHeight(30)
        self.lb_vendedor.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        lay.addWidget(self.lb_vendedor, 1)
        return box

    def _build_resumen_block(self) -> QFrame:
        box = QFrame()
        box.setObjectName("card")
        lay = QHBoxLayout(box)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        self.card_a_cargo, self.lb_a_cargo = self._mk_resumen_card("A cargo OS")
        self.card_pvp_pami, self.lb_imp_obs = self._mk_resumen_card("PVP Pami")
        self.card_pvp, self.lb_imp_neto = self._mk_resumen_card("PVP")

        lay.addWidget(self.card_a_cargo, 1)
        lay.addWidget(self.card_pvp_pami, 1)
        lay.addWidget(self.card_pvp, 1)

        return box

    def _mk_resumen_card(self, title: str) -> tuple[QFrame, QLabel]:
        card = QFrame()
        card.setObjectName("card")
        v = QVBoxLayout(card)
        v.setContentsMargins(12, 10, 12, 10)
        v.setSpacing(2)

        lb_title = QLabel(title)
        lb_title.setObjectName("muted")

        lb_value = QLabel("—")
        f2 = QFont()
        f2.setPointSize(15)
        f2.setBold(True)
        lb_value.setFont(f2)

        v.addWidget(lb_title, 0)
        v.addWidget(lb_value, 0)
        return card, lb_value

    def _build_actions_block(self) -> QFrame:
        box = QFrame()
        box.setObjectName("card")
        lay = QHBoxLayout(box)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(8)

        lay.addStretch(1)

        self.btn_finalizar = QPushButton("Finalizar")
        self.btn_finalizar.setProperty("variant", "primary")
        self.btn_finalizar.setMinimumHeight(34)
        self.btn_finalizar.clicked.connect(self._on_finalizar)

        lay.addWidget(self.btn_finalizar, 0)
        return box

    # -------------------------
    # Data load + render
    # -------------------------
    def _load(self) -> None:
        try:
            with session_scope() as s:
                self.data = AuditoriaVisualService.load_by_asociacion_id(s, self.asociacion_id)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar la Auditoría Visual:\n{e}")
            self.data = None
            return

        self._render_all()

    def _render_all(self) -> None:
        assert self.data is not None

        fr = (getattr(self.data.receta, "ubicacion_frente", None) or "").strip()
        dr = (getattr(self.data.receta, "ubicacion_dorso", None) or "").strip()

        self.btn_frente.setEnabled(bool(fr))
        self.btn_dorso.setEnabled(bool(dr))

        if fr:
            self._current_lado = "F"
            self.btn_frente.setChecked(True)
            self.btn_dorso.setChecked(False)
            self._set_preview_and_fit(fr)
        elif dr:
            self._current_lado = "D"
            self.btn_dorso.setChecked(True)
            self.btn_frente.setChecked(False)
            self._set_preview_and_fit(dr)
        else:
            self._current_lado = "F"
            self._clear_preview("Sin imagen")

        self._refresh_motivos_catalogo()
        self._render_troqueles()
        self._render_archivo_detalle()

        imp_neto = Decimal(str(getattr(self.data.archivo, "importe_neto", 0) or 0))
        imp_obs = Decimal(str(getattr(self.data.archivo, "importe_obs", 0) or 0))
        a_cargo = Decimal(str(getattr(self.data.archivo, "a_cargo_entidad", 0) or 0))

        fp = getattr(self.data.receta, "fecha_prescripcion", None)
        self.in_prescripcion.setDate(QDate(fp.year, fp.month, fp.day) if fp else QDate.currentDate())

        self.lb_big.setText(str(getattr(self.data.archivo, "orden_lote", "") or "—"))
        self.lb_venta.setText(str(getattr(self.data.archivo, "fecha", "") or "—"))
        self.lb_emision_aut.setText("—")
        self.lb_autorizacion.setText(self.in_prescripcion.text())

        self.lb_a_cargo.setText(self._fmt_money(a_cargo))
        self.lb_imp_obs.setText(self._fmt_money(imp_obs))
        self.lb_imp_neto.setText(self._fmt_money(imp_neto))

    def _render_troqueles(self) -> None:
        assert self.data is not None
        rows = self.data.troqueles

        self.tbl_troqueles.setRowCount(len(rows))
        for i, t in enumerate(rows):
            estado = t.estado

            self._set_cell(self.tbl_troqueles, i, 0, str(getattr(t, "codigo_barra", "") or ""))
            self._set_cell(self.tbl_troqueles, i, 1, str(getattr(t, "droga", "") or ""))
            self._set_cell(self.tbl_troqueles, i, 2, str(getattr(t, "presentacion", "") or ""))
            self._set_cell(self.tbl_troqueles, i, 3, str(getattr(t, "code_alfabeta", "") or ""))
            self._set_cell(self.tbl_troqueles, i, 4, self._fmt_money(Decimal(str(getattr(t, "monto", 0) or 0))))
            self._set_cell(self.tbl_troqueles, i, 5, str(getattr(t, "cantidad", "") or ""))
            self._set_cell(self.tbl_troqueles, i, 6, estado)

            # Si querés mantener colores, dejalo; si querés monocromo total, comentá esto.
            color = None
            if estado == EstadoTroquelEnum.V:
                color = QColor(17, 151, 59)
            elif estado == EstadoTroquelEnum.A:
                color = QColor(228, 245, 44)
            elif estado == "R":
                color = QColor(220, 220, 220)
            print(color)
            if color is not None:
                brush = QBrush(color)
                for c in range(self.tbl_troqueles.columnCount()):
                    it = self.tbl_troqueles.item(i, c)
                    if it:
                        it.setData(Qt.BackgroundRole, brush)

    def _render_archivo_detalle(self) -> None:
        assert self.data is not None
        rows = self.data.archivo_detalles

        self.tbl_arch_det.setRowCount(len(rows))
        for i, d in enumerate(rows):
            self._set_cell(self.tbl_arch_det, i, 0, str(getattr(d, "cod_medic", "") or ""))
            self._set_cell(self.tbl_arch_det, i, 1, str(getattr(d, "nombre", "") or ""))
            self._set_cell(self.tbl_arch_det, i, 2, str(getattr(d, "presentacion", "") or ""))
            self._set_cell(self.tbl_arch_det, i, 3, str(getattr(d, "estado", "") or ""))
            self._set_cell(self.tbl_arch_det, i, 4, str(getattr(d, "nro_autorizacion", "") or ""))
            self._set_cell(self.tbl_arch_det, i, 5, str(getattr(d, "cantidad", "") or ""))
            self._set_cell(self.tbl_arch_det, i, 6, self._fmt_money(Decimal(str(getattr(d, "importe_neto", 0) or 0))))
            self._set_cell(self.tbl_arch_det, i, 7, self._fmt_money(Decimal(str(getattr(d, "importe_obs", 0) or 0))))
            self._set_cell(self.tbl_arch_det, i, 8, str(getattr(d, "descuento", "") or ""))

    # -------------------------
    # Preview controls
    # -------------------------
    def _show_side(self, lado: str) -> None:
        if not self.data:
            return

        fr = (getattr(self.data.receta, "ubicacion_frente", None) or "").strip()
        dr = (getattr(self.data.receta, "ubicacion_dorso", None) or "").strip()

        if lado == "F":
            self.btn_frente.setChecked(True)
            self.btn_dorso.setChecked(False)
            self._current_lado = "F"
            self._set_preview_and_fit(fr) if fr else self._clear_preview("Sin imagen (frente)")
        else:
            self.btn_dorso.setChecked(True)
            self.btn_frente.setChecked(False)
            self._current_lado = "D"
            self._set_preview_and_fit(dr) if dr else self._clear_preview("Sin imagen (dorso)")

        self._refresh_motivos_catalogo()

    def _clear_preview(self, text: str) -> None:
        self.img_preview.setPixmap(QPixmap())
        self.img_preview.setText(text)
        self._last_preview_path = None

    def _set_preview_and_fit(self, path: str) -> None:
        p = Path(path)
        if not p.exists():
            self.img_preview.set_pixmap(None)
            self.img_preview.setText(f"No existe: {p}")
            self._last_preview_path = None
            return

        pix = QPixmap(str(p))
        if pix.isNull():
            self.img_preview.set_pixmap(None)
            self.img_preview.setText("No se pudo leer la imagen.")
            self._last_preview_path = None
            return

        self.img_preview.setText("")
        self.img_preview.set_pixmap(pix)
        self._last_preview_path = str(p)

        QTimer.singleShot(0, lambda: self.img_preview.fit_to(self.scroll.viewport().size()))

    # -------------------------
    # Motivos
    # -------------------------
    def _refresh_motivos_catalogo(self) -> None:
        if not self.data:
            return

        with session_scope() as s:
            motivos = MotivosDebitosService.list_motivos(s, self._current_lado)

        while self.motivos_layout.count() > 1:
            item = self.motivos_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        for m in motivos:
            motivo_id = m.motivo_debito_id

            row = QWidget()
            row_l = QHBoxLayout(row)
            row_l.setContentsMargins(0, 0, 0, 0)
            row_l.setSpacing(8)

            cb = QCheckBox()
            cb.setProperty("motivo_id", motivo_id)
            cb.setProperty("lado", str(m.lado))
            cb.setChecked(motivo_id in self._selected_debitos)
            cb.stateChanged.connect(self._on_motivo_checkbox_changed)

            lb = QLabel(str(m.descripcion))
            lb.setWordWrap(True)
            lb.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
            lb.setCursor(Qt.CursorShape.PointingHandCursor)

            # click en el texto = toggle checkbox
            def _toggle(_evt, _cb=cb):
                _cb.setChecked(not _cb.isChecked())

            lb.mousePressEvent = _toggle

            row_l.addWidget(cb, 0, Qt.AlignmentFlag.AlignTop)
            row_l.addWidget(lb, 1)

            self.motivos_layout.insertWidget(self.motivos_layout.count() - 1, row)

    def _on_motivo_checkbox_changed(self, state: int) -> None:
        cb = self.sender()
        if not isinstance(cb, QCheckBox):
            return

        motivo_id = cb.property("motivo_id")
        if not motivo_id:
            return
        motivo_id = int(motivo_id)

        if state != Qt.CheckState.Checked.value:
            self._selected_debitos.pop(motivo_id, None)
            return

        prev = self._selected_debitos.get(motivo_id) or ""
        detalle, ok = QInputDialog.getText(
            self,
            "Detalle del débito",
            "Detalle (opcional):",
            text=prev,
        )

        if not ok:
            cb.blockSignals(True)
            cb.setChecked(False)
            cb.blockSignals(False)
            self._selected_debitos.pop(motivo_id, None)
            return

        self._selected_debitos[motivo_id] = (detalle.strip() or None)

    # -------------------------
    # Vendedor
    # -------------------------
    def _pick_vendedor(self) -> None:
        dlg = VendedorPickDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        vid = dlg.selected_vendedor_id()
        if not vid:
            return

        try:
            with session_scope() as s:
                from app.db.models import Vendedores
                v = s.get(Vendedores, int(vid))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar el vendedor:\n{e}")
            return

        if not v:
            return

        self._vendedor_id = int(v.vendedor_id)
        self.lb_vendedor.setText(str(getattr(v, "descripcion", "") or "—"))
        self.lb_vendedor.setToolTip(f"Código: {getattr(v, 'codigo', '')}")

    # -------------------------
    # Finalizar
    # -------------------------
    def _on_finalizar(self) -> None:
        if not self.data:
            return

        if not self._vendedor_id:
            QMessageBox.warning(self, "Falta vendedor", "Tenés que seleccionar un vendedor para finalizar.")
            return

        receta_id = int(getattr(self.data.receta, "receta_id", 0) or 0)
        if not receta_id:
            QMessageBox.critical(self, "Error", "No se pudo determinar receta_id.")
            return

        dlg = EstadoSeguimientoPickDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            QMessageBox.warning(self, "Falta estado", "Tenés que seleccionar un estado de seguimiento para finalizar.")
            return

        estado_seg_id = dlg.selected_estado_seguimiento_id()
        if not estado_seg_id:
            QMessageBox.warning(self, "Falta estado", "Tenés que seleccionar un estado de seguimiento para finalizar.")
            return

        q = self.in_prescripcion.date()
        if not q.isValid():
            QMessageBox.warning(self, "Falta fecha", "Tenés que cargar la fecha de prescripción para finalizar.")
            return
        fecha_prescripcion: date = date(q.year(), q.month(), q.day())

        debitos_inputs = [
            DebitoInput(motivo_debito_id=mid, detalle=det)
            for mid, det in self._selected_debitos.items()
        ]

        try:
            with session_scope() as s:
                DebitosService.replace_for_receta(s, receta_id=receta_id, items=debitos_inputs)
                RecetaService.update_auditoria(
                    s,
                    receta_id=receta_id,
                    vendedor_id=int(self._vendedor_id),
                    estado_seguimiento_id=int(estado_seg_id),
                    estado_receta_id=1,
                    fecha_prescripcion=fecha_prescripcion,
                    usuario_id=self.creado_por_usuario_id
                )
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo finalizar:\n{e}")

    # -------------------------
    # Helpers
    # -------------------------
    @staticmethod
    def _set_cell(tbl: QTableWidget, row: int, col: int, text: str) -> None:
        it = QTableWidgetItem(text)
        it.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        tbl.setItem(row, col, it)

    @staticmethod
    def _fmt_money(v: Decimal) -> str:
        try:
            return f"{Decimal(v):.2f}"
        except Exception:
            return "0.00"
