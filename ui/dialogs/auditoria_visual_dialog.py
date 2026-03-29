from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, QThreadPool
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QSplitter,
    QLabel, QPushButton, QFrame, QScrollArea, QTableWidget,
    QHeaderView, QAbstractItemView, QMessageBox,
    QWidget, QInputDialog, QLineEdit, QMenu, QListWidget, QListWidgetItem, QToolButton, QStyle
)

from ui.dialogs.estado_seguimiento_pick_dialog import EstadoSeguimientoPickDialog
from ui.dialogs.historial_dialog import HistorialDialog
from ui.dialogs.auditoria_visual_cache_helpers import put_preview_cache_item
from ui.dialogs.auditoria_visual_finalize_helpers import build_finalizar_payload
from ui.dialogs.auditoria_visual_motivos_helpers import render_motivos_list, set_motivo_item_text
from ui.dialogs.auditoria_visual_preview_helpers import (
    empty_preview_text,
    extract_preview_error,
    is_stale_preview_response,
    pixmap_from_png_bytes,
    viewport_preview_size,
)
from ui.label.image_view_label import ImageViewer
from ui.label.clickable_label import ClickableLabel
from ui.dialogs.auditoria_visual_prefetch_helpers import build_prefetch_queue, pop_next_prefetch
from ui.dialogs.vendedor_pick_dialog import VendedorPickDialog
from ui.dialogs.troquel_dialog import TroquelDialog
from ui.dialogs.auditoria_visual_helpers import fmt_date, fmt_money, parse_ddmmyyyy
from ui.dialogs.auditoria_visual_render_helpers import (
    render_archivo_detalle_table,
    render_header_fields,
    render_navigation_label,
    render_resumen_fields,
    render_troqueles_table,
)
from ui.state.auditoria_state import AuditoriaState
from ui.usecase.auditoria_visual_usecase import AuditoriaVisualUseCase
from ui.utils.worker import Worker

from ui.usecase.auditoria_usecase import AuditoriaUseCase


