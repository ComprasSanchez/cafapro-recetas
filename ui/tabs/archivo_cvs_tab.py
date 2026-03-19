from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QLineEdit, QSizePolicy, QGridLayout,
    QTableWidgetItem, QTableWidget, QAbstractItemView, QSplitter, QHeaderView, QDateEdit
)

from app.db.session import session_scope
from app.service.recetas.archivo_service import ArchivoService
from ui.dialogs.dias_descargado_dialog import DiasDescargadosDialog
from ui.tabs.base_tab import BaseTabWidget
from ui.dialogs.recepcion_pick_dialog import RecepcionPickDialog

from ui.usecase.archivo_cvs_usecase import (
    ArchivoCvsUseCase,
    RecepcionOut,
    CsvOut,
    SubirOut,
)


class ArchivoCvsTab(BaseTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._recepcion_id: int | None = None

        self.imed: str | None = None
        self.obs: str | None = None
        self._validador: str = "imed"
        self._codigo_financiador: int | None = None

        self._uc = ArchivoCvsUseCase()

        # data en memoria
        self._recetas_por_ref: dict[str, dict] = {}
        self._detalles_por_ref: dict[str, list[dict]] = {}
        self._current_ref: str | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        header = self._build_header()
        root.addWidget(header)

        body = self._build_body()
        root.addWidget(body, 1)

    # --------------------------
    # UI helpers
    # --------------------------
    @staticmethod
    def _ro_line(text: str = "-") -> QLineEdit:
        le = QLineEdit(text)
        le.setReadOnly(True)
        le.setFocusPolicy(Qt.NoFocus)
        le.setMinimumHeight(26)
        le.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return le

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("card")
        header.setMaximumHeight(90)

        grid = QGridLayout(header)
        grid.setContentsMargins(12, 10, 12, 10)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        # ===== Controles =====
        lb_num = QLabel("N° Recepción:")
        self.in_numero = self._ro_line()
        self.in_numero.setFixedWidth(90)

        self.btn_pick_recepcion = QPushButton("…")
        self.btn_pick_recepcion.setFixedSize(32, 26)

        # (si no usás "nueva" acá, lo dejo oculto para mantener layout)
        self.btn_new_recepcion = QPushButton("+")
        self.btn_new_recepcion.setFixedSize(32, 26)
        self.btn_new_recepcion.setVisible(False)

        lb_obra = QLabel("Obra social:")
        self.in_obra = self._ro_line()
        self.in_obra.setFixedWidth(360)

        lb_prest = QLabel("Prestador:")
        self.in_prestador = self._ro_line()
        self.in_prestador.setFixedWidth(360)

        lb_imed = QLabel("IMED:")
        self.in_imed = self._ro_line()
        self.in_imed.setFixedWidth(220)

        self.de_fecha = QDateEdit()
        self.de_fecha.setCalendarPopup(True)
        self.de_fecha.setDate(QDate.currentDate())
        self.de_fecha.setDisplayFormat("dd/MM/yyyy")
        self.de_fecha.setFixedSize(110, 26)

        # ===== Botones derecha =====
        self.btn_cargar = QPushButton("Cargar")
        self.btn_cargar.setFixedSize(90, 26)

        self.btn_subir = QPushButton("Subir")
        self.btn_subir.setFixedSize(90, 26)

        self.btn_dias_descargados = QPushButton("Días Descargados")
        self.btn_dias_descargados.setFixedSize(120, 26)

        right_box = QWidget()
        right_l = QHBoxLayout(right_box)
        right_l.setContentsMargins(0, 0, 0, 0)
        right_l.setSpacing(6)
        right_l.addWidget(self.btn_cargar)
        right_l.addWidget(self.btn_subir)
        right_l.addStretch(0)

        # ===== Bloque compacto para N° Recepción + botones =====
        num_box = QWidget()
        num_l = QHBoxLayout(num_box)
        num_l.setContentsMargins(0, 0, 0, 0)
        num_l.setSpacing(4)

        self.in_numero.setMinimumWidth(140)
        self.in_numero.setMaximumWidth(9999)
        self.in_numero.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        num_l.addWidget(self.in_numero, 1)
        num_l.addWidget(self.btn_pick_recepcion, 0)
        num_l.addWidget(self.btn_new_recepcion, 0)

        # ===== Layout (2 filas) =====
        grid.addWidget(lb_num, 0, 0, Qt.AlignmentFlag.AlignRight)
        grid.addWidget(num_box, 0, 1, 1, 3)

        grid.addWidget(lb_obra, 0, 4, Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self.in_obra, 0, 5, 1, 4)

        grid.addWidget(lb_prest, 1, 0, Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self.in_prestador, 1, 1, 1, 3)

        grid.addWidget(lb_imed, 1, 4, Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self.in_imed, 1, 5)

        fecha_box = QWidget()
        fecha_l = QHBoxLayout(fecha_box)
        fecha_l.setContentsMargins(0, 0, 0, 0)
        fecha_l.setSpacing(6)
        fecha_l.addWidget(self.de_fecha)
        fecha_l.addWidget(self.btn_dias_descargados)

        grid.addWidget(fecha_box, 1, 9)

        grid.setColumnStretch(8, 1)
        grid.addWidget(right_box, 1, 10, Qt.AlignmentFlag.AlignRight)

        # señales
        self.btn_pick_recepcion.clicked.connect(self._on_pick_recepcion)
        self.btn_cargar.clicked.connect(self._on_cargar)
        self.btn_subir.clicked.connect(self._on_subir)
        self.btn_dias_descargados.clicked.connect(self._on_dias_descargados)

        return header

    def _build_body(self) -> QSplitter:
        split = QSplitter(Qt.Orientation.Horizontal)

        # ===== Izq: recetas =====
        left = QWidget()
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(0, 0, 0, 0)
        left_l.setSpacing(10)

        self.tbl_recetas = QTableWidget()
        self.tbl_recetas.setColumnCount(9)
        self.tbl_recetas.setHorizontalHeaderLabels([
            "Nro Referencia",
            "Nro Receta",
            "Beneficiario",
            "Fecha",
            "Hora",
            "Importe Gral",
            "Importe Obs",
            "A Cargo Entidad",
            "Orden Del Lote",
        ])
        self.tbl_recetas.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_recetas.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_recetas.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_recetas.verticalHeader().setVisible(False)
        self.tbl_recetas.setAlternatingRowColors(True)
        self.tbl_recetas.setSortingEnabled(True)

        h1 = self.tbl_recetas.horizontalHeader()
        h1.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        h1.setHighlightSections(False)
        h1.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        left_l.addWidget(QLabel("Recetas (IMED)"))
        left_l.addWidget(self.tbl_recetas, 1)

        # ===== Der: detalles =====
        right = QWidget()
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(0, 0, 0, 0)
        right_l.setSpacing(10)

        self.tbl_detalles = QTableWidget()
        self.tbl_detalles.setColumnCount(9)
        self.tbl_detalles.setHorizontalHeaderLabels([
            "Cód. Medic.", "Nombre", "Present.", "Estado", "Nro. aut.",
            "Cant.", "Importe Gral.", "Importe Obs", "Desc."
        ])
        self.tbl_detalles.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_detalles.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_detalles.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_detalles.verticalHeader().setVisible(False)
        self.tbl_detalles.setAlternatingRowColors(True)

        h2 = self.tbl_detalles.horizontalHeader()
        h2.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        h2.setHighlightSections(False)
        h2.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        right_l.addWidget(QLabel("Detalles"))
        right_l.addWidget(self.tbl_detalles, 1)

        split.addWidget(left)
        split.addWidget(right)
        split.setStretchFactor(0, 2)
        split.setStretchFactor(1, 3)

        self.tbl_recetas.itemSelectionChanged.connect(self._on_select_receta)

        return split

    # --------------------------
    # Recepción (async)
    # --------------------------
    def _on_pick_recepcion(self):
        dlg = RecepcionPickDialog(self, show_closed=False, enable_filter=False)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        selected = dlg.selected()
        rid = next(iter(selected or []), None)
        if not rid:
            return

        self.run_job(
            self._uc.load_recepcion,
            recepcion_id=rid,
            title="Cargando recepción…",
            on_result=self._apply_recepcion,
            on_error=self._show_worker_error,
        )

    def _apply_recepcion(self, out: RecepcionOut) -> None:
        self._recepcion_id = out.recepcion_id

        self.in_numero.setText(out.numero)
        self.in_prestador.setText(out.prestador)
        self.in_obra.setText(out.obra_social)

        self.imed = out.imed
        self.obs = out.obs
        self._validador = (out.validador or "imed").strip().lower()
        self._codigo_financiador = out.codigo_financiador
        self.in_imed.setText(self.imed)

        usa_csv = self._validador == "imed"
        self.de_fecha.setEnabled(usa_csv)

        # al cambiar recepción: limpiar tablas / cache
        self._recetas_por_ref = {}
        self._detalles_por_ref = {}
        self._current_ref = None
        self._render_recetas()
        self._render_detalles(None)

    def _show_worker_error(self, err: str) -> None:
        QMessageBox.critical(self, "Error", err)

    def _enable_subir_controls(self) -> None:
        self.btn_subir.setEnabled(True)
        self.btn_cargar.setEnabled(True)

    # --------------------------
    # CSV (async)
    # --------------------------
    def _on_cargar(self) -> None:
        imed = self.in_imed.text().strip()
        fecha = self.de_fecha.date().toString("dd/MM/yyyy")
        obs = self.in_obra.text().strip()

        if not imed:
            QMessageBox.warning(self, "Atención", "Primero seleccioná una recepción (para tener IMED).")
            return

        if self._validador != "imed" and self._codigo_financiador is None:
            QMessageBox.warning(self, "Atención", "La obra social no tiene código financiador configurado.")
            return

        self.run_job(
            self._uc.load_csv,
            imed=imed,
            fecha_str=fecha,
            obs=obs,
            validador=self._validador,
            nro_prestador=imed,
            codigo_financiador=self._codigo_financiador,
            title="Cargando recetas…",
            on_result=self._apply_csv,
        )

    def _apply_csv(self, out: CsvOut) -> None:
        self._recetas_por_ref = out.recetas_por_ref or {}
        self._detalles_por_ref = out.detalles_por_ref or {}
        self._current_ref = None

        self._render_recetas()
        self._render_detalles(None)

        if self.tbl_recetas.rowCount() > 0:
            self.tbl_recetas.selectRow(0)

    def _render_recetas(self) -> None:
        self.tbl_recetas.setSortingEnabled(False)
        self.tbl_recetas.setUpdatesEnabled(False)
        try:
            self.tbl_recetas.clearContents()
            self.tbl_recetas.setRowCount(0)

            for nro_ref in sorted(self._recetas_por_ref.keys()):
                receta = self._recetas_por_ref[nro_ref]

                r = self.tbl_recetas.rowCount()
                self.tbl_recetas.insertRow(r)

                # 0) Nro Referencia (UserRole)
                it_ref = QTableWidgetItem(str(nro_ref))
                it_ref.setData(Qt.UserRole, str(nro_ref))
                self.tbl_recetas.setItem(r, 0, it_ref)

                nro_receta = receta.get("Nro_Receta") or receta.get("Nro Receta") or ""
                self.tbl_recetas.setItem(r, 1, QTableWidgetItem(str(nro_receta)))

                beneficiario = receta.get("Beneficiario") or ""
                self.tbl_recetas.setItem(r, 2, QTableWidgetItem(str(beneficiario)))

                fecha = receta.get("Fecha") or ""
                self.tbl_recetas.setItem(r, 3, QTableWidgetItem(str(fecha)))

                hora = receta.get("Hora") or ""
                self.tbl_recetas.setItem(r, 4, QTableWidgetItem(str(hora)))

                imp_gral = receta.get("Importe_Gral") or receta.get("Importe Gral") or ""
                self.tbl_recetas.setItem(r, 5, QTableWidgetItem(str(imp_gral)))

                imp_pami = receta.get("Importe_Pami") or receta.get("Importe Pami") or ""
                self.tbl_recetas.setItem(r, 6, QTableWidgetItem(str(imp_pami)))

                cargo = receta.get("A_Cargo_Entidad") or receta.get("A Cargo Entidad") or ""
                self.tbl_recetas.setItem(r, 7, QTableWidgetItem(str(cargo)))

                orden = receta.get("Orden_Del_Lote") or receta.get("Orden Del Lote") or ""
                self.tbl_recetas.setItem(r, 8, QTableWidgetItem(str(orden)))
        finally:
            self.tbl_recetas.setUpdatesEnabled(True)
            self.tbl_recetas.setSortingEnabled(True)

        self.tbl_recetas.resizeColumnsToContents()

    def _on_select_receta(self) -> None:
        row = self.tbl_recetas.currentRow()
        if row < 0:
            self._current_ref = None
            self._render_detalles(None)
            return

        it = self.tbl_recetas.item(row, 0)
        if not it:
            return

        nro_ref = it.data(Qt.UserRole) or it.text()
        self._current_ref = str(nro_ref)
        self._render_detalles(self._current_ref)

    def _render_detalles(self, nro_ref: str | None):
        self.tbl_detalles.setUpdatesEnabled(False)
        try:
            self.tbl_detalles.clearContents()
            self.tbl_detalles.setRowCount(0)

            if not nro_ref:
                return

            detalles = self._detalles_por_ref.get(nro_ref, [])
            for d in detalles:
                r = self.tbl_detalles.rowCount()
                self.tbl_detalles.insertRow(r)

                cod = d.get("cod_medic") or ""
                nom = d.get("nombre") or ""
                pre = d.get("presentacion") or ""
                est = d.get("estado") or ""
                aut = d.get("nro_aut") or ""
                can = d.get("cantidad") or ""
                igr = d.get("importe_gral") or ""
                ipa = d.get("importe_pami") or ""
                des = d.get("desc") or ""

                self.tbl_detalles.setItem(r, 0, QTableWidgetItem(str(cod)))
                self.tbl_detalles.setItem(r, 1, QTableWidgetItem(str(nom)))
                self.tbl_detalles.setItem(r, 2, QTableWidgetItem(str(pre)))
                self.tbl_detalles.setItem(r, 3, QTableWidgetItem(str(est)))
                self.tbl_detalles.setItem(r, 4, QTableWidgetItem(str(aut)))
                self.tbl_detalles.setItem(r, 5, QTableWidgetItem(str(can)))
                self.tbl_detalles.setItem(r, 6, QTableWidgetItem(str(igr)))
                self.tbl_detalles.setItem(r, 7, QTableWidgetItem(str(ipa)))
                self.tbl_detalles.setItem(r, 8, QTableWidgetItem(str(des)))
        finally:
            self.tbl_detalles.setUpdatesEnabled(True)

    def _on_subir(self):
        if not self._recepcion_id:
            QMessageBox.warning(self, "Atención", "Seleccione la recepción.")
            return

        if not self._recetas_por_ref:
            QMessageBox.warning(self, "Atención", "Primero cargá el CSV (botón Cargar).")
            return

        total = len(self._recetas_por_ref)
        resp = QMessageBox.question(
            self,
            "Confirmar",
            f"Vas a subir {total} recetas a la base.\n"
            "Esto puede demorar.\n\n"
            "¿Querés continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        self.btn_subir.setEnabled(False)
        self.btn_cargar.setEnabled(False)

        self.run_job(
            self._uc.subir,
            recepcion_id=self._recepcion_id,
            recetas_por_ref=self._recetas_por_ref,
            detalles_por_ref=self._detalles_por_ref,
            title="Subiendo recetas…",
            on_result=self._show_subir_result,
            on_error=self._on_subir_error,
            on_finished=self._enable_subir_controls,
        )

    def _on_subir_error(self, err: str) -> None:
        msg = str(err)

        if "uq_archivo_detalle_archivo_cod_medic" in msg or "UniqueViolation" in msg:
            QMessageBox.warning(
                self,
                "CSV inválido",
                "El archivo IMED contiene medicamentos duplicados para la misma receta.\n\n"
                "Debe descargarse nuevamente."
            )
            return

        QMessageBox.critical(self, "Error", msg)

    def _show_subir_result(self, out: SubirOut) -> None:
        resumen = (
            f"Listo.\n\n"
            f"Insertadas: {out.inserted}\n"
            f"Salteadas (ya existían): {out.skipped}\n"
            f"Con error: {out.failed}"
        )

        if out.errores:
            top = "\n".join(out.errores[:15])
            if len(out.errores) > 15:
                top += f"\n... y {len(out.errores) - 15} más"
            resumen += f"\n\nErrores:\n{top}"

        QMessageBox.information(self, "Subida finalizada", resumen)

    def _on_dias_descargados(self) -> None:
        if not self._recepcion_id:
            QMessageBox.warning(self, "Atención", "Primero seleccioná una recepción.")
            return

        # Cargamos fechas (rápido) y abrimos calendario
        with session_scope() as s:
            fechas = ArchivoService.list_fechas(s, recepcion_id=self._recepcion_id)

        dlg = DiasDescargadosDialog(
            recepcion_id=self._recepcion_id,
            fechas_descargadas=fechas,
            parent=self
        )

        def on_pick(d: date):
            self.de_fecha.setDate(QDate(d.year, d.month, d.day))

        dlg.dateSelected.connect(on_pick)
        dlg.exec()



