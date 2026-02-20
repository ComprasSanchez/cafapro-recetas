from __future__ import annotations

from PySide6.QtCore import Qt, QSignalBlocker
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton, QMessageBox,
    QTableWidget, QTableWidgetItem, QAbstractItemView,
    QHeaderView, QFrame, QSizePolicy, QWidget
)

from app.db.session import session_scope
from app.service.recetas.estado_seguimiento_service import EstadoSeguimientoService
from app.service.recetas.recetas_service import RecetaService
from app.service.debitos.view_debitos import ViewDebitos
from ui.dialogs.recepcion_pick_dialog import RecepcionPickDialog


class ListadoDebitosWindow(QDialog):
    ROW_H = 38
    COMBO_H = 28

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Débitos por recepción")
        self.setMinimumSize(1100, 650)
        self.setModal(True)

        self._estados: list[tuple[int, str]] = []
        self._recepcion_id: int | None = None

        self._build_ui()
        self._load_estados()

        # estado inicial
        self._set_empty_state()

    # ---------------- UI ----------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # -------------------------
        # Header / Filters (card)
        # -------------------------
        header_card = QFrame()
        header_card.setObjectName("card")
        hc = QHBoxLayout(header_card)
        hc.setContentsMargins(12, 10, 12, 10)
        hc.setSpacing(10)

        self.lb_recepcion = QLabel("Recepción: —")
        self.lb_recepcion.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        hc.addWidget(self.lb_recepcion, 1)

        self.btn_pick = QPushButton("Elegir recepción…")
        self.btn_pick.setMinimumHeight(32)
        self.btn_pick.clicked.connect(self._pick_recepcion)
        hc.addWidget(self.btn_pick, 0)

        self.btn_reload = QPushButton("Refrescar")
        self.btn_reload.setProperty("variant", "primary")
        self.btn_reload.setMinimumHeight(32)
        self.btn_reload.setEnabled(False)
        self.btn_reload.clicked.connect(self._reload)
        hc.addWidget(self.btn_reload, 0)

        root.addWidget(header_card, 0)

        # -------------------------
        # Table (card)
        # -------------------------
        table_card = QFrame()
        table_card.setObjectName("card")
        tc = QVBoxLayout(table_card)
        tc.setContentsMargins(12, 12, 12, 12)
        tc.setSpacing(8)

        self.tbl = QTableWidget(0, 9)
        self.tbl.setHorizontalHeaderLabels([
            "N° Recepción",
            "Orden lote",
            "N° receta",
            "Creado en",
            "Importe OBS",
            "A cargo entidad",
            "Débito",
            "Estado seguimiento",
            "Detalle",
        ])

        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSortingEnabled(False)

        self.tbl.verticalHeader().setDefaultSectionSize(self.ROW_H)
        self.tbl.verticalHeader().setMinimumSectionSize(self.ROW_H)

        header = self.tbl.horizontalHeader()
        header.setStretchLastSection(True)

        # base
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        # columnas largas
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)      # Débito
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)      # Detalle
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Interactive)  # Estado
        self.tbl.setColumnWidth(7, 260)

        tc.addWidget(self.tbl, 1)
        root.addWidget(table_card, 1)

        # -------------------------
        # Footer
        # -------------------------
        footer = QHBoxLayout()
        footer.addStretch(1)

        btn_close = QPushButton("Cerrar")
        btn_close.setProperty("variant", "ghost")
        btn_close.setMinimumHeight(32)
        btn_close.clicked.connect(self.close)

        footer.addWidget(btn_close)
        root.addLayout(footer)

    # ---------------- data loaders ----------------
    def _load_estados(self) -> None:
        with session_scope() as s:
            rows = EstadoSeguimientoService.list(s)
        self._estados = [(int(r.estado_seguimiento_id), str(r.descripcion)) for r in rows]

    # ---------------- recepción (patrón Excluidos) ----------------
    def _pick_recepcion(self) -> None:
        dlg = RecepcionPickDialog(self, all=False)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        rid, numero= dlg.selected()
        if not rid:
            return

        self._recepcion_id = int(rid)
        self.lb_recepcion.setText(f"Recepción: {numero}")
        self.btn_reload.setEnabled(True)
        self._reload()

    def _set_empty_state(self) -> None:
        self.tbl.setRowCount(0)
        self.lb_recepcion.setText("Recepción: —")
        self.btn_reload.setEnabled(bool(self._recepcion_id))

    # ---------------- render ----------------
    def _reload(self) -> None:
        if not self._recepcion_id:
            self._set_empty_state()
            return

        try:
            rows = ViewDebitos.list_debitos(
                recepcion_id=int(self._recepcion_id),
                fecha_auditoria=None,  # ✅ sin filtro de fecha por ahora
            )
            self._render(rows)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar los débitos.\n\n{e}")

    def _render(self, rows) -> None:
        self.tbl.setRowCount(len(rows))

        for i, r in enumerate(rows):
            self.tbl.setRowHeight(i, self.ROW_H)

            self._set_item(i, 0, str(getattr(r, "recepcion_numero", "") or ""))
            self._set_item(i, 1, str(getattr(r, "orden_lote", "") or ""))
            self._set_item(i, 2, str(getattr(r, "nro_receta", "") or ""))

            creado_en = getattr(r, "creado_en", None)
            if creado_en:
                try:
                    creado_txt = creado_en.strftime("%d/%m/%Y")
                except Exception:
                    creado_txt = str(creado_en)
            else:
                creado_txt = ""
            self._set_item(i, 3, creado_txt)

            self._set_item(i, 4, self._fmt_money(getattr(r, "importe_obs", None)))
            self._set_item(i, 5, self._fmt_money(getattr(r, "a_cargo_entidad", None)))
            self._set_item(i, 6, str(getattr(r, "descripcion_debito", "") or ""))

            # 7 Estado seguimiento (Combo)
            receta_id = int(getattr(r, "receta_id", 0) or 0)

            cb = QComboBox()
            cb.setMinimumHeight(self.COMBO_H)
            cb.setMaximumHeight(self.COMBO_H)
            cb.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            cb.setProperty("receta_id", receta_id)

            with QSignalBlocker(cb):
                cb.clear()
                for estado_id, desc in self._estados:
                    cb.addItem(desc, estado_id)

                cur = getattr(r, "estado_seguimiento_id", None)
                if cur is not None:
                    idx = cb.findData(int(cur))
                    if idx >= 0:
                        cb.setCurrentIndex(idx)

            cb.setToolTip(cb.currentText())
            cb.currentTextChanged.connect(cb.setToolTip)
            cb.currentIndexChanged.connect(self._on_estado_changed)

            cell = QWidget()
            cell.setMinimumHeight(self.ROW_H)
            cell_l = QHBoxLayout(cell)
            cell_l.setContentsMargins(8, 4, 8, 4)
            cell_l.setSpacing(0)
            cell_l.addWidget(cb, 1)

            self.tbl.setCellWidget(i, 7, cell)

            self._set_item(i, 8, str(getattr(r, "detalle", "") or ""))

    def _on_estado_changed(self) -> None:
        cb = self.sender()
        if not isinstance(cb, QComboBox):
            return

        receta_id = cb.property("receta_id")
        new_estado_id = cb.currentData()

        if not receta_id:
            return

        try:
            RecetaService.update_estado_seguimiento(
                int(receta_id),
                int(new_estado_id) if new_estado_id is not None else None
            )
            self._reload()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo actualizar el estado.\n\n{e}")
            self._reload()

    # ---------------- utils ----------------
    def _set_item(self, row: int, col: int, text: str) -> None:
        it = QTableWidgetItem(text)
        it.setFlags(it.flags() & ~Qt.ItemIsEditable)
        self.tbl.setItem(row, col, it)

    @staticmethod
    def _fmt_money(v) -> str:
        if v is None:
            return "0,00"
        try:
            return f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            return str(v)
