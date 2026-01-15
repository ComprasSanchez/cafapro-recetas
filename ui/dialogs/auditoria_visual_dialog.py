from __future__ import annotations

from pathlib import Path
from decimal import Decimal

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QColor, QBrush, QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QSplitter,
    QLabel, QPushButton, QFrame, QScrollArea, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox, QWidget, QCheckBox
)

from app.db.session import session_scope
from app.service.auditoria_visual_service import AuditoriaVisualService, AuditoriaVisualData
from app.service.motivos_debito_service import MotivosDebitosService
from ui.label.image_view_label import ImageViewer
from ui.label.clickable_label import ClickableLabel
from ui.dialogs.vendedor_pick_dialog import VendedorPickDialog



class AuditoriaVisualDialog(QDialog):
    def __init__(self, asociacion_id: int, parent=None):
        super().__init__(parent)
        self.asociacion_id = asociacion_id
        self.data: AuditoriaVisualData | None = None
        self._last_preview_path: str | None = None
        self._current_lado = "F"
        self._vendedor_id: int | None = None

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

        self.show()

    # -------------------------
    # UI: Body split
    # -------------------------
    def _build_body(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)

        split = QSplitter(Qt.Orientation.Horizontal)
        lay.addWidget(split, 1)

        # Left
        left = QWidget()
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(0, 0, 0, 0)
        left_l.setSpacing(10)

        left_l.addWidget(self._build_image_block(), 5)  # antes 3
        left_l.addWidget(self._build_tables_block(), 2)  # igual

        split.addWidget(left)

        # Right
        right = QWidget()
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(0, 0, 0, 0)
        right_l.setSpacing(10)

        right_l.addWidget(self._build_right_header(), 0)
        right_l.addWidget(self._build_vendedor_field(), 0)
        right_l.addWidget(self._build_debitos_block(), 1)
        right_l.addWidget(self._build_resumen_block(), 0)

        split.addWidget(right)

        split.setStretchFactor(0, 6)
        split.setStretchFactor(1, 3)

        return w

    # -------------------------
    # Image block
    # -------------------------
    def _build_image_block(self) -> QFrame:
        box = QFrame()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        # Toggle buttons
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

        # Scroll + image label
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
        root.setSpacing(6)

        # Split horizontal: izquierda troqueles, derecha archivo detalle
        split = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(split, 1)

        # ----------------- IZQUIERDA: TROQUELES -----------------
        left = QWidget()
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(0, 0, 0, 0)
        left_l.setSpacing(6)

        left_l.addWidget(QLabel("Troqueles"), 0)

        self.tbl_troqueles = QTableWidget()
        self.tbl_troqueles.setColumnCount(6)
        self.tbl_troqueles.setHorizontalHeaderLabels([
            "Código barra", "Droga", "Presentación", "Alfabeta", "Monto", "Cant."
        ])
        self._setup_table(self.tbl_troqueles)
        left_l.addWidget(self.tbl_troqueles, 1)

        split.addWidget(left)

        # ----------------- DERECHA: ARCHIVO DETALLE -----------------
        right = QWidget()
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(0, 0, 0, 0)
        right_l.setSpacing(6)

        right_l.addWidget(QLabel("Archivo detalle"), 0)

        self.tbl_arch_det = QTableWidget()
        self.tbl_arch_det.setColumnCount(9)
        self.tbl_arch_det.setHorizontalHeaderLabels([
            "CodMedic", "Nombre", "Presentación", "Estado", "Nro Aut", "Cant.", "Imp Neto", "Imp OBS", "Desc"
        ])
        self._setup_table(self.tbl_arch_det)
        right_l.addWidget(self.tbl_arch_det, 1)

        split.addWidget(right)

        # Proporción inicial (ajustá a gusto)
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
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

    # -------------------------
    # Debitos block
    # -------------------------
    def _build_debitos_block(self) -> QFrame:
        box = QFrame()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        lay.addWidget(QLabel("Motivos débito"), 0)

        # Scroll de checklist
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
        lay = QHBoxLayout(box)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(12)

        # “Cuadro grande” (A412)
        self.lb_big = QLabel("—")
        self.lb_big.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lb_big.setMinimumWidth(120)
        self.lb_big.setMinimumHeight(70)
        self.lb_big.setFrameShape(QFrame.Shape.StyledPanel)
        lay.addWidget(self.lb_big, 0)

        # Datos a la derecha (labels en grilla)
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        def mk_row(r: int, title: str):
            lb_t = QLabel(title)
            lb_v = QLabel("—")
            grid.addWidget(lb_t, r, 0, alignment=Qt.AlignmentFlag.AlignRight)
            grid.addWidget(lb_v, r, 1)
            return lb_v

        self.lb_prescripcion = mk_row(0, "Prescripción")
        self.lb_emision_aut = mk_row(1, "Emisión Aut")
        self.lb_venta = mk_row(2, "Venta")
        self.lb_autorizacion = mk_row(3, "Autorización")

        lay.addLayout(grid, 1)
        return box

    # -------------------------
    # Resumen block
    # -------------------------
    def _build_resumen_block(self) -> QFrame:
        box = QFrame()
        lay = QHBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        self.card_a_cargo, self.lb_a_cargo = self._mk_resumen_card(None,"A cargo OS")
        self.card_pvp_pami, self.lb_imp_obs = self._mk_resumen_card(None,"PVP Pami")
        self.card_pvp, self.lb_imp_neto = self._mk_resumen_card(None,"PVP")

        lay.addWidget(self.card_a_cargo, 1)
        lay.addWidget(self.card_pvp_pami, 1)
        lay.addWidget(self.card_pvp, 1)

        return box

    def _build_vendedor_field(self) -> QFrame:
        box = QFrame()
        lay = QHBoxLayout(box)
        lay.setContentsMargins(8, 0, 8, 0)
        lay.setSpacing(8)

        lay.addWidget(QLabel("Vendedor:"), 0)

        self.lb_vendedor = ClickableLabel("— Seleccioná —")
        self.lb_vendedor.clicked.connect(self._pick_vendedor)

        # opcional: que parezca input (sin QSS global)
        self.lb_vendedor.setFrameShape(QFrame.Shape.StyledPanel)
        self.lb_vendedor.setMinimumHeight(28)
        self.lb_vendedor.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        lay.addWidget(self.lb_vendedor, 1)
        return box

    def _pick_vendedor(self) -> None:
        dlg = VendedorPickDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        vid = dlg.selected_vendedor_id()
        if not vid:
            return

        # buscar descripción para mostrar (simple y claro)
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

    @staticmethod
    def _mk_resumen_card(self, title: str) -> tuple[QFrame, QLabel]:
        card = QFrame()

        # borde simple sin QSS global
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setFrameShadow(QFrame.Shadow.Raised)

        v = QVBoxLayout(card)
        v.setContentsMargins(12, 10, 12, 10)
        v.setSpacing(2)

        # título chico gris
        lb_title = QLabel(title)
        f1 = QFont()
        f1.setPointSize(10)
        lb_title.setFont(f1)
        lb_title.setStyleSheet("color: #6b7280;")  # inline, no QSS global

        # valor grande azul
        lb_value = QLabel("-")
        f2 = QFont()
        f2.setPointSize(16)
        f2.setBold(True)
        lb_value.setFont(f2)
        lb_value.setStyleSheet("color: #1e88e5;")  # inline

        v.addWidget(lb_title, 0)
        v.addWidget(lb_value, 0)

        return card, lb_value

    # -------------------------
    # Load data + render
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

        # botones frente/dorso
        fr = (getattr(self.data.receta, "ubicacion_frente", None) or "").strip()
        dr = (getattr(self.data.receta, "ubicacion_dorso", None) or "").strip()

        self.btn_frente.setEnabled(bool(fr))
        self.btn_dorso.setEnabled(bool(dr))

        # mostrar primero frente si existe, si no dorso
        if fr:
            self._current_lado = "F"
            self.btn_frente.setChecked(True)
            self.btn_dorso.setChecked(False)
            self._set_preview_from_file(fr)
            self._set_preview_and_fit(fr)
        elif dr:
            self._current_lado = "D"
            self.btn_dorso.setChecked(True)
            self.btn_frente.setChecked(False)
            self._set_preview_from_file(dr)
            self._set_preview_and_fit(dr)
        else:
            self._current_lado = "F"
            self._clear_preview("Sin imagen")

        # refrescar catálogo de motivos (según lado actual)
        self._refresh_motivos_catalogo()

        # tablas
        self._render_troqueles()
        self._render_archivo_detalle()

        # resumen
        imp_neto = Decimal(str(getattr(self.data.archivo, "importe_neto", 0) or 0))
        imp_obs = Decimal(str(getattr(self.data.archivo, "importe_obs", 0) or 0))
        a_cargo = Decimal(str(getattr(self.data.archivo, "a_cargo_entidad", 0) or 0))
        self.lb_big.setText(str(getattr(self.data.receta, "nro_receta", "") or "—"))
        self.lb_prescripcion.setText(str(getattr(self.data.receta, "fecha_prescripcion", "") or "—"))
        self.lb_venta.setText(str(getattr(self.data.archivo, "fecha", "") or "—"))
        self.lb_emision_aut.setText("—")
        self.lb_autorizacion.setText("—")

        self.lb_a_cargo.setText(self._fmt_money(a_cargo))  # A cargo OS
        self.lb_imp_obs.setText(self._fmt_money(imp_obs))  # PVP Pami
        self.lb_imp_neto.setText(self._fmt_money(imp_neto))  # PVP

    def _render_troqueles(self) -> None:
        assert self.data is not None
        rows = self.data.troqueles

        self.tbl_troqueles.setRowCount(len(rows))

        for i, t in enumerate(rows):
            estado = str(getattr(t, "estado", "") or "")

            # 1) cargar celdas
            self._set_cell(self.tbl_troqueles, i, 0, str(getattr(t, "codigo_barra", "") or ""))
            self._set_cell(self.tbl_troqueles, i, 1, str(getattr(t, "droga", "") or ""))
            self._set_cell(self.tbl_troqueles, i, 2, str(getattr(t, "presentacion", "") or ""))
            self._set_cell(self.tbl_troqueles, i, 3, str(getattr(t, "code_alfabeta", "") or ""))
            self._set_cell(self.tbl_troqueles, i, 4, self._fmt_money(Decimal(str(getattr(t, "monto", 0) or 0))))
            self._set_cell(self.tbl_troqueles, i, 5, str(getattr(t, "cantidad", "") or ""))
            # Si NO querés mostrar estado como texto, podés comentar esta línea
            self._set_cell(self.tbl_troqueles, i, 6, estado)

            # 2) decidir color según estado
            color = None
            if estado == "V":
                color = QColor(0, 180, 0)  # verde
            elif estado == "A":
                color = QColor(220, 180, 0)  # amarillo
            elif estado == "R":
                color = QColor(200, 0, 0)  # rojo

            # 3) aplicar color a TODA la fila
            if color is not None:
                brush = QBrush(color)
                for c in range(self.tbl_troqueles.columnCount()):
                    it = self.tbl_troqueles.item(i, c)
                    if it:
                        it.setBackground(brush)

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
            if fr:
                self._set_preview_from_file(fr)
            else:
                self._clear_preview("Sin imagen (frente)")
        else:
            self.btn_dorso.setChecked(True)
            self.btn_frente.setChecked(False)
            if dr:
                self._set_preview_from_file(dr)
            else:
                self._clear_preview("Sin imagen (dorso)")

        self._current_lado = lado
        self._refresh_motivos_catalogo()

    def _clear_preview(self, text: str) -> None:
        self.img_preview.setPixmap(QPixmap())
        self.img_preview.setText(text)
        self._last_preview_path = None

    def _set_preview_from_file(self, path: str) -> None:
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
        self.img_preview.set_pixmap(pix)  # carga pixmap "original" en el viewer
        self._last_preview_path = str(p)

        QTimer.singleShot(0, lambda: self.img_preview.fit_to(self.scroll.viewport().size()))

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

    def _refresh_motivos_catalogo(self) -> None:
        if not self.data:
            return

        with session_scope() as s:
            motivos = MotivosDebitosService.list_motivos(s, self._current_lado)

        # 1) limpiar layout (excepto el stretch final)
        while self.motivos_layout.count() > 1:
            item = self.motivos_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        # 2) crear checkboxes
        for m in motivos:
            cb = QCheckBox(str(m.descripcion))
            cb.setProperty("motivo_id", m.motivo_debito_id)  # por si lo necesitás
            cb.setProperty("lado", str(m.lado))
            self.motivos_layout.insertWidget(self.motivos_layout.count() - 1, cb)

    def selected_motivo_ids(self) -> list[int]:
        ids: list[int] = []
        for i in range(self.motivos_layout.count() - 1):  # -1 por el stretch
            w = self.motivos_layout.itemAt(i).widget()
            if isinstance(w, QCheckBox) and w.isChecked():
                ids.append(int(w.property("motivo_id")))
        return ids

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
        self.img_preview.set_pixmap(pix)  # carga original + zoom reset (1.0)
        self._last_preview_path = str(p)

        # Fit automático al viewport (cuando ya hay tamaño real)
        QTimer.singleShot(0, lambda: self.img_preview.fit_to(self.scroll.viewport().size()))
