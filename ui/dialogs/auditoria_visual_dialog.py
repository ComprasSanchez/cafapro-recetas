from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from PySide6.QtCore import Qt, QTimer, QThreadPool
from PySide6.QtGui import QPixmap, QColor, QBrush, QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QSplitter,
    QLabel, QPushButton, QFrame, QScrollArea, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox,
    QWidget, QInputDialog, QLineEdit, QMenu, QListWidget, QListWidgetItem, QToolButton, QStyle
)

from app.db.models import EstadoTroquelEnum
from app.db.session import session_scope
from app.service.auditoria.auditoria_visual_service import AuditoriaVisualData
from app.service.debitos.debitos_service import DebitoInput
from ui.dialogs.estado_seguimeinto_pick_dialog import EstadoSeguimientoPickDialog
from ui.dialogs.historial_dialog import HistorialDialog
from ui.label.image_view_label import ImageViewer
from ui.label.clickable_label import ClickableLabel
from ui.dialogs.vendedor_pick_dialog import VendedorPickDialog
from ui.dialogs.troquel_dialog import TroquelDialog
from ui.state.auditoria_state import AuditoriaState
from ui.usecase.auditoria_visual_usecase import AuditoriaVisualUseCase
from ui.utils.worker import Worker

from ui.usecase.auditoria_usecase import AuditoriaUseCase


