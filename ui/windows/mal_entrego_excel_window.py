from __future__ import annotations

from datetime import date
from pathlib import Path
import re
import unicodedata

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QVBoxLayout,
)

from ui.usecase.catalogos_windows_usecase import CatalogosWindowsUseCase
from ui.usecase.mal_entrego_excel_usecase import ExportMalEntregoExcelIn, MalEntregoExcelUseCase
from ui.utils.worker import Worker


MESES = [
    (1, "Enero"),
    (2, "Febrero"),
    (3, "Marzo"),
    (4, "Abril"),
    (5, "Mayo"),
    (6, "Junio"),
    (7, "Julio"),
    (8, "Agosto"),
    (9, "Septiembre"),
    (10, "Octubre"),
    (11, "Noviembre"),
    (12, "Diciembre"),
]


class MalEntregoExcelWindow(QDialog):
    _MESES_MAYUS = {
        1: "ENERO",
        2: "FEBRERO",
        3: "MARZO",
        4: "ABRIL",
        5: "MAYO",
        6: "JUNIO",
        7: "JULIO",
        8: "AGOSTO",
        9: "SEPTIEMBRE",
        10: "OCTUBRE",
        11: "NOVIEMBRE",
        12: "DICIEMBRE",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bajar Mal Entregado General")
        self.setMinimumSize(920, 290)

        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        self._progress: QProgressDialog | None = None
        self._worker: Worker | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        card = QFrame()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(12, 10, 12, 10)
        cl.setSpacing(10)

        self.cb_obra_social = QComboBox()
        self.cb_obra_social.setMinimumWidth(320)
        self.cb_obra_social.setMinimumHeight(30)

        self.cb_anio = QComboBox()
        self.cb_anio.setMinimumWidth(110)
        self.cb_anio.setMinimumHeight(30)

        self.cb_mes = QComboBox()
        self.cb_mes.setMinimumWidth(160)
        self.cb_mes.setMinimumHeight(30)
        for mes_num, mes_nombre in MESES:
            self.cb_mes.addItem(mes_nombre, mes_num)
        self.cb_mes.setCurrentIndex(max(0, min(11, date.today().month - 1)))

        row_filters = QHBoxLayout()
        row_filters.setSpacing(8)
        row_filters.addWidget(QLabel("Obra social"))
        row_filters.addWidget(self.cb_obra_social)
        row_filters.addWidget(QLabel("Año"))
        row_filters.addWidget(self.cb_anio)
        row_filters.addWidget(QLabel("Mes"))
        row_filters.addWidget(self.cb_mes)
        row_filters.addStretch(1)
        cl.addLayout(row_filters)

        self.in_folder = QLineEdit()
        self.in_folder.setReadOnly(True)
        self.in_folder.setPlaceholderText("Seleccioná carpeta destino...")
        self.in_folder.setMinimumHeight(30)
        self.in_folder.setText(str((Path.home() / "Documents").resolve()))

        self.btn_pick_folder = QPushButton("Elegir carpeta...")
        self.btn_pick_folder.setProperty("variant", "ghost")
        self.btn_pick_folder.setMinimumHeight(32)
        self.btn_pick_folder.clicked.connect(self._pick_folder)

        row_folder = QHBoxLayout()
        row_folder.setSpacing(8)
        row_folder.addWidget(QLabel("Destino"))
        row_folder.addWidget(self.in_folder, 1)
        row_folder.addWidget(self.btn_pick_folder)
        cl.addLayout(row_folder)

        self.in_filename = QLineEdit()
        self.in_filename.setReadOnly(True)
        self.in_filename.setMinimumHeight(30)

        row_file = QHBoxLayout()
        row_file.setSpacing(8)
        row_file.addWidget(QLabel("Archivo"))
        row_file.addWidget(self.in_filename, 1)
        cl.addLayout(row_file)

        self.btn_export = QPushButton("Generar Excel")
        self.btn_export.setProperty("variant", "primary")
        self.btn_export.setMinimumHeight(32)
        self.btn_export.clicked.connect(self._on_export)

        btn_close = QPushButton("Cerrar")
        btn_close.setProperty("variant", "ghost")
        btn_close.setMinimumHeight(32)
        btn_close.clicked.connect(self.close)

        row_actions = QHBoxLayout()
        row_actions.setSpacing(8)
        row_actions.addStretch(1)
        row_actions.addWidget(self.btn_export)
        row_actions.addWidget(btn_close)
        cl.addLayout(row_actions)

        root.addWidget(card)

        self.cb_obra_social.currentIndexChanged.connect(self._refresh_filename_preview)
        self.cb_anio.currentIndexChanged.connect(self._refresh_filename_preview)
        self.cb_mes.currentIndexChanged.connect(self._refresh_filename_preview)

        self._load_catalogs()
        self._refresh_filename_preview()

    def _load_catalogs(self) -> None:
        try:
            obras = CatalogosWindowsUseCase.list_obras_sociales(solo_activas=False)
            periodos = CatalogosWindowsUseCase.list_periodos(solo_activos=False)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar catálogos:\n{e}")
            return

        self.cb_obra_social.clear()
        for os in obras:
            self.cb_obra_social.addItem(str(getattr(os, "nombre", "") or ""), int(os.obra_social_id))

        years = sorted({int(p.anio) for p in periodos}, reverse=True)
        if not years:
            years = [date.today().year]

        self.cb_anio.clear()
        for y in years:
            self.cb_anio.addItem(str(y), int(y))

        idx_year = self.cb_anio.findData(date.today().year)
        if idx_year >= 0:
            self.cb_anio.setCurrentIndex(idx_year)

        self._refresh_filename_preview()

    @staticmethod
    def _sanitize_filename_part(text: str) -> str:
        raw = str(text or "").strip()
        if not raw:
            return "OBRA_SOCIAL"

        raw = unicodedata.normalize("NFD", raw)
        raw = raw.encode("ascii", "ignore").decode("utf-8")
        raw = re.sub(r"[^A-Za-z0-9]+", "_", raw).strip("_")
        out = raw.upper()
        return out or "OBRA_SOCIAL"

    def _build_filename(self) -> str:
        obra_social = self._sanitize_filename_part(self.cb_obra_social.currentText())
        anio = int(self.cb_anio.currentData() or date.today().year)
        mes = int(self.cb_mes.currentData() or date.today().month)
        mes_txt = self._MESES_MAYUS.get(mes, f"MES_{mes:02d}")
        return f"MAL_ENTREGO_{obra_social}_{mes_txt}_{anio:04d}.xlsx"

    def _refresh_filename_preview(self) -> None:
        self.in_filename.setText(self._build_filename())

    def _pick_folder(self) -> None:
        current = self.in_folder.text().strip() or str(Path.home())
        folder = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar carpeta de destino",
            current,
        )
        if folder:
            self.in_folder.setText(folder)

    def _on_export(self) -> None:
        obra_social_id = self.cb_obra_social.currentData()
        obra_social_nombre = self.cb_obra_social.currentText().strip()
        anio = self.cb_anio.currentData()
        mes = self.cb_mes.currentData()

        if obra_social_id is None or anio is None or mes is None:
            QMessageBox.information(self, "Atención", "Seleccioná obra social, año y mes.")
            return

        folder = self.in_folder.text().strip()
        if not folder:
            self._pick_folder()
            folder = self.in_folder.text().strip()
        if not folder:
            return

        self.btn_export.setEnabled(False)
        self.btn_pick_folder.setEnabled(False)
        self._progress = QProgressDialog("Generando Excel...", "", 0, 0, self)
        self._progress.setWindowTitle("Exportación")
        self._progress.setCancelButton(None)
        self._progress.setMinimumDuration(0)
        self._progress.show()

        self._worker = Worker(
            MalEntregoExcelUseCase.run,
            data=ExportMalEntregoExcelIn(
                obra_social_id=int(obra_social_id),
                obra_social_nombre=obra_social_nombre,
                anio=int(anio),
                mes=int(mes),
                folder=folder,
            ),
        )
        self._worker.signals.finished.connect(self._on_export_finished)
        self._worker.signals.error.connect(self._on_export_error)
        self._pool.start(self._worker)

    def _on_export_finished(self, out) -> None:
        self._worker = None
        self.btn_export.setEnabled(True)
        self.btn_pick_folder.setEnabled(True)
        if self._progress is not None:
            self._progress.close()
            self._progress = None

        QMessageBox.information(
            self,
            "Exportación finalizada",
            f"Registros exportados: {int(getattr(out, 'total', 0) or 0)}\n\nArchivo:\n{getattr(out, 'file_path', '')}",
        )

    def _on_export_error(self, err: str) -> None:
        self._worker = None
        self.btn_export.setEnabled(True)
        self.btn_pick_folder.setEnabled(True)
        if self._progress is not None:
            self._progress.close()
            self._progress = None

        QMessageBox.critical(self, "Error", err)