class AuditoriaVisualDialog(QDialog):
    ESTADO_TROQUEL_VERDE = "V"
    ESTADO_TROQUEL_AMARILLO = "A"
    ESTADO_TROQUEL_ROJO = "R"

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
        self.data = None
        self.state = AuditoriaState()

        # navegación
        self._asociacion_ids: list[int] = [int(x) for x in (asociacion_ids or []) if x]
        self._idx: int = max(0, int(start_index or 0))
        if self._idx >= len(self._asociacion_ids):
            self._idx = 0

        self.asociacion_id: int | None = None

        self.PREFETCH_SIZE = 6
        self._prefetch_running = False
        self._loading_ids = set()
        self._prefetch_queue: list[int] = []

        # cache de previews (incluye lado por seguridad)
        self._preview_cache: dict[str, bytes] = {}
        self.MAX_PREVIEW_CACHE = 200
        self._updating_motivos = False
        self._motivo_dialog_open = False

        self.setWindowTitle("Auditoría Visual")
        self.setModal(True)
        self.setWindowFlags(
            Qt.Dialog
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
            | Qt.WindowCloseButtonHint
        )

        self._data_cache: dict[int, object] = {}

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

        lb_a = QLabel("Detalle de archivo")
        lb_a.setProperty("role", "subtitle")
        right_l.addWidget(lb_a, 0)

        self.tbl_arch_det = QTableWidget()
        self.tbl_arch_det.setColumnCount(9)
        self.tbl_arch_det.setHorizontalHeaderLabels([
            "Código de barra", "Código Medic.", "Nombre", "Presentación", "Estado", "N° Aut.", "Cant.", "Imp. neto", "Imp. O.S.", "Desc."
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
        box = QFrame()
        box.setObjectName("card")

        lay = QVBoxLayout(box)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(6)

        title = QLabel("Motivos de débito")
        title.setProperty("role", "subtitle")
        lay.addWidget(title)

        self.list_motivos = QListWidget()
        self.list_motivos.itemChanged.connect(self._on_motivo_item_changed)
        self.list_motivos.itemDoubleClicked.connect(self._on_motivo_item_activated)
        self.list_motivos.setSpacing(1)
        self.list_motivos.setUniformItemSizes(True)
        self.list_motivos.setStyleSheet("""
        QListWidget::item {
            padding: 2px 4px;
            margin: 0px;
        }
        """)

        lay.addWidget(self.list_motivos)

        return box

    def _build_right_header(self) -> QFrame:
        box = QFrame()
        box.setObjectName("card")
        lay = QHBoxLayout(box)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(12)

        self.lb_big = QLabel("—")
        self.lb_big.setObjectName("ordenLoteBig")
        self.lb_big.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lb_big.setMinimumWidth(120)
        self.lb_big.setMinimumHeight(70)
        self.lb_big.setFrameShape(QFrame.Shape.StyledPanel)
        self.lb_big.setStyleSheet(
            "QLabel#ordenLoteBig { font-size: 42px; font-weight: 900; padding: 0px; }"
        )

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

        self.card_a_cargo, self.lb_a_cargo = self._mk_resumen_card("A cargo O.S.")
        self.card_pvp_pami, self.lb_imp_obs = self._mk_resumen_card("A cargo afiliado")
        self.card_pvp, self.lb_imp_neto = self._mk_resumen_card("Total")

        lay.addWidget(self.card_pvp, 1)
        lay.addWidget(self.card_a_cargo, 1)
        lay.addWidget(self.card_pvp_pami, 1)

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
    # - usa caché si el registro ya fue cargado
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
        self._rebuild_prefetch_queue()

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
        render_troqueles_table(
            self.tbl_troqueles,
            rows=self.data.troqueles,
            estado_troquel_verde=self.ESTADO_TROQUEL_VERDE,
            estado_troquel_amarillo=self.ESTADO_TROQUEL_AMARILLO,
            estado_troquel_rojo=self.ESTADO_TROQUEL_ROJO,
            fmt_money=fmt_money,
        )

    def _render_archivo_detalle(self) -> None:
        assert self.data is not None
        render_archivo_detalle_table(
            self.tbl_arch_det,
            rows=self.data.archivo_detalles,
            fmt_money=fmt_money,
        )

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
            self._clear_preview(lado, empty_preview_text(lado))
            return

        self._last_preview_path[lado] = raw

        scroll, viewer = self._widgets_por_lado(lado)
        vw, vh = viewport_preview_size(scroll)

        if raw in self._preview_cache:

            png_bytes = self._preview_cache[raw]

            pix = pixmap_from_png_bytes(png_bytes)
            if pix is not None:
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

        if is_stale_preview_response(
            lado=lado,
            req_id=req_id,
            raw=raw,
            preview_req_id=self._preview_req_id,
            last_preview_path=self._last_preview_path,
        ):
            return

        png_bytes = out.get("png_bytes") or b""
        if not png_bytes:
            self._clear_preview(lado, "No se pudo cargar la imagen.")
            return

        scroll, viewer = self._widgets_por_lado(lado)

        self._cache_preview(raw, png_bytes)

        pix = pixmap_from_png_bytes(png_bytes)
        if pix is None:
            self._clear_preview(lado, "No se pudo leer la imagen.")
            return

        viewer.setText("")
        viewer.set_pixmap(pix)
        QTimer.singleShot(0, lambda: viewer.fit_to(scroll.viewport().size()))

    def _ui_error_preview(self, lado: str, err_text: str) -> None:
        nice = extract_preview_error(err_text)

        viewer = self.img_frente if lado == "F" else self.img_dorso
        viewer.set_pixmap(None)
        viewer.setText(f"No se pudo cargar la imagen.\n{nice}")


    def _on_motivo_item_changed(self, item: QListWidgetItem):
        if self._updating_motivos:
            return

        motivo_id = item.data(Qt.ItemDataRole.UserRole)
        if not motivo_id:
            return

        motivo_id = int(motivo_id)

        if item.checkState() != Qt.CheckState.Checked:
            self.state.debitos.pop(motivo_id, None)
            self._set_motivo_item_text(item, None)
            return

        self._edit_motivo_detail(item, motivo_id, uncheck_on_cancel=True)

    def _on_motivo_item_activated(self, item: QListWidgetItem) -> None:
        if not item or item.checkState() != Qt.CheckState.Checked:
            return

        motivo_id = item.data(Qt.ItemDataRole.UserRole)
        if not motivo_id:
            return

        self._edit_motivo_detail(item, int(motivo_id), uncheck_on_cancel=False)

    def _edit_motivo_detail(self, item: QListWidgetItem, motivo_id: int, *, uncheck_on_cancel: bool) -> None:
        if self._motivo_dialog_open:
            return

        prev = self.state.debitos.get(motivo_id) or ""

        self._motivo_dialog_open = True
        try:
            detalle, ok = QInputDialog.getText(
                self,
                "Detalle del débito",
                "Detalle (opcional):",
                text=prev,
            )
        finally:
            self._motivo_dialog_open = False

        if not ok:
            if uncheck_on_cancel:
                self._updating_motivos = True
                try:
                    item.setCheckState(Qt.CheckState.Unchecked)
                finally:
                    self._updating_motivos = False
                self.state.debitos.pop(motivo_id, None)
                self._set_motivo_item_text(item, None)
            return

        detalle_final = detalle.strip() or None
        self.state.debitos[motivo_id] = detalle_final
        self._set_motivo_item_text(item, detalle_final)

    def _set_motivo_item_text(self, item: QListWidgetItem, detalle: str | None) -> None:
        self._updating_motivos = True
        try:
            set_motivo_item_text(item, detalle)
        finally:
            self._updating_motivos = False

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
            vendedor = AuditoriaVisualUseCase.get_vendedor_info(vendedor_id=int(vid))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar el vendedor:\n{e}")
            return

        if not vendedor:
            return

        self.state.vendedor_id = int(vendedor.vendedor_id)
        self.lb_vendedor.setText(str(vendedor.descripcion or "—"))
        self.lb_vendedor.setToolTip(f"Código: {vendedor.codigo}")

    # ---------------------------------------------------------
    # Valida datos ingresados y guarda la auditoría.
    # Si es exitosa, navega automáticamente a la siguiente.
    # ---------------------------------------------------------
    def _on_finalizar(self) -> None:
        if not self.data:
            return

        payload, validation_error = build_finalizar_payload(
            data=self.data,
            state=self.state,
            prescripcion_text=self.in_prescripcion.text(),
            emision_text=self.in_emision.text(),
            venta_text=self.in_venta.text(),
        )

        if validation_error:
            if validation_error.level == "critical":
                QMessageBox.critical(self, validation_error.title, validation_error.message)
            else:
                QMessageBox.warning(self, validation_error.title, validation_error.message)
            return

        assert payload is not None
        receta_id = payload.receta_id
        debitos_inputs = payload.debitos_inputs

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
            usuario_id = self.creado_por_usuario_id
            if usuario_id is None:
                QMessageBox.warning(
                    self,
                    "Falta usuario",
                    "No se pudo determinar el usuario actual.",
                )
                return

            worker = Worker(
                self._save_auditoria_background,
                receta_id=receta_id,
                vendedor_id=self.state.vendedor_id,
                estado_seg_id=estado_seg_id,
                fecha_prescripcion=payload.fecha_prescripcion,
                fecha_emision=payload.fecha_emision,
                fecha_venta=payload.fecha_venta,
                debitos_inputs=debitos_inputs,
                usuario_id=int(usuario_id),
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

        act_delete = None

        # 🔥 verificar estado del troquel
        if row >= 0:
            estado_item = tbl.item(row, 6)
            estado = estado_item.text() if estado_item else ""

            if estado in (self.ESTADO_TROQUEL_AMARILLO, self.ESTADO_TROQUEL_ROJO):
                act_delete = menu.addAction("Eliminar troquel")

        chosen = menu.exec(tbl.viewport().mapToGlobal(pos))
        if not chosen:
            return

        if chosen == act_add:
            self._ctx_add_troquel()

        elif chosen == act_edit:
            self._ctx_edit_troquel_qty()

        elif act_delete and chosen == act_delete:
            self._ctx_delete_troquel()

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
            QMessageBox.warning(self, "Error", "No se pudo determinar el troquel.")
            return

        codigo = (
            it0.text()
            if it0
            else ""
        ).strip()

        item_qty = self.tbl_troqueles.item(row, 2)
        qty_txt = (
            item_qty.text()
            if item_qty
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
            QMessageBox.warning(self, "Error", "No se pudo determinar el archivo.")
            return

        dlg = HistorialDialog(archivo_id_actual=archivo_id, parent=self)
        dlg.exec()

    def _on_next_only(self):

        if self._idx + 1 < len(self._asociacion_ids):
            self._goto(self._idx + 1)
            return

        # si es la última → cerrar dialog
        self.accept()

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
    # Construye cola bidireccional de prefetch alrededor del
    # índice actual: +1, -1, +2, -2, ... (hasta PREFETCH_SIZE).
    # ---------------------------------------------------------
    def _rebuild_prefetch_queue(self) -> None:
        self._prefetch_queue = build_prefetch_queue(
            asociacion_ids=self._asociacion_ids,
            current_index=self._idx,
            prefetch_size=self.PREFETCH_SIZE,
            cached_ids={int(x) for x in self._data_cache.keys()},
            loading_ids=self._loading_ids,
        )

    # ---------------------------------------------------------
    # Precarga en background asociaciones cercanas para
    # navegación fluida en ambos sentidos.
    # ---------------------------------------------------------
    def _preload_batch(self):

        if self._prefetch_running:
            return

        if not self._prefetch_queue:
            return

        asociacion_id = pop_next_prefetch(
            self._prefetch_queue,
            cached_ids={int(x) for x in self._data_cache.keys()},
            loading_ids=self._loading_ids,
        )

        if not asociacion_id:
            return

        self._loading_ids.add(asociacion_id)
        self._prefetch_running = True

        w = Worker(
            self._load_data_background_sync,
            asociacion_id=asociacion_id
        )

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

        self.list_motivos.clear()

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

        if event.key() not in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            super().keyPressEvent(event)
            return

        focus = self.focusWidget()

        # ENTER en fecha de venta
        if focus is self.in_venta:

            fecha_venta = parse_ddmmyyyy(self.in_venta.text())

            # si no hay fecha, no hacer nada
            if not fecha_venta:
                return

            # pasar foco a finalizar
            self.btn_finalizar.setFocus()
            return

        # ENTER en botón finalizar
        if focus is self.btn_finalizar:
            self._on_finalizar()
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
        put_preview_cache_item(
            self._preview_cache,
            raw=raw,
            img_bytes=img_bytes,
            max_items=self.MAX_PREVIEW_CACHE,
        )

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
            usuario_id,
    ):
        AuditoriaVisualUseCase.finalizar_auditoria(
            receta_id=receta_id,
            vendedor_id=vendedor_id,
            estado_seguimiento_id=estado_seg_id,
            fecha_prescripcion=fecha_prescripcion,
            fecha_emision=fecha_emision,
            fecha_venta=fecha_venta,
            usuario_id=int(usuario_id),
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
                self._clear_preview(lado, empty_preview_text(lado))

    def _render_motivos(self):

        if not self.data:
            return

        render_motivos_list(
            self.list_motivos,
            motivos_frente=self.data.motivos_frente,
            motivos_dorso=self.data.motivos_dorso,
            selected_debitos=self.state.debitos,
        )

    def _render_header(self):
        if not self.data:
            return

        render_header_fields(
            data=self.data,
            in_prescripcion=self.in_prescripcion,
            in_emision=self.in_emision,
            in_venta=self.in_venta,
            lb_big=self.lb_big,
            lb_autorizacion=self.lb_autorizacion,
            btn_debitada=self.btn_debitada,
            fmt_date=fmt_date,
        )

    def _render_resumen(self):
        if not self.data:
            return

        render_resumen_fields(
            data=self.data,
            lb_a_cargo=self.lb_a_cargo,
            lb_imp_obs=self.lb_imp_obs,
            lb_imp_neto=self.lb_imp_neto,
            fmt_money=fmt_money,
        )

    def _render_navigation(self):
        render_navigation_label(
            lb_pos=self.lb_pos,
            idx=self._idx,
            total=len(self._asociacion_ids),
        )

    # ---------------------------------------------------------
    # Precarga previews de frente/dorso en background
    # y los guarda en cache de imágenes.
    # ---------------------------------------------------------
    def _preload_images_for_data(self, data):

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
        self._loading_ids.discard(asociacion_id)

        self._preload_images_for_data(data)
        self._rebuild_prefetch_queue()

        self._prefetch_running = False

        self._preload_batch()

    def _ctx_delete_troquel(self):

        row = self.tbl_troqueles.currentRow()
        if row < 0:
            return

        it0 = self.tbl_troqueles.item(row, 0)
        estado_item = self.tbl_troqueles.item(row, 6)
        estado = estado_item.text() if estado_item else ""
        if not it0:
            return

        troquel_id = int(it0.data(Qt.ItemDataRole.UserRole) or 0)

        if not troquel_id:
            QMessageBox.warning(self, "Error", "No se pudo determinar el troquel.")
            return

        if estado == self.ESTADO_TROQUEL_ROJO:
            ok = QMessageBox.warning(
                self,
                "Eliminar troquel rechazado",
                (
                    "⚠ Este troquel está en estado RECHAZADO.\n\n"
                    "Eliminar este troquel puede romper la auditoría "
                    "y generar inconsistencias en la validación.\n\n"
                    "Verificá correctamente la receta física antes de continuar."
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

        else:
            ok = QMessageBox.question(
                self,
                "Eliminar troquel",
                "¿Seguro que querés eliminar este troquel?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

        if ok != QMessageBox.StandardButton.Yes:
            return

        try:
            AuditoriaVisualUseCase.delete_troquel(troquel_id=troquel_id)

            # 🔥 invalidar cache
            if self.asociacion_id:
                asoc_id = int(self.asociacion_id)
                self._data_cache.pop(asoc_id, None)

            # recargar
            self._goto(self._idx)

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo eliminar el troquel:\n{e}"
            )
