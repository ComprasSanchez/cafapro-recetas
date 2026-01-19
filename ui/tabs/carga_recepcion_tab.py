from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QHBoxLayout, QLabel, QPushButton,
    QDateEdit, QMessageBox, QLineEdit, QSizePolicy, QGridLayout,
    QTableWidgetItem, QTableWidget, QAbstractItemView
)

from app.db.session import session_scope
from app.service.recepcion_service import RecepcionService
from app.service.tif_service import ProcesarItemIn, TiffService
from core.image_handler import ImageHandler
from ui.dialogs.recepcion_create_dialog import RecepcionCreateDialog
from ui.dialogs.recepcion_pick_dialog import RecepcionPickDialog


class CargaRecepcionTab(QWidget):
    def __init__(self, parent=None, creado_por_usuario_id: int | None = 1):
        super().__init__(parent)
        self.creado_por_usuario_id = creado_por_usuario_id

        self._recepcion_id: int | None = None
        self._fecha: datetime | None = None

        self.imed: str | None = None
        self.obs: str | None = None

        self._img = ImageHandler(parent=self)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        root.addWidget(self._build_header(), 0)
        root.addWidget(self._build_table_card(), 1)

    # --------------------------
    # Helpers
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
    def _btn(text: str, *, variant: str = "ghost", size: str = "md", w: int | None = None, h: int | None = None) -> QPushButton:
        b = QPushButton(text)
        b.setProperty("variant", variant)
        b.setProperty("size", size)
        if w is not None:
            b.setFixedWidth(w)
        if h is not None:
            b.setMinimumHeight(h)
        return b

    # --------------------------
    # Header
    # --------------------------
    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("card")
        header.setMaximumHeight(98)

        grid = QGridLayout(header)
        grid.setContentsMargins(12, 10, 12, 10)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        # ===== Controles =====
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

        # Fecha
        self.de_fecha = QDateEdit()
        self.de_fecha.setCalendarPopup(True)
        self.de_fecha.setDate(QDate.currentDate())
        self.de_fecha.setDisplayFormat("dd/MM/yyyy")
        self.de_fecha.setMinimumHeight(28)
        self.de_fecha.setFixedWidth(120)

        # ===== Botones derecha =====
        self.btn_cargar = self._btn("Cargar", variant="ghost", size="md", w=90, h=32)
        self.btn_procesar = self._btn("Procesar", variant="primary", size="md", w=90, h=32)

        right_box = QWidget()
        right_l = QHBoxLayout(right_box)
        right_l.setContentsMargins(0, 0, 0, 0)
        right_l.setSpacing(8)
        right_l.addWidget(self.btn_cargar)
        right_l.addWidget(self.btn_procesar)

        # ===== Bloque compacto: N° + botones =====
        num_box = QWidget()
        num_l = QHBoxLayout(num_box)
        num_l.setContentsMargins(0, 0, 0, 0)
        num_l.setSpacing(6)

        num_l.addWidget(self.in_numero, 1)
        num_l.addWidget(self.btn_pick_recepcion, 0)
        num_l.addWidget(self.btn_new_recepcion, 0)

        # ===== Layout =====
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

        grid.addWidget(self.de_fecha, 1, 9)

        grid.setColumnStretch(8, 1)                 # empuja la derecha
        grid.addWidget(right_box, 1, 10, Qt.AlignmentFlag.AlignRight)

        # Signals
        self.btn_pick_recepcion.clicked.connect(self._on_pick_recepcion)
        self.btn_new_recepcion.clicked.connect(self._on_new_recepcion)
        self.btn_cargar.clicked.connect(self._on_cargar)
        self.btn_procesar.clicked.connect(self._on_procesar)

        return header

    # --------------------------
    # Tabla (card)
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

    def _build_table(self) -> QTableWidget:
        t = QTableWidget()
        t.setColumnCount(4)
        t.setHorizontalHeaderLabels(["Archivo", "Fecha", "Hora", "Ruta"])
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # Sin selección y sin focus visual
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
    # Recepción: cargar / mostrar
    # --------------------------
    def _on_pick_recepcion(self):
        dlg = RecepcionPickDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        rid = dlg.selected_recepcion_id()
        if not rid:
            return

        self._load_recepcion(rid)

    def _on_new_recepcion(self):
        dlg = RecepcionCreateDialog(self, creado_por_usuario_id=self.creado_por_usuario_id)
        if dlg.exec() == dlg.DialogCode.Accepted and dlg.created_recepcion_id:
            self._load_recepcion(dlg.created_recepcion_id)
            return

        QMessageBox.information(self, "OK", "Recepción creada. Ahora seleccionála con 'Elegir recepción…'.")

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

        self.in_numero.setText(f"{rec.numero}")
        self.in_prestador.setText(f"{rec.prestador}")
        self.in_obra.setText(f"{rec.obra_social}")

        self.obs = str(rec.obra_social)
        self.imed = str(rec.imed)

        periodo_txt = str(rec.periodo)
        self.in_periodo.setText(periodo_txt)

        quincena = "—"
        if "Q1" in periodo_txt:
            quincena = "1ª"
        elif "Q2" in periodo_txt:
            quincena = "2ª"
        self.in_quincena.setText(quincena)

        self._clear_images_table()

    # --------------------------
    # Acciones
    # --------------------------
    def _on_cargar(self) -> None:
        self._clear_images_table()

        if not self._recepcion_id:
            QMessageBox.warning(self, "Atención", "Primero seleccioná una recepción.")
            return
        if not self.imed or not self.obs:
            QMessageBox.warning(self, "Atención", "La recepción seleccionada no tiene IMED/Obra Social.")
            return

        qd = self.de_fecha.date()
        date_str = qd.toString("dd/MM/yyyy")

        try:
            rows = self._img.get_images_tif(name_folder=self.imed, date=date_str, obs=self.obs)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron listar imágenes:\n{e}")
            return

        if not rows:
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

    def _on_procesar(self) -> None:
        if not self._recepcion_id:
            QMessageBox.warning(self, "Atención", "Primero seleccioná una recepción.")
            return

        if self.tbl_imgs.rowCount() == 0:
            QMessageBox.warning(self, "Atención", "No hay imágenes cargadas para procesar.")
            return

        items: list[ProcesarItemIn] = []
        for r in range(self.tbl_imgs.rowCount()):
            file_name = self.tbl_imgs.item(r, 0).text().strip() if self.tbl_imgs.item(r, 0) else ""
            full_path = self.tbl_imgs.item(r, 3).text().strip() if self.tbl_imgs.item(r, 3) else ""
            if file_name and full_path:
                items.append(ProcesarItemIn(file_name=file_name, full_path=full_path))

        if not items:
            QMessageBox.warning(self, "Atención", "No hay rutas válidas para procesar.")
            return

        output_dir = f"output/recepciones/{self._recepcion_id}"

        try:
            svc = TiffService()
            with session_scope() as s:
                resumen = svc.procesar(
                    s=s,
                    recepcion_id=self._recepcion_id,
                    usuario_id=self.creado_por_usuario_id,
                    items=items,
                    output_dir=output_dir,
                )

            msg = (
                f"OK: {resumen.ok}\n"
                f"Sin match: {resumen.sin_match}\n"
                f"Duplicados (nro_referencia en múltiples Archivo): {resumen.duplicados}\n"
                f"Ya asociados: {resumen.ya_asociado}"
            )
            if resumen.errores:
                msg += "\n\nErrores:\n" + "\n".join(resumen.errores[:10])
                if len(resumen.errores) > 10:
                    msg += f"\n... y {len(resumen.errores) - 10} más"

            QMessageBox.information(self, "Procesar", msg)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo procesar:\n{e}")
