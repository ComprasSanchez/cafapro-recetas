from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QHeaderView,
    QMessageBox,
)

from ui.usecase.auditoria_usecase import AuditoriaUseCase


class ReasociarRecetaDialog(QDialog):

    MAX_ROWS = 20

    def __init__(
        self,
        recepcion_id: int,
        receta_id: int,
        parent=None,
    ):
        super().__init__(parent)

        self.recepcion_id = recepcion_id
        self.receta_id = receta_id

        self.setWindowTitle("Reasociar receta")
        self.resize(600, 420)

        self._all_rows = []

        self._build_ui()
        self._load()

    def _build_ui(self):

        layout = QVBoxLayout(self)

        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText(
            "Buscar por nro receta o referencia..."
        )
        self.txt_buscar.textChanged.connect(self._apply_filter)

        layout.addWidget(self.txt_buscar)

        self.tbl = QTableWidget(0, 3)

        self.tbl.setHorizontalHeaderLabels(
            [
                "Receta",
                "Referencia",
                "Lote",
            ]
        )

        hh = self.tbl.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.tbl)

        btn_layout = QHBoxLayout()

        self.btn_asociar = QPushButton("Reasociar")
        self.btn_asociar.clicked.connect(self._on_reasociar)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_asociar)

        layout.addLayout(btn_layout)

    def _load(self):

        rows = AuditoriaUseCase.load_archivos_reasociables(
            self.recepcion_id
        )

        self._all_rows = rows

        self._render(rows[: self.MAX_ROWS])

    def _apply_filter(self):

        txt = self.txt_buscar.text().strip().lower()

        if not txt:
            rows = self._all_rows[: self.MAX_ROWS]

        else:

            rows = [
                r
                for r in self._all_rows
                if txt in (r.numero_receta or "").lower()
                or txt in (r.numero_referencia or "").lower()
            ][: self.MAX_ROWS]

        self._render(rows)

    def _render(self, rows):

        self.tbl.setRowCount(len(rows))

        for i, r in enumerate(rows):

            it0 = QTableWidgetItem(str(r.numero_receta))
            it0.setData(256, r.archivo_id)

            self.tbl.setItem(i, 0, it0)
            self.tbl.setItem(i, 1, QTableWidgetItem(r.numero_referencia or ""))
            self.tbl.setItem(i, 2, QTableWidgetItem(str(r.nro_lote or "")))

    def _on_reasociar(self):

        row = self.tbl.currentRow()

        if row < 0:
            QMessageBox.warning(
                self,
                "Atención",
                "Seleccione un archivo.",
            )
            return

        archivo_id = self.tbl.item(row, 0).data(256)

        AuditoriaUseCase.reasociar(
            receta_id=self.receta_id,
            archivo_id=archivo_id,
        )

        self.accept()