class AuditoriaVisualDialog(QDialog):
    # ---------------------------------------------------------
    # Dialog principal de auditoría visual.
    # Maneja:
    # - navegación entre asociaciones
    # - render de datos de auditoría
    # - carga async de datos e imágenes
    # - cache de recetas y previews
    # ---------------------------------------------------------
    def __init__(
        self,
        asociacion_ids: list[int],
        start_index: int = 0,
        parent=None,
        creado_por_usuario_id=None,
    ):
        super().__init__(parent)
        self._pool = QThreadPool.globalInstance()
        self.ROW_H = 36

        # Preview state por lado
        self._preview_req_id: dict[str, int] = {"F": 0, "D": 0}
        self._last_preview_path: dict[str, str | None] = {"F": None, "D": None}

        self.creado_por_usuario_id = creado_por_usuario_id
        self.data: AuditoriaVisualData | None = None
        self.state = AuditoriaState()

        # navegación
        self._asociacion_ids: list[int] = [int(x) for x in (asociacion_ids or []) if x]
        self._idx: int = max(0, int(start_index or 0))
        if self._idx >= len(self._asociacion_ids):
            self._idx = 0

        self.asociacion_id: int | None = None

        # cache de previews (incluye lado por seguridad)
        self._preview_cache: dict[str, bytes] = {}
        self.MAX_PREVIEW_CACHE = 200

        self.setWindowTitle("Auditoría Visual")
        self.setModal(True)
        self.setWindowFlags(
            Qt.Dialog
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
            | Qt.WindowCloseButtonHint
        )

        self._data_cache: dict[int, AuditoriaVisualData] = {}

        self._loading_overlay = QLabel("Cargando…", self)
        self._loading_overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._loading_overlay.setStyleSheet("""
            QLabel {
                background: rgba(0, 0, 0, 120);
                color: white;
                font-size: 18px;
                font-weight: bold;
            }
        """)
        self._loading_overlay.hide()

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        root.addWidget(self._build_body(), 1)
        self.showMaximized()

        if not self._asociacion_ids:
            QMessageBox.warning(self, "Sin registros", "No hay asociaciones para auditar.")
            self.reject()
            return

        self._goto(self._idx)

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

        # ⬇️ ahora el bloque de débitos son 2 segmentos (F y D)
        right_l.addWidget(self._build_debitos_block(), 1)

        right_l.addWidget(self._build_resumen_block(), 0)
        right_l.addWidget(self._build_actions_block(), 0)

        split.addWidget(right)

        split.setStretchFactor(0, 8)
        split.setStretchFactor(1, 3)

        return w

    # -------------------------
    # Image block (Frente + Dorso juntos)
    # -------------------------
    def _build_image_block(self) -> QFrame:
        box = QFrame()
        box.setObjectName("card")
        lay = QVBoxLayout(box)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        # ✅ ahora horizontal (Frente | Dorso)
        split = QSplitter(Qt.Orientation.Horizontal)
        lay.addWidget(split, 1)

        # -------- Frente --------
        fr = QFrame()
        fr.setObjectName("card")
        fr_l = QVBoxLayout(fr)
        fr_l.setContentsMargins(10, 10, 10, 10)
        fr_l.setSpacing(6)

        lb_fr = QLabel("Frente")
        lb_fr.setProperty("role", "subtitle")
        fr_l.addWidget(lb_fr, 0)

        self.scroll_frente = QScrollArea()
        self.scroll_frente.setWidgetResizable(True)
        self.scroll_frente.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_frente.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.img_frente = ImageViewer()
        self.img_frente.setText("Sin imagen (frente)")
        self.scroll_frente.setWidget(self.img_frente)

        fr_l.addWidget(self.scroll_frente, 1)
        split.addWidget(fr)

        # -------- Dorso --------
        dr = QFrame()
        dr.setObjectName("card")
        dr_l = QVBoxLayout(dr)
        dr_l.setContentsMargins(10, 10, 10, 10)
        dr_l.setSpacing(6)

        lb_dr = QLabel("Dorso")
        lb_dr.setProperty("role", "subtitle")
        dr_l.addWidget(lb_dr, 0)

        self.scroll_dorso = QScrollArea()
        self.scroll_dorso.setWidgetResizable(True)
        self.scroll_dorso.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_dorso.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.img_dorso = ImageViewer()
        self.img_dorso.setText("Sin imagen (dorso)")
        self.scroll_dorso.setWidget(self.img_dorso)

        dr_l.addWidget(self.scroll_dorso, 1)
        split.addWidget(dr)

        # 50/50 (podés ajustar)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 1)

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
        self.tbl_troqueles.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tbl_troqueles.customContextMenuRequested.connect(self._on_troqueles_context_menu)
        self.tbl_troqueles.setColumnCount(7)
        self.tbl_troqueles.setHorizontalHeaderLabels([
            "Código barra",      # 0
            "Presentación",      # 1
            "Cant.",             # 2
            "Droga",             # 3
            "Alfabeta",          # 4
            "Monto",             # 5
            "Estado",            # 6
        ])
        self.tbl_troqueles.setColumnHidden(6, True)
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

        max_height = (self.ROW_H * 2) + 100
        w.setMaximumHeight(max_height)
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
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hh.setHighlightSections(False)

    # -------------------------
    # Debitos block (dos segmentos: Frente + Dorso)
    # -------------------------
    def _build_debitos_block(self) -> QWidget:
        w = QWidget()
        root = QVBoxLayout(w)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        # ---------- Frente ----------
        box_f = QFrame()
        box_f.setObjectName("card")
        lay_f = QVBoxLayout(box_f)
        lay_f.setContentsMargins(12, 12, 12, 12)
        lay_f.setSpacing(8)

        title_f = QLabel("Motivos débito – Frente")
        lay_f.addWidget(title_f)

        self.list_motivos_f = QListWidget()
        lay_f.addWidget(self.list_motivos_f, 1)

        # ---------- Dorso ----------
        box_d = QFrame()
        box_d.setObjectName("card")
        lay_d = QVBoxLayout(box_d)
        lay_d.setContentsMargins(12, 12, 12, 12)
        lay_d.setSpacing(8)

        title_d = QLabel("Motivos débito – Dorso")
        lay_d.addWidget(title_d)

        self.list_motivos_d = QListWidget()
        lay_d.addWidget(self.list_motivos_d, 1)

        self.list_motivos_f.itemChanged.connect(self._on_motivo_item_changed)
        self.list_motivos_d.itemChanged.connect(self._on_motivo_item_changed)

        root.addWidget(box_f, 1)
        root.addWidget(box_d, 1)
        return w

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

        def mk_row_line_date(r: int, title: str) -> QLineEdit:
            lb_title = QLabel(title)

            le = QLineEdit()
            le.setPlaceholderText("dd/MM/yyyy")
            le.setInputMask("00/00/0000")
            le.setMinimumHeight(28)

            grid.addWidget(lb_title, r, 0, alignment=Qt.AlignmentFlag.AlignRight)
            grid.addWidget(le, r, 1)
            return le

        self.in_prescripcion = mk_row_line_date(0, "Prescripción")
        self.in_emision = mk_row_line_date(1, "Emisión")
        self.in_venta = mk_row_line_date(2, "Venta")

        lb_t = QLabel("Autorización")
        self.lb_autorizacion = QLabel("—")
        grid.addWidget(lb_t, 3, 0, alignment=Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self.lb_autorizacion, 3, 1)

        # indicador de progreso
        self.lb_pos = QLabel("—")
        self.lb_pos.setObjectName("muted")
        grid.addWidget(self.lb_pos, 4, 1, alignment=Qt.AlignmentFlag.AlignLeft)

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

    @staticmethod
    def _mk_resumen_card(title: str) -> tuple[QFrame, QLabel]:
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

        self.btn_salir = QPushButton("Salir")
        self.btn_salir.setMinimumHeight(34)
        self.btn_salir.clicked.connect(self.reject)
        lay.addWidget(self.btn_salir, 0)

        # Botón anterior (icono flecha izquierda)
        self.btn_prev = QToolButton()
        self.btn_prev.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowBack))
        self.btn_prev.setToolTip("Anterior")
        self.btn_prev.setAutoRaise(True)  # estilo plano
        self.btn_prev.setIconSize(self.btn_prev.iconSize())
        self.btn_prev.clicked.connect(self._on_prev)
        lay.addWidget(self.btn_prev)

        # Botón siguiente (icono flecha derecha)
        self.btn_next = QToolButton()
        self.btn_next.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowForward))
        self.btn_next.setToolTip("Siguiente")
        self.btn_next.setAutoRaise(True)
        self.btn_next.clicked.connect(self._on_next_only)
        lay.addWidget(self.btn_next)

        lay.addStretch(1)

        self.btn_finalizar = QPushButton("Finalizar y siguiente")
        self.btn_finalizar.setProperty("variant", "primary")
        self.btn_finalizar.setMinimumHeight(34)
        self.btn_finalizar.clicked.connect(self._on_finalizar)

        self.btn_debitada = QPushButton("DEBITADA")
        self.btn_debitada.setMinimumHeight(34)
        self.btn_debitada.setVisible(False)  # por defecto oculto
        self.btn_debitada.clicked.connect(self._open_historial_debitada)

        # azul flúor + blanco (ajustalo vos)
        self.btn_debitada.setStyleSheet("""
                   QPushButton {
                       background: #00B8FF;
                       color: white;
                       font-weight: 800;
                       border-radius: 8px;
                       padding: 6px 14px;
                   }
                   QPushButton:hover { background: #2AC6FF; }
                   QPushButton:pressed { background: #0099D6; }
               """)

        lay.addWidget(self.btn_debitada, 0)

        lay.addWidget(self.btn_finalizar, 0)
        return box

    # ---------------------------------------------------------
    # Navega a una posición de la lista de asociaciones.
    # - limpia estado visual
    # - usa cache si el registro ya fue cargado
    # - si no, dispara carga async
    # - inicia preload de registros siguientes
    # ---------------------------------------------------------
    def _goto(self, idx: int) -> None:
        if not self._asociacion_ids:
            return

        idx = max(0, min(idx, len(self._asociacion_ids) - 1))
        self._idx = idx

        asociacion_id = int(self._asociacion_ids[self._idx])
        self.asociacion_id = asociacion_id

        # 🔥 reset visual
        self._reset_ui_state()

        # 🔥 cache hit
        if asociacion_id in self._data_cache:
            data = self._data_cache[asociacion_id]

            self._apply_data_to_state(data)
            self._render_all()

            self._preload_images_for_data(data)

            self._preload_batch()
            return

        # 🔥 async load
        self._show_loading()

        w = Worker(self._load_data_background_sync, asociacion_id=asociacion_id)
        w.signals.finished.connect(self._on_data_loaded)
        self._pool.start(w)

    # ---------------------------------------------------------
    # Carga preview de imagen para frente/dorso.
    # - usa cache si existe
    # - si no, carga async
    # - ajusta zoom al viewport
    # ---------------------------------------------------------
    def _render_all(self) -> None:
        if not self.data:
            return

        QTimer.singleShot(0, self._focus_venta)

        self._render_images()
        self._render_motivos()
        self._render_troqueles()
        self._render_archivo_detalle()
        self._render_header()
        self._render_resumen()
        self._render_navigation()

    def _render_troqueles(self) -> None:
        assert self.data is not None
        rows = self.data.troqueles

        self.tbl_troqueles.setUpdatesEnabled(False)
        self.tbl_troqueles.setRowCount(len(rows))
        for i, t in enumerate(rows):
            estado = getattr(t, "estado", "")

            self._set_cell(self.tbl_troqueles, i, 0, str(getattr(t, "codigo_barra", "") or ""))
            self._set_cell(self.tbl_troqueles, i, 1, str(getattr(t, "presentacion", "") or ""))
            self._set_cell(self.tbl_troqueles, i, 2, str(getattr(t, "cantidad", "") or ""))

            self._set_cell(self.tbl_troqueles, i, 3, str(getattr(t, "droga", "") or ""))
            self._set_cell(self.tbl_troqueles, i, 4, str(getattr(t, "code_alfabeta", "") or ""))
            self._set_cell(self.tbl_troqueles, i, 5, self._fmt_money(Decimal(str(getattr(t, "monto", 0) or 0))))
            self._set_cell(self.tbl_troqueles, i, 6, str(estado))

            troq_id = int(getattr(t, "troquel_id", 0) or 0)
            it0 = self.tbl_troqueles.item(i, 0)
            if it0 and troq_id:
                it0.setData(Qt.ItemDataRole.UserRole, troq_id)

            color = None
            if estado == EstadoTroquelEnum.V:
                color = QColor(17, 151, 59)
            elif estado == EstadoTroquelEnum.A:
                color = QColor(228, 245, 44)
            elif estado == EstadoTroquelEnum.R:
                color = QColor(165, 32, 25)
            if color is not None:
                brush = QBrush(color)
                for c in range(self.tbl_troqueles.columnCount()):
                    it = self.tbl_troqueles.item(i, c)
                    if it:
                        it.setData(Qt.BackgroundRole, brush)

        self.tbl_troqueles.setUpdatesEnabled(True)

    def _render_archivo_detalle(self) -> None:
        assert self.data is not None
        rows = self.data.archivo_detalles

        self.tbl_arch_det.setUpdatesEnabled(False)
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
        self.tbl_arch_det.setUpdatesEnabled(True)

    # -------------------------
    # Preview controls (doble)
    # -------------------------
    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._loading_overlay.setGeometry(self.rect())


    def _clear_preview(self, lado: str, text: str) -> None:
        if lado == "F":
            self.img_frente.set_pixmap(None)
            self.img_frente.setText(text)
        else:
            self.img_dorso.set_pixmap(None)
            self.img_dorso.setText(text)
        self._last_preview_path[lado] = None

    # ---------------------------------------------------------
    # Carga preview de imagen para frente/dorso.
    # - usa cache si existe
    # - si no, carga async
    # - ajusta zoom al viewport
    # ---------------------------------------------------------
    def _set_preview_and_fit(self, lado: str, key_or_path: str) -> None:
        raw = (key_or_path or "").strip()
        if not raw:
            self._clear_preview(lado, f"Sin imagen ({'frente' if lado == 'F' else 'dorso'})")
            return

        self._last_preview_path[lado] = raw

        scroll, viewer = self._widgets_por_lado(lado)

        vw = max(200, scroll.viewport().width() - 12)
        vh = max(200, scroll.viewport().height() - 12)

        if raw in self._preview_cache:

            png_bytes = self._preview_cache[raw]

            pix = QPixmap()
            ok = pix.loadFromData(png_bytes)

            if ok and not pix.isNull():
                viewer.setText("")
                viewer.set_pixmap(pix)
                QTimer.singleShot(0, lambda: viewer.fit_to(scroll.viewport().size()))
                return

        self._preview_req_id[lado] += 1
        req_id = self._preview_req_id[lado]

        viewer.setText("Cargando…")
        viewer.set_pixmap(None)

        w = Worker(self._load_preview_via_usecase, lado=lado, raw=raw, vw=vw, vh=vh, req_id=req_id)
        w.signals.finished.connect(self._apply_preview_bytes)
        w.signals.error.connect(lambda e, _lado=lado: self._ui_error_preview(_lado, e))
        self._pool.start(w)

    # ---------------------------------------------------------
    # Worker thread:
    # obtiene preview reducido de imagen vía UseCase.
    # ---------------------------------------------------------
    def _load_preview_via_usecase(self, *, lado: str, raw: str, vw: int, vh: int, req_id: int) -> dict:
        if raw in self._preview_cache:
            return {
                "lado": lado,
                "png_bytes": self._preview_cache[raw],
                "req_id": req_id,
                "raw": raw
            }

        out = AuditoriaUseCase.load_preview_bytes(path=raw, vw=vw, vh=vh)

        if out.img_bytes:
            self._cache_preview(raw, out.img_bytes)

        return {
            "lado": lado,
            "png_bytes": out.img_bytes,
            "req_id": req_id,
            "raw": raw
        }

    # ---------------------------------------------------------
    # Aplica preview cargado al viewer correspondiente.
    # Valida request_id para evitar race conditions.
    # ---------------------------------------------------------
    def _apply_preview_bytes(self, out: dict) -> None:
        lado = (out.get("lado") or "F").strip()
        req_id = int(out.get("req_id") or 0)
        raw = (out.get("raw") or "").strip()

        if req_id != self._preview_req_id.get(lado, 0):
            return
        if self._last_preview_path.get(lado) and self._last_preview_path[lado] != raw:
            return

        png_bytes = out.get("png_bytes") or b""
        if not png_bytes:
            self._clear_preview(lado, "No se pudo cargar la imagen.")
            return

        scroll, viewer = self._widgets_por_lado(lado)

        self._cache_preview(raw, png_bytes)

        pix = QPixmap()
        ok = pix.loadFromData(png_bytes)
        if not ok or pix.isNull():
            self._clear_preview(lado, "No se pudo leer la imagen.")
            return

        viewer.setText("")
        viewer.set_pixmap(pix)
        QTimer.singleShot(0, lambda: viewer.fit_to(scroll.viewport().size()))

    def _ui_error_preview(self, lado: str, err_text: str) -> None:
        lines = [l.strip() for l in (err_text or "").splitlines() if l.strip()]
        nice = lines[-1] if lines else "Error cargando imagen."

        viewer = self.img_frente if lado == "F" else self.img_dorso
        viewer.set_pixmap(None)
        viewer.setText(f"No se pudo cargar la imagen.\n{nice}")

    def _render_motivos_lado(self, lado: str) -> None:
        if not self.data:
            return

        if lado == "F":
            motivos = self.data.motivos_frente
            list_widget = self.list_motivos_f
        else:
            motivos = self.data.motivos_dorso
            list_widget = self.list_motivos_d

        list_widget.blockSignals(True)
        list_widget.clear()

        for m in motivos:
            motivo_id = int(m.motivo_debito_id)
            descripcion = m.descripcion
            activo = bool(getattr(m, "activo", True))
            seleccionado = motivo_id in self.state.debitos

            # 🔴 Si está inactivo y no estaba seleccionado → no se muestra
            if not activo and not seleccionado:
                continue

            text = descripcion

            if seleccionado:
                detalle = self.state.debitos.get(motivo_id)
                if detalle:
                    text = f"{descripcion}  ({detalle})"

            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, motivo_id)

            # Habilitamos checkbox
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)

            if seleccionado:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)

            # 🔥 Si está inactivo → deshabilitar interacción y pintar gris
            if not activo:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                item.setForeground(QBrush(QColor(150, 150, 150)))

            list_widget.addItem(item)

        list_widget.blockSignals(False)


    def _on_motivo_item_changed(self, item: QListWidgetItem):
        motivo_id = item.data(Qt.ItemDataRole.UserRole)
        if not motivo_id:
            return

        motivo_id = int(motivo_id)

        if item.checkState() != Qt.CheckState.Checked:
            self.state.debitos.pop(motivo_id, None)
            return

        prev = self.state.debitos.get(motivo_id) or ""
        detalle, ok = QInputDialog.getText(
            self,
            "Detalle del débito",
            "Detalle (opcional):",
            text=prev,
        )

        if not ok:
            item.setCheckState(Qt.CheckState.Unchecked)
            self.state.debitos.pop(motivo_id, None)
            return

        self.state.debitos[motivo_id] = (detalle.strip() or None)

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

        self.state.vendedor_id = int(v.vendedor_id)
        self.lb_vendedor.setText(str(getattr(v, "descripcion", "") or "—"))
        self.lb_vendedor.setToolTip(f"Código: {getattr(v, 'codigo', '')}")

    # ---------------------------------------------------------
    # Valida datos ingresados y guarda la auditoría.
    # Si es exitosa, navega automáticamente a la siguiente.
    # ---------------------------------------------------------
    def _on_finalizar(self) -> None:
        if not self.data:
            return

        receta_id = int(getattr(self.data.receta, "receta_id", 0) or 0)
        if not receta_id:
            QMessageBox.critical(self, "Error", "No se pudo determinar receta_id.")
            return

        # -------- PARSE FECHAS --------
        fecha_prescripcion = self._parse_ddmmyyyy(self.in_prescripcion.text())
        fecha_emision = self._parse_ddmmyyyy(self.in_emision.text())
        fecha_venta = self._parse_ddmmyyyy(self.in_venta.text())

        # Venta obligatoria
        if not fecha_venta:
            QMessageBox.warning(
                self,
                "Falta fecha",
                "Tenés que cargar la fecha de Venta (dd/MM/yyyy)."
            )
            return

        # -------- VALIDACIÓN 1: AUTORIZACIÓN vs VENTA --------
        fecha_autorizacion = getattr(self.data.archivo, "fecha", None)

        if fecha_autorizacion and fecha_venta:
            if fecha_autorizacion != fecha_venta:
                QMessageBox.warning(
                    self,
                    "Fechas no coinciden",
                    "La fecha de Autorización y la fecha de Venta deben coincidir."
                )
                return

        # -------- VALIDACIÓN 2: SI HAY DÉBITOS → VENDEDOR OBLIGATORIO --------
        if self.state.debitos and not self.state.vendedor_id:
            QMessageBox.warning(
                self,
                "Falta vendedor",
                "Si seleccionás algún débito, tenés que cargar un vendedor."
            )
            return

        # -------- CONSTRUCCIÓN DÉBITOS --------
        debitos_inputs = [
            DebitoInput(motivo_debito_id=mid, detalle=det)
            for mid, det in self.state.debitos.items()
        ]

        estado_seg_id: int | None = None

        if debitos_inputs:
            dlg = EstadoSeguimientoPickDialog(self)
            if dlg.exec() != dlg.DialogCode.Accepted:
                QMessageBox.warning(
                    self,
                    "Falta estado",
                    "Tenés que seleccionar un estado de seguimiento para finalizar."
                )
                return

            estado_seg_id = dlg.selected_estado_seguimiento_id()
            if not estado_seg_id:
                QMessageBox.warning(
                    self,
                    "Falta estado",
                    "Tenés que seleccionar un estado de seguimiento para finalizar."
                )
                return

            estado_seg_id = int(estado_seg_id)

        try:
            worker = Worker(
                self._save_auditoria_background,
                receta_id=receta_id,
                vendedor_id=self.state.vendedor_id,
                estado_seg_id=estado_seg_id,
                fecha_prescripcion=fecha_prescripcion,
                fecha_emision=fecha_emision,
                fecha_venta=fecha_venta,
                debitos_inputs=debitos_inputs,
            )

            worker.signals.error.connect(self._on_save_error)

            self._pool.start(worker)

            # invalidar cache
            if self.asociacion_id:
                asoc_id = int(self.asociacion_id)
                self._data_cache.pop(asoc_id, None)

            # PASAR A LA SIGUIENTE INMEDIATAMENTE
            self._on_next_only()

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

    @staticmethod
    def _parse_ddmmyyyy(s: str) -> date | None:
        s = (s or "").strip()
        if not s or "_" in s:
            return None
        try:
            return datetime.strptime(s, "%d/%m/%Y").date()
        except ValueError:
            return None

    def _on_troqueles_context_menu(self, pos) -> None:
        if not self.data or not self.asociacion_id:
            return

        tbl = self.tbl_troqueles
        row = tbl.rowAt(pos.y())

        if row >= 0:
            tbl.selectRow(row)

        menu = QMenu(self)

        act_add = menu.addAction("Agregar troquel…")
        act_edit = menu.addAction("Editar cantidad…")
        act_edit.setEnabled(row >= 0)

        chosen = menu.exec(tbl.viewport().mapToGlobal(pos))
        if not chosen:
            return

        if chosen == act_add:
            self._ctx_add_troquel()
        elif chosen == act_edit:
            self._ctx_edit_troquel_qty()

    def _ctx_add_troquel(self) -> None:
        if not self.asociacion_id:
            return

        dlg = TroquelDialog(
            mode="create",
            asociacion_id=int(self.asociacion_id),
            parent=self,
        )

        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        # 🔥 invalidar cache y recargar async
        asoc_id = int(self.asociacion_id)
        self._data_cache.pop(asoc_id, None)
        self._goto(self._idx)

    def _ctx_edit_troquel_qty(self) -> None:
        row = self.tbl_troqueles.currentRow()
        if row < 0:
            QMessageBox.information(self, "Sin selección", "Seleccioná un troquel para editar.")
            return

        it0 = self.tbl_troqueles.item(row, 0)
        if not it0:
            return

        troquel_id = int(it0.data(Qt.ItemDataRole.UserRole) or 0)
        if not troquel_id:
            QMessageBox.warning(self, "Error", "No se pudo determinar troquel_id.")
            return

        codigo = (
            self.tbl_troqueles.item(row, 0).text()
            if self.tbl_troqueles.item(row, 0)
            else ""
        ).strip()

        qty_txt = (
            self.tbl_troqueles.item(row, 2).text()
            if self.tbl_troqueles.item(row, 2)
            else "1"
        ).strip()

        try:
            qty = int(qty_txt)
        except Exception:
            qty = 1

        dlg = TroquelDialog(
            mode="update",
            troquel_id=troquel_id,
            codigo_barra=codigo,
            cantidad=qty,
            parent=self,
        )

        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        # 🔥 invalidar cache y recargar async
        if self.asociacion_id:
            asoc_id = int(self.asociacion_id)
            self._data_cache.pop(asoc_id, None)
            self._goto(self._idx)

    def _open_historial_debitada(self) -> None:
        if not self.data:
            return

        archivo_id = int(getattr(self.data.archivo, "archivo_id", 0) or 0)
        if not archivo_id:
            QMessageBox.warning(self, "Error", "No se pudo determinar archivo_id.")
            return

        dlg = HistorialDialog(archivo_id_actual=archivo_id, parent=self)
        dlg.exec()

    @staticmethod
    def _fmt_date(d):
        if not d:
            return ""
        try:
            return d.strftime("%d/%m/%Y")
        except Exception:
            return ""

    def _on_next_only(self):
        if self._idx + 1 < len(self._asociacion_ids):
            self._goto(self._idx + 1)

    def _on_prev(self):
        if self._idx - 1 >= 0:
            self._goto(self._idx - 1)

    def _show_loading(self):
        self._loading_overlay.setGeometry(self.rect())
        self._loading_overlay.show()

    def _hide_loading(self):
        self._loading_overlay.hide()

    # ---------------------------------------------------------
    # Worker thread:
    # carga datos completos de auditoría para una asociación.
    # ---------------------------------------------------------
    @staticmethod
    def _load_data_background_sync(*, asociacion_id: int):
        data = AuditoriaVisualUseCase.load_auditoria(asociacion_id)
        return {"id": asociacion_id, "data": data}

    def _on_data_loaded(self, result: dict):
        asociacion_id = result["id"]
        data = result["data"]

        self._data_cache[asociacion_id] = data

        self._apply_data_to_state(data)

        self._render_all()
        self._hide_loading()

        self._preload_images_for_data(data)

        # 🔥 precargar próximas recetas
        self._preload_batch()

    # ---------------------------------------------------------
    # Precarga en background las próximas asociaciones
    # para navegación más fluida.
    # ---------------------------------------------------------
    def _preload_batch(self, batch_size: int = 3):
        for i in range(1, batch_size + 1):
            idx = self._idx + i
            if idx >= len(self._asociacion_ids):
                break

            next_id = int(self._asociacion_ids[idx])
            if next_id in self._data_cache:
                continue

            w = Worker(self._load_data_background_sync, asociacion_id=next_id)
            w.signals.finished.connect(self._on_preload_finished)
            self._pool.start(w)

    # ---------------------------------------------------------
    # Limpia completamente el estado visual antes de
    # mostrar una nueva asociación.
    # ---------------------------------------------------------
    def _reset_ui_state(self):
        self.data = None
        self.state.debitos = {}
        self.state.vendedor_id = None

        self.lb_vendedor.setText("— Seleccioná —")
        self.lb_vendedor.setToolTip("")

        self.in_prescripcion.clear()
        self.in_emision.clear()
        self.in_venta.clear()

        self.lb_autorizacion.setText("—")
        self.lb_big.setText("—")

        self.tbl_troqueles.setRowCount(0)
        self.tbl_arch_det.setRowCount(0)

        self.list_motivos_f.clear()
        self.list_motivos_d.clear()

        for lado, txt in {
            "F": "Sin imagen (frente)",
            "D": "Sin imagen (dorso)"
        }.items():
            self._clear_preview(lado, txt)

    def _apply_data_to_state(self, data):
        self.data = data

        # reconstruir débitos
        self.state.debitos = {
            int(d.motivo_debito_id): d.detalle
            for d in (data.debitos or [])
            if getattr(d, "motivo_debito_id", None)
        }

        vendedor = getattr(data, "vendedor", None)
        if vendedor:
            self.state.vendedor_id = vendedor.vendedor_id
            self.lb_vendedor.setText(vendedor.descripcion or "—")
            self.lb_vendedor.setToolTip(f"Código: {vendedor.codigo or ''}")

    def _focus_venta(self):
        self.in_venta.setFocus(Qt.FocusReason.TabFocusReason)
        self.in_venta.selectAll()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            event.ignore()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        self._pool.clear()
        self._pool.waitForDone()
        super().closeEvent(event)

    def _widgets_por_lado(self, lado: str):
        if lado == "F":
            return self.scroll_frente, self.img_frente
        else:
            return self.scroll_dorso, self.img_dorso

    # ---------------------------------------------------------
    # Guarda preview en cache con límite MAX_PREVIEW_CACHE.
    # Elimina el más antiguo cuando se llena.
    # ---------------------------------------------------------
    def _cache_preview(self, raw: str, img_bytes: bytes):

        if not img_bytes:
            return

        # si ya existe, no hacer nada
        if raw in self._preview_cache:
            return

        # controlar tamaño del cache
        if len(self._preview_cache) >= self.MAX_PREVIEW_CACHE:
            # eliminar el más antiguo
            self._preview_cache.pop(next(iter(self._preview_cache)))

        self._preview_cache[raw] = img_bytes

    def _on_save_error(self, err):
        QMessageBox.critical(
            self,
            "Error guardando auditoría",
            str(err)
        )

    def _save_auditoria_background(
            self,
            *,
            receta_id,
            vendedor_id,
            estado_seg_id,
            fecha_prescripcion,
            fecha_emision,
            fecha_venta,
            debitos_inputs,
    ):
        AuditoriaVisualUseCase.finalizar_auditoria(
            receta_id=receta_id,
            vendedor_id=vendedor_id,
            estado_seguimiento_id=estado_seg_id,
            fecha_prescripcion=fecha_prescripcion,
            fecha_emision=fecha_emision,
            fecha_venta=fecha_venta,
            usuario_id=self.creado_por_usuario_id,
            debitos_inputs=debitos_inputs,
        )

    def _render_images(self):

        if not self.data:
            return

        fr = (getattr(self.data.receta, "ubicacion_frente", None) or "").strip()
        dr = (getattr(self.data.receta, "ubicacion_dorso", None) or "").strip()

        for lado, path in {
            "F": fr,
            "D": dr
        }.items():

            if path:
                self._set_preview_and_fit(lado, path)
            else:
                self._clear_preview(
                    lado,
                    f"Sin imagen ({'frente' if lado == 'F' else 'dorso'})"
                )

    def _render_motivos(self):
        self._render_motivos_lado("F")
        self._render_motivos_lado("D")

    def _render_header(self):

        self.in_prescripcion.setText(
            self._fmt_date(getattr(self.data.receta, "fecha_prescripcion", None))
        )

        self.in_emision.setText(
            self._fmt_date(getattr(self.data.receta, "fecha_emision", None))
        )

        self.in_venta.setText(
            self._fmt_date(getattr(self.data.receta, "fecha_venta", None))
        )

        self.lb_big.setText(
            str(getattr(self.data.archivo, "orden_lote", "") or "—")
        )

        self.lb_autorizacion.setText(
            str(getattr(self.data.archivo, "fecha", "") or "—")
        )

        self.btn_debitada.setVisible(self.data.has_historial_debitada)

    def _render_resumen(self):

        self.lb_a_cargo.setText(
            self._fmt_money(
                Decimal(str(getattr(self.data.archivo, "a_cargo_entidad", 0) or 0))
            )
        )

        self.lb_imp_obs.setText(
            self._fmt_money(
                Decimal(str(getattr(self.data.archivo, "importe_obs", 0) or 0))
            )
        )

        self.lb_imp_neto.setText(
            self._fmt_money(
                Decimal(str(getattr(self.data.archivo, "importe_neto", 0) or 0))
            )
        )

    def _render_navigation(self):

        self.lb_pos.setText(
            f"{self._idx + 1} / {len(self._asociacion_ids)}"
        )

    # ---------------------------------------------------------
    # Precarga previews de frente/dorso en background
    # y los guarda en cache de imágenes.
    # ---------------------------------------------------------
    def _preload_images_for_data(self, data: AuditoriaVisualData):

        if not data:
            return

        fr = (getattr(data.receta, "ubicacion_frente", None) or "").strip()
        dr = (getattr(data.receta, "ubicacion_dorso", None) or "").strip()

        for raw in (fr, dr):

            if not raw:
                continue

            if raw in self._preview_cache:
                continue

            worker = Worker(
                self._preload_image_background,
                raw=raw
            )

            worker.signals.finished.connect(self._on_preload_image_finished)

            self._pool.start(worker)

    @staticmethod
    def _preload_image_background(*, raw: str):

        out = AuditoriaUseCase.load_preview_bytes(
            path=raw,
            vw=800,
            vh=800
        )

        if out.img_bytes:
            return {
                "raw": raw,
                "bytes": out.img_bytes
            }

        return None

    def _on_preload_image_finished(self, result):

        if not result:
            return

        raw = result["raw"]
        img_bytes = result["bytes"]

        self._cache_preview(raw, img_bytes)

    def _on_preload_finished(self, result: dict):

        asociacion_id = result["id"]
        data = result["data"]

        self._data_cache[asociacion_id] = data

        self._preload_images_for_data(data)