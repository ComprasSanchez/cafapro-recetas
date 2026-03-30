from __future__ import annotations

from datetime import date, datetime

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QHBoxLayout, QLabel, QPushButton,
    QDateEdit, QMessageBox, QLineEdit, QSizePolicy, QGridLayout,
    QTableWidgetItem, QTableWidget, QAbstractItemView
)

from config.config_manager import ConfigManager
from ui.dialogs.dias_descargado_dialog import DiasDescargadosDialog
from ui.dialogs.recepcion_create_dialog import RecepcionCreateDialog
from ui.dialogs.recepcion_pick_dialog import RecepcionPickDialog

from ui.tabs.base_tab import BaseTabWidget
from ui.usecase.carga_recepcion_usecase import (
    CargaRecepcionUseCase,
    LoadRecepcionOut,
    ListImagesOut,
    ProcesarOut,
    ProcesarCargaIn,
)
from ui.windows.excluidos_window import ExcluidosWindow
from ui.windows.listado_debitos_window import ListadoDebitosWindow


class CargaRecepcionTab(BaseTabWidget):
    def __init__(self, creado_por_usuario_id, parent=None):
        super().__init__(parent)
        self.creado_por_usuario_id = creado_por_usuario_id
        self.cfg = ConfigManager()
        self._recepcion_id: int | None = None
        self._fecha: datetime | None = None

        self.imed: str | None = None
        self.obs: str | None = None

        self._uc = CargaRecepcionUseCase()

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        root.addWidget(self._build_header(), 0)
        root.addWidget(self._build_table_card(), 1)

    # --------------------------
    # Helpers UI
    # --------------------------
    @staticmethod
    def _ro_line(text: str = "—") -> QLineEdit:
        le = QLineEdit(text)
        le.setReadOnly(True)
        le.setFocusPolicy(Qt.NoFocus)
        le.setMinimumHeight(28)
        le.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return le

    @staticmethod
    def _btn(
        text: str,
        *,
        variant: str = "ghost",
        size: str = "md",
        w: int | None = None,
        h: int | None = None,
        enabled: bool = True,
    ) -> QPushButton:
        b = QPushButton(text)
        b.setProperty("variant", variant)
        b.setProperty("size", size)
        b.setEnabled(enabled)
        if w is not None:
            b.setFixedWidth(w)
        if h is not None:
            b.setMinimumHeight(h)
        return b

    @staticmethod
    def _fmt_duration(seconds: float) -> str:
        total = max(0, int(round(float(seconds))))
        hh, rem = divmod(total, 3600)
        mm, ss = divmod(rem, 60)
        if hh > 0:
            return f"{hh:02d}:{mm:02d}:{ss:02d}"
        return f"{mm:02d}:{ss:02d}"

    def _set_actions_enabled(self, enabled: bool) -> None:
        self.btn_pick_recepcion.setEnabled(enabled)
        self.btn_new_recepcion.setEnabled(enabled)
        self.btn_cargar.setEnabled(enabled)
        self.btn_procesar.setEnabled(enabled)
        self.btn_cerrar.setEnabled(enabled)
        self.btn_debitos.setEnabled(enabled)
        self.btn_excluidos.setEnabled(enabled)
        self.btn_dias_descargados.setEnabled(enabled)
        self.de_fecha.setEnabled(enabled)

    def _show_job_error(self, err: str) -> None:
        QMessageBox.critical(self, "Error del proceso", err)

    # --------------------------
    # Header
    # --------------------------
    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("card")
        header.setMaximumHeight(128)

        grid = QGridLayout(header)
        grid.setContentsMargins(12, 10, 12, 10)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        lb_num = QLabel("N° Recepción:")
        self.in_numero = self._ro_line()
        self.in_numero.setMinimumWidth(120)

        self.btn_pick_recepcion = self._btn("…", variant="ghost", size="sm", w=32, h=28)
        self.btn_new_recepcion = self._btn("+", variant="ghost", size="sm", w=32, h=28)

        lb_obra = QLabel("Obra social:")
        self.in_obra = self._ro_line()
        self.in_obra.setMinimumWidth(300)

        lb_prest = QLabel("Prestador:")
        self.in_prestador = self._ro_line()
        self.in_prestador.setMinimumWidth(300)

        lb_periodo = QLabel("Período:")
        self.in_periodo = self._ro_line()
        self.in_periodo.setMinimumWidth(120)

        lb_quincena = QLabel("Quincena:")
        self.in_quincena = self._ro_line()
        self.in_quincena.setFixedWidth(70)
        self.in_quincena.setAlignment(Qt.AlignCenter)

        self.de_fecha = QDateEdit()
        self.de_fecha.setCalendarPopup(True)
        self.de_fecha.setDate(QDate.currentDate())
        self.de_fecha.setDisplayFormat("dd/MM/yyyy")
        self.de_fecha.setMinimumHeight(28)
        self.de_fecha.setFixedWidth(120)
        self.btn_dias_descargados = self._btn("Días descargados", variant="ghost", size="md", w=140, h=32)

        self.btn_cargar = self._btn("Cargar", variant="ghost", size="md", w=90, h=32)
        self.btn_procesar = self._btn("Procesar", variant="primary", size="md", w=90, h=32)

        self.btn_cerrar = self._btn("Cerrar recepción", variant="ghost", size="md", w=140, h=32)
        self.btn_debitos = self._btn("Débitos", variant="ghost", size="md", w=90, h=32)
        self.btn_excluidos = self._btn("Excluidos", variant="ghost", size="md", w=90, h=32)

        fecha_box = QWidget()
        fecha_l = QHBoxLayout(fecha_box)
        fecha_l.setContentsMargins(0, 0, 0, 0)
        fecha_l.setSpacing(6)
        fecha_l.addWidget(self.de_fecha)

        right_box = QWidget()
        right_l = QVBoxLayout(right_box)
        right_l.setContentsMargins(0, 0, 0, 0)
        right_l.setSpacing(6)

        right_top = QWidget()
        right_top_l = QHBoxLayout(right_top)
        right_top_l.setContentsMargins(0, 0, 0, 0)
        right_top_l.setSpacing(8)
        right_top_l.addWidget(self.btn_cargar)
        right_top_l.addWidget(self.btn_procesar)
        right_top_l.addWidget(self.btn_cerrar)

        right_bottom = QWidget()
        right_bottom_l = QHBoxLayout(right_bottom)
        right_bottom_l.setContentsMargins(0, 0, 0, 0)
        right_bottom_l.setSpacing(8)
        right_bottom_l.addWidget(self.btn_debitos)
        right_bottom_l.addWidget(self.btn_excluidos)
        right_bottom_l.addWidget(self.btn_dias_descargados)

        right_l.addWidget(right_top)
        right_l.addWidget(right_bottom)

        num_box = QWidget()
        num_l = QHBoxLayout(num_box)
        num_l.setContentsMargins(0, 0, 0, 0)
        num_l.setSpacing(6)
        num_l.addWidget(self.in_numero, 1)
        num_l.addWidget(self.btn_pick_recepcion, 0)
        num_l.addWidget(self.btn_new_recepcion, 0)

        grid.addWidget(lb_num, 0, 0, Qt.AlignmentFlag.AlignRight)
        grid.addWidget(num_box, 0, 1, 1, 3)

        grid.addWidget(lb_obra, 0, 4, Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self.in_obra, 0, 5, 1, 4)

        grid.addWidget(lb_prest, 1, 0, Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self.in_prestador, 1, 1, 1, 3)

        grid.addWidget(lb_periodo, 1, 4, Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self.in_periodo, 1, 5)

        grid.addWidget(lb_quincena, 1, 6, Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self.in_quincena, 1, 7)

        grid.addWidget(fecha_box, 1, 9)

        grid.setColumnStretch(8, 1)
        grid.addWidget(right_box, 0, 10, 2, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.btn_pick_recepcion.clicked.connect(self._on_pick_recepcion)
        self.btn_new_recepcion.clicked.connect(self._on_new_recepcion)
        self.btn_cargar.clicked.connect(self._on_cargar)
        self.btn_procesar.clicked.connect(self._on_procesar)
        self.btn_cerrar.clicked.connect(self._on_cerrar_recepcion)
        self.btn_debitos.clicked.connect(self._on_open_debitos)
        self.btn_excluidos.clicked.connect(self._on_open_excluidos)
        self.btn_dias_descargados.clicked.connect(self._on_dias_descargados)

        return header

    # --------------------------
    # Tabla
    # --------------------------
    def _build_table_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)
        self.tbl_imgs = self._build_table()
        lay.addWidget(self.tbl_imgs, 1)
        return card

    @staticmethod
    def _build_table() -> QTableWidget:
        t = QTableWidget()
        t.setColumnCount(4)
        t.setHorizontalHeaderLabels(["Archivo", "Fecha", "Hora", "Ruta"])
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.setFocusPolicy(Qt.NoFocus)
        header = t.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.setHighlightSections(False)
        header.setStretchLastSection(True)
        header.setMinimumSectionSize(80)
        t.setColumnWidth(0, 260)
        t.setColumnWidth(1, 140)
        t.setColumnWidth(2, 90)
        t.setColumnWidth(3, 520)
        t.verticalHeader().setVisible(False)
        t.setSortingEnabled(True)
        t.setAlternatingRowColors(True)
        return t

    def _clear_images_table(self) -> None:
        self.tbl_imgs.setRowCount(0)

    # --------------------------
    # Recepción (async)
    # --------------------------
    def _on_pick_recepcion(self):
        dlg = RecepcionPickDialog(self, show_closed=False, enable_filter=False)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        rid = dlg.selected()[0]
        if not rid:
            return

        self.run_job(
            self._uc.load_recepcion,
            recepcion_id=rid,
            title="Cargando recepción…",
            on_result=self._apply_recepcion,
            on_error=self._show_job_error,
        )

    def _on_new_recepcion(self):
        dlg = RecepcionCreateDialog(self, creado_por_usuario_id=self.creado_por_usuario_id)
        if dlg.exec() == dlg.DialogCode.Accepted and dlg.created_recepcion_id:
            rid = dlg.created_recepcion_id
            self.run_job(
                self._uc.load_recepcion,
                recepcion_id=rid,
                title="Cargando recepción…",
                on_result=self._apply_recepcion,
            )
            return

        QMessageBox.information(self, "Listo", "Recepción creada. Ahora seleccionála con 'Elegir recepción…'.")

    def _apply_recepcion(self, out: LoadRecepcionOut) -> None:
        self._recepcion_id = out.recepcion_id

        self.in_numero.setText(out.numero)
        self.in_prestador.setText(out.prestador)
        self.in_obra.setText(out.obra_social)
        self.in_periodo.setText(out.periodo)

        self.obs = out.obs
        self.imed = out.imed

        quincena = "—"
        if "Q1" in out.periodo:
            quincena = "1ª"
        elif "Q2" in out.periodo:
            quincena = "2ª"
        self.in_quincena.setText(quincena)

        self._clear_images_table()
        self._set_actions_enabled(True)
        self.footer_set(info=f"Recepción {out.recepcion_id} lista")

    # --------------------------
    # Cargar imágenes (async)
    # --------------------------
    def _on_cargar(self) -> None:
        self._clear_images_table()

        if not self._recepcion_id:
            QMessageBox.warning(self, "Atención", "Primero seleccioná una recepción.")
            return
        if not self.imed or not self.obs:
            QMessageBox.warning(self, "Atención", "La recepción seleccionada no tiene IMED/obra social.")
            return

        date_str = self.de_fecha.date().toString("dd/MM/yyyy")

        self.run_job(
            self._uc.list_images,
            imed=self.imed,
            obs=self.obs,
            date_str=date_str,
            title="Listando imágenes…",
            on_result=self._render_images,
        )

    def _render_images(self, out: ListImagesOut) -> None:
        rows = out.rows
        if not rows:
            self.footer_set(info="No se encontraron imágenes")
            return

        self.tbl_imgs.setSortingEnabled(False)
        self.tbl_imgs.setRowCount(len(rows))

        for r, it in enumerate(rows):
            self.tbl_imgs.setItem(r, 0, QTableWidgetItem(str(it.get("name", ""))))
            self.tbl_imgs.setItem(r, 1, QTableWidgetItem(str(it.get("date", ""))))
            self.tbl_imgs.setItem(r, 2, QTableWidgetItem(str(it.get("time", ""))))
            self.tbl_imgs.setItem(r, 3, QTableWidgetItem(str(it.get("full_path", ""))))

        self.tbl_imgs.setSortingEnabled(True)
        self.tbl_imgs.resizeColumnsToContents()
        self.footer_set(info=f"{len(rows)} imágenes cargadas")

    # --------------------------
    # Procesar (async)
    # --------------------------
    def _on_procesar(self) -> None:
        if not self._recepcion_id:
            QMessageBox.warning(self, "Atención", "Primero seleccioná una recepción.")
            return
        if self.tbl_imgs.rowCount() == 0:
            QMessageBox.warning(self, "Atención", "No hay imágenes cargadas para procesar.")
            return

        items: list[ProcesarCargaIn] = []
        for r in range(self.tbl_imgs.rowCount()):
            file_name = self.tbl_imgs.item(r, 0).text().strip() if self.tbl_imgs.item(r, 0) else ""
            full_path = self.tbl_imgs.item(r, 3).text().strip() if self.tbl_imgs.item(r, 3) else ""
            if file_name and full_path:
                items.append(ProcesarCargaIn(file_name=file_name, full_path=full_path))

        if not items:
            QMessageBox.warning(self, "Atención", "No hay rutas válidas para procesar.")
            return

        self.run_job(
            self._uc.procesar,
            recepcion_id=self._recepcion_id,
            usuario_id=self.creado_por_usuario_id,
            items=items,
            title="Procesando…",
            on_result=self._show_procesar_result,
        )

    def _show_procesar_result(self, out: ProcesarOut) -> None:
        resumen = out.resumen

        msg = (
            f"Procesadas: {resumen.ok}\n"
            f"Sin coincidencia: {resumen.sin_match}\n"
            f"Duplicadas (nro_referencia en múltiples archivos): {resumen.duplicados}\n"
            f"Ya asociadas: {resumen.ya_asociado}"
        )
        if getattr(resumen, "errores", None):
            errs = resumen.errores or []
            if errs:
                msg += "\n\nErrores:\n" + "\n".join(errs[:10])
                if len(errs) > 10:
                    msg += f"\n... y {len(errs) - 10} más"

        stats = getattr(resumen, "stats", None)
        if stats is not None:
            elapsed = float(getattr(stats, "elapsed_seconds", 0.0) or 0.0)
            rpm = float(getattr(stats, "items_per_minute", 0.0) or 0.0)
            sec_item = float(getattr(stats, "seconds_per_item", 0.0) or 0.0)
            processed_items = int(getattr(stats, "processed_items", 0) or 0)
            total_items = int(getattr(stats, "total_items", 0) or 0)
            chunk_count = int(getattr(stats, "chunk_count", 0) or 0)
            cmin = float(getattr(stats, "chunk_min_seconds", 0.0) or 0.0)
            cavg = float(getattr(stats, "chunk_avg_seconds", 0.0) or 0.0)
            cmax = float(getattr(stats, "chunk_max_seconds", 0.0) or 0.0)
            con_header = int(getattr(stats, "con_header", 0) or 0)
            sin_header = int(getattr(stats, "sin_header", 0) or 0)
            rev_sin_match = int(getattr(stats, "revision_por_sin_match", 0) or 0)
            rev_ya_asoc = int(getattr(stats, "revision_por_ya_asociado", 0) or 0)
            reintentos_seguro = int(getattr(stats, "reintentos_modo_seguro", 0) or 0)

            msg += (
                "\n\nEstadísticas:\n"
                f"Items procesados: {processed_items}/{total_items}\n"
                f"Tiempo total: {self._fmt_duration(elapsed)}\n"
                f"Ritmo: {rpm:.1f} recetas/min\n"
                f"Promedio: {sec_item:.2f} s/receta\n"
                f"Chunks: {chunk_count}\n"
                f"Chunk min/prom/max: {cmin:.1f}s / {cavg:.1f}s / {cmax:.1f}s\n"
                f"Con header: {con_header} | Sin header: {sin_header}\n"
                f"Revision por sin match: {rev_sin_match}\n"
                f"Revision por ya asociado: {rev_ya_asoc}\n"
                f"Reintentos modo seguro: {reintentos_seguro}"
            )

        QMessageBox.information(self, "Resultado del procesamiento", msg)

    def _on_open_debitos(self) -> None:
        if not self._recepcion_id:
            QMessageBox.warning(self, "Atención", "Primero seleccioná una recepción.")
            return

        numero = self.in_numero.text().strip()
        dlg = ListadoDebitosWindow(
            self,
            recepcion_id=self._recepcion_id,
            recepcion_numero=numero,
        )
        dlg.exec()

    def _on_open_excluidos(self) -> None:
        if not self._recepcion_id:
            QMessageBox.warning(self, "Atención", "Primero seleccioná una recepción.")
            return

        numero = self.in_numero.text().strip()
        dlg = ExcluidosWindow(
            self,
            recepcion_id=self._recepcion_id,
            recepcion_numero=numero,
        )
        dlg.exec()

    def _on_dias_descargados(self) -> None:
        if not self._recepcion_id:
            QMessageBox.warning(self, "Atención", "Primero seleccioná una recepción.")
            return

        fechas = self._uc.list_fechas_descargadas(recepcion_id=self._recepcion_id)

        dlg = DiasDescargadosDialog(
            recepcion_id=self._recepcion_id,
            fechas_descargadas=fechas,
            parent=self,
        )

        def on_pick(d: date) -> None:
            self.de_fecha.setDate(QDate(d.year, d.month, d.day))

        dlg.dateSelected.connect(on_pick)
        dlg.exec()

    def _on_cerrar_recepcion(self) -> None:
        if not self._recepcion_id:
            QMessageBox.warning(self, "Atención", "Primero seleccioná una recepción.")
            return

        ans = QMessageBox.question(
            self,
            "Cerrar recepción",
            f"¿Querés cerrar la recepción #{self.in_numero.text()}?\n"
            "Se cambiará su estado a CERRADA.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return

        self.run_job(
            self._uc.cerrar_recepcion,  # debe existir en el UseCase
            recepcion_id=self._recepcion_id,
            title="Cerrando recepción…",
            on_result=self._on_recepcion_cerrada,
            on_error=self._show_job_error,
        )

    def _on_recepcion_cerrada(self, out) -> None:
        rid = getattr(out, "recepcion_id", None) or self._recepcion_id
        self.footer_set(info=f"Recepción {rid} cerrada")
        QMessageBox.information(self, "Listo", f"Recepción {rid} cerrada correctamente.")

        # opcional: deshabilitar acciones al cerrar
        self.btn_cargar.setEnabled(False)
        self.btn_procesar.setEnabled(False)
        self.btn_cerrar.setEnabled(False)
        self.de_fecha.setEnabled(False)

