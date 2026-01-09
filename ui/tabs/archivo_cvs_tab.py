from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QLineEdit, QSizePolicy, QGridLayout,
    QTableWidgetItem, QTableWidget, QAbstractItemView, QSplitter, QHeaderView, QDateEdit
)

from app.db.session import session_scope
from app.service.archivo_service import ArchivoService
from app.service.recepcion_service import RecepcionService
from core.imed_cvs_handler import ImedCvsHandler
from ui.dialogs.recepcion_pick_dialog import RecepcionPickDialog


class ArchivoCvsTab(QWidget):
    def __init__(self, parent=None, creado_por_usuario_id: int | None = None):
        super().__init__(parent)
        self.creado_por_usuario_id = creado_por_usuario_id

        self._recepcion_id: int | None = None
        self._fecha: datetime | None = None

        self.imed: str | None = None
        self.obs: str | None = None

        self._cvs = ImedCvsHandler()

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

        self.btn_new_recepcion = QPushButton("+")
        self.btn_new_recepcion.setFixedSize(32, 26)

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

        grid.addWidget(self.de_fecha, 1, 9)

        grid.setColumnStretch(8, 1)
        grid.addWidget(right_box, 1, 10, Qt.AlignmentFlag.AlignRight)

        # señales
        self.btn_pick_recepcion.clicked.connect(self._on_pick_recepcion)

        self.btn_cargar.clicked.connect(self._on_cargar)
        self.btn_subir.clicked.connect(self._on_subir)

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
    # Recepción
    # --------------------------
    def _on_pick_recepcion(self):
        dlg = RecepcionPickDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        rid = dlg.selected_recepcion_id()
        if rid:
            self._load_recepcion(rid)

    def _load_recepcion(self, recepcion_id: int):
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
        self.in_prestador.setText(str(rec.prestador))
        self.in_obra.setText(str(rec.obra_social))

        self.obs = str(rec.obra_social)
        self.imed = str(rec.imed)
        self.in_imed.setText(self.imed)

        # al cambiar recepción: limpiar tablas / cache
        self._recetas_por_ref = {}
        self._detalles_por_ref = {}
        self._current_ref = None
        self._render_recetas()
        self._render_detalles(None)

    # --------------------------
    # CSV
    # --------------------------
    def _on_cargar(self) -> None:
        imed = self.in_imed.text().strip()
        fecha = self.de_fecha.date().toString("dd/MM/yyyy")  # coherente con el handler

        if not imed:
            QMessageBox.warning(self, "Atención", "Primero seleccioná una recepción (para tener IMED).")
            return

        try:
            recetas, detalles = self._cvs.read_cvs_by_imed_and_date(imed=imed, date=fecha)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self._recetas_por_ref = recetas or {}
        self._detalles_por_ref = detalles or {}
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

                # 0) Nro Referencia (y lo guardo en UserRole)
                it_ref = QTableWidgetItem(str(nro_ref))
                it_ref.setData(Qt.UserRole, str(nro_ref))
                self.tbl_recetas.setItem(r, 0, it_ref)

                # 1) Nro Receta
                nro_receta = receta.get("Nro_Receta") or receta.get("Nro Receta") or ""
                self.tbl_recetas.setItem(r, 1, QTableWidgetItem(str(nro_receta)))

                # 2) Beneficiario
                beneficiario = receta.get("Beneficiario") or ""
                self.tbl_recetas.setItem(r, 2, QTableWidgetItem(str(beneficiario)))

                # 3) Fecha
                fecha = receta.get("Fecha") or ""
                self.tbl_recetas.setItem(r, 3, QTableWidgetItem(str(fecha)))

                # 4) Hora
                hora = receta.get("Hora") or ""
                self.tbl_recetas.setItem(r, 4, QTableWidgetItem(str(hora)))

                # 5) Importe Gral
                imp_gral = receta.get("Importe_Gral") or receta.get("Importe Gral") or ""
                self.tbl_recetas.setItem(r, 5, QTableWidgetItem(str(imp_gral)))

                # 6) Importe Pami
                imp_pami = receta.get("Importe_Pami") or receta.get("Importe Pami") or ""
                self.tbl_recetas.setItem(r, 6, QTableWidgetItem(str(imp_pami)))

                # 7) A Cargo Entidad
                cargo = receta.get("A_Cargo_Entidad") or receta.get("A Cargo Entidad") or ""
                self.tbl_recetas.setItem(r, 7, QTableWidgetItem(str(cargo)))

                # 8) Orden Del Lote
                orden = receta.get("Orden_Del_Lote") or receta.get("Orden Del Lote") or ""
                self.tbl_recetas.setItem(r, 8, QTableWidgetItem(str(orden)))
        finally:
            self.tbl_recetas.setUpdatesEnabled(True)
            self.tbl_recetas.setSortingEnabled(True)

        self.tbl_recetas.resizeColumnsToContents()

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

                self.tbl_detalles.setItem(r, 0, QTableWidgetItem(cod))
                self.tbl_detalles.setItem(r, 1, QTableWidgetItem(nom))
                self.tbl_detalles.setItem(r, 2, QTableWidgetItem(pre))
                self.tbl_detalles.setItem(r, 3, QTableWidgetItem(est))
                self.tbl_detalles.setItem(r, 4, QTableWidgetItem(aut))
                self.tbl_detalles.setItem(r, 5, QTableWidgetItem(can))
                self.tbl_detalles.setItem(r, 6, QTableWidgetItem(igr))
                self.tbl_detalles.setItem(r, 7, QTableWidgetItem(ipa))
                self.tbl_detalles.setItem(r, 8, QTableWidgetItem(des))
        finally:
            self.tbl_detalles.setUpdatesEnabled(True)

    # --------------------------
    # DB (ArchivoService)
    # --------------------------
    def _on_subir(self):
        # 1) Validaciones
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

        # 2) Proceso masivo
        inserted = 0
        skipped = 0
        failed = 0
        errores: list[str] = []

        try:
            with session_scope() as s:
                # Tip: una transacción grande (más rápido). Si querés “por receta”, avisame.
                for nro_ref, receta in self._recetas_por_ref.items():
                    detalles = self._detalles_por_ref.get(nro_ref, [])

                    try:
                        ArchivoService.create_from_imed(
                            s,
                            receta=receta,
                            detalles=detalles,
                            recepcion_id=None,  # NULL
                            nro_referencia=nro_ref,  # clave del dict
                            skip_if_exists=True,
                            check_scope="ref",
                        )
                        inserted += 1

                    except ValueError as e:
                        # si tu service lanza ValueError por “Ya existe...”
                        msg = str(e)
                        if "Ya existe" in msg or "existe" in msg.lower():
                            skipped += 1
                        else:
                            failed += 1
                            errores.append(f"{nro_ref}: {msg}")

                    except Exception as e:
                        failed += 1
                        errores.append(f"{nro_ref}: {e}")

            # 3) Resultado
            resumen = (
                f"Listo.\n\n"
                f"Insertadas: {inserted}\n"
                f"Salteadas (ya existían): {skipped}\n"
                f"Con error: {failed}"
            )

            if errores:
                # mostramos solo las primeras para no romper el dialog
                top = "\n".join(errores[:15])
                if len(errores) > 15:
                    top += f"\n... y {len(errores) - 15} más"
                resumen += f"\n\nErrores:\n{top}"

            QMessageBox.information(self, "Subida finalizada", resumen)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo subir el lote:\n{e}")

