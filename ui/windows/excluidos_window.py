from __future__ import annotations

from decimal import Decimal

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView, QFrame
)

from ui.dialogs.recepcion_pick_dialog import RecepcionPickDialog
from ui.usecase.recepciones_windows_usecase import RecepcionesWindowsUseCase
from ui.utils.worker import Worker


class ExcluidosWindow(QDialog):
    def __init__(
        self,
        parent=None,
        recepcion_id: int | None = None,
        recepcion_numero: str | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Archivos Excluidos")
        self.setMinimumSize(950, 520)

        self._recepcion_id: int | None = int(recepcion_id) if recepcion_id is not None else None
        self._recepcion_numero = str(recepcion_numero or "").strip()
        self._recepcion_fija = recepcion_id is not None
        self._validador = "imed"
        self._rows_cache: list = []
        self._has_debitos_sin_estado = False
        self._sync_running = False
        self._worker: Worker | None = None
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ===== Header (card) =====
        header_card = QFrame()
        header_card.setObjectName("card")
        head = QHBoxLayout(header_card)
        head.setContentsMargins(16, 12, 16, 12)
        head.setSpacing(10)

        self.lb_recepcion = QLabel("Recepción: —")
        self.lb_recepcion.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        head.addWidget(self.lb_recepcion, 1)

        self.btn_pick = QPushButton("Elegir recepción…")
        self.btn_pick.clicked.connect(self._pick_recepcion)
        head.addWidget(self.btn_pick, 0)

        self.btn_reload = QPushButton("Refrescar")
        self.btn_reload.setEnabled(False)
        self.btn_reload.clicked.connect(self._load)
        head.addWidget(self.btn_reload, 0)

        root.addWidget(header_card)

        # ===== Warning label (NOT in a card) =====
        self.lb_estado_warning = QLabel("")
        self.lb_estado_warning.setWordWrap(True)
        self.lb_estado_warning.setProperty("role", "error")
        self.lb_estado_warning.setVisible(False)
        root.addWidget(self.lb_estado_warning, 0)

        # ===== Table (card) =====
        table_card = QFrame()
        table_card.setObjectName("card")
        tl = QVBoxLayout(table_card)
        tl.setContentsMargins(12, 12, 12, 12)
        tl.setSpacing(0)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Referencia", "Receta", "Fecha", "Hora", "Total", "A cargo obs"
        ])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        hh.setStretchLastSection(True)
        hh.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

        tl.addWidget(self.table)
        root.addWidget(table_card, 1)

        # ===== Actions (card) =====
        actions_card = QFrame()
        actions_card.setObjectName("card")
        actions = QHBoxLayout(actions_card)
        actions.setContentsMargins(12, 8, 12, 8)
        actions.setSpacing(8)

        self.btn_copy = QPushButton("Copiar tabla")
        self.btn_copy.setEnabled(False)
        self.btn_copy.clicked.connect(self._copy_table_to_clipboard)
        actions.addWidget(self.btn_copy)

        self.btn_excluir_todos = QPushButton("Excluir todo (E)")
        self.btn_excluir_todos.setEnabled(False)
        self.btn_excluir_todos.setVisible(False)
        self.btn_excluir_todos.clicked.connect(self._on_excluir_todos)
        actions.addWidget(self.btn_excluir_todos)

        self.btn_incluir_todos = QPushButton("Incluir todo (I)")
        self.btn_incluir_todos.setEnabled(False)
        self.btn_incluir_todos.setVisible(False)
        self.btn_incluir_todos.clicked.connect(self._on_incluir_todos)
        actions.addWidget(self.btn_incluir_todos)

        actions.addStretch(1)

        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.reject)
        actions.addWidget(btn_close)

        root.addWidget(actions_card)

        if self._recepcion_id:
            self._set_recepcion_label(self._recepcion_numero or str(self._recepcion_id))
            self.btn_reload.setEnabled(True)

            if self._recepcion_fija:
                self.btn_pick.setVisible(False)
                self.btn_pick.setEnabled(False)

            self._load()

    def _pick_recepcion(self) -> None:
        dlg = RecepcionPickDialog(self, show_closed=False, enable_filter=False)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        selected = dlg.selected()
        if not selected:
            return

        rid = selected[0] if len(selected) > 0 else None
        numero = selected[1] if len(selected) > 1 else ""
        if not rid:
            return

        self._recepcion_id = int(rid)
        self._set_recepcion_label(numero)
        self.btn_reload.setEnabled(True)

        self._load()

    def _set_recepcion_label(self, numero: str) -> None:
        value = str(numero or "").strip()
        self.lb_recepcion.setText(f"Recepción: {value or '—'}")

    def _load(self) -> None:
        if not self._recepcion_id:
            return

        try:
            ctx = RecepcionesWindowsUseCase.get_recepcion_integracion_context(
                recepcion_id=self._recepcion_id,
            )
            self._validador = str(getattr(ctx, "validador", "imed") or "imed").strip().lower()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar contexto de recepción:\n{e}")
            return

        try:
            self._has_debitos_sin_estado = RecepcionesWindowsUseCase.has_debitos_sin_estado_by_recepcion(
                recepcion_id=int(self._recepcion_id),
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo validar estados de seguimiento:\n{e}")
            return

        try:
            rows = RecepcionesWindowsUseCase.list_excluidos_by_recepcion(
                recepcion_id=self._recepcion_id,
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar excluidos:\n{e}")
            return

        self._rows_cache = list(rows)

        self.table.setRowCount(0)

        for r in rows:
            i = self.table.rowCount()
            self.table.insertRow(i)

            self._set(i, 0, str(getattr(r, "nro_referencia", "") or ""))
            self._set(i, 1, str(getattr(r, "nro_receta", "") or ""))
            self._set(i, 2, str(getattr(r, "fecha", "") or ""))
            self._set(i, 3, str(getattr(r, "hora", "") or ""))

            imp_bruto = Decimal(str(getattr(r, "importe_bruto", 0) or 0))
            imp_cobertura = Decimal(str(getattr(r, "importe_cobertura", 0) or 0))

            self._set(i, 4, self._fmt_ar(imp_bruto), align_center=True)
            self._set(i, 5, self._fmt_ar(imp_cobertura), align_center=True)

        self._refresh_validators_actions()

    def _refresh_validators_actions(self) -> None:
        enabled_for_os = self._validador == "preserfar"
        has_refs = bool(self._collect_referencias())
        blocked_by_estado = self._has_debitos_sin_estado
        has_rows = self.table.rowCount() > 0

        can_run = enabled_for_os and has_refs and not self._sync_running and not blocked_by_estado
        can_copy = has_rows and not self._sync_running and not blocked_by_estado

        self.btn_excluir_todos.setVisible(enabled_for_os)
        self.btn_incluir_todos.setVisible(enabled_for_os)
        self.btn_excluir_todos.setEnabled(can_run)
        self.btn_incluir_todos.setEnabled(can_run)
        self.btn_copy.setEnabled(can_copy)

        if blocked_by_estado:
            self.lb_estado_warning.setText(
                "Hay débitos sin estado de seguimiento en esta recepción. "
                "Resolvelos en Débitos antes de usar Excluidos."
            )
            self.lb_estado_warning.setVisible(True)
        else:
            self.lb_estado_warning.setVisible(False)
            self.lb_estado_warning.setText("")

    def _collect_referencias(self) -> list[str]:
        refs: list[str] = []
        seen: set[str] = set()

        for row in self._rows_cache:
            ref = str(getattr(row, "nro_referencia", "") or "").strip()
            if not ref or ref in seen:
                continue
            seen.add(ref)
            refs.append(ref)

        return refs

    def _on_excluir_todos(self) -> None:
        self._run_sync_validadores("E")

    def _on_incluir_todos(self) -> None:
        self._run_sync_validadores("I")

    def _run_sync_validadores(self, accion: str) -> None:
        if not self._recepcion_id:
            return
        if self._has_debitos_sin_estado:
            QMessageBox.warning(
                self,
                "Acción bloqueada",
                "Hay débitos sin estado de seguimiento en esta recepción. "
                "Resolvelos en Débitos antes de usar Excluidos.",
            )
            return
        if self._validador != "preserfar":
            QMessageBox.information(
                self,
                "Acción no disponible",
                "Esta acción solo aplica para obras sociales con validador 'preserfar'.",
            )
            return

        referencias = self._collect_referencias()
        if not referencias:
            QMessageBox.information(self, "Sin datos", "No hay referencias para enviar.")
            return

        verbo = "excluir" if accion == "E" else "incluir"
        reply = QMessageBox.question(
            self,
            "Confirmar",
            (
                f"Se enviarán {len(referencias)} referencias para {verbo} en Validators API.\n\n"
                "¿Desea continuar?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._sync_running = True
        self._refresh_validators_actions()

        self._worker = Worker(
            self._sync_validadores,
            accion=accion,
            referencias=referencias,
        )
        self._worker.signals.finished.connect(self._on_sync_validadores_ok)
        self._worker.signals.error.connect(self._on_sync_validadores_error)
        self._pool.start(self._worker)

    def _sync_validadores(self, *, accion: str, referencias: list[str]):
        if self._recepcion_id is None:
            raise ValueError("No hay recepción seleccionada.")

        return RecepcionesWindowsUseCase.incluir_excluir_recetas_en_validador(
            recepcion_id=int(self._recepcion_id),
            accion=accion,
            referencias=referencias,
        )

    def _on_sync_validadores_ok(self, out) -> None:
        self._sync_running = False
        self._worker = None
        self._refresh_validators_actions()

        accion = str(getattr(out, "accion", "") or "").upper()
        enviadas = int(getattr(out, "referencias_enviadas", 0) or 0)
        verbo = "excluidas" if accion == "E" else "incluidas"
        QMessageBox.information(
            self,
            "Operación completada",
            f"Se enviaron {enviadas} referencias ({verbo}) al validador.",
        )
        self._load()

    def _on_sync_validadores_error(self, err: str) -> None:
        self._sync_running = False
        self._worker = None
        self._refresh_validators_actions()
        QMessageBox.critical(self, "Error", f"No se pudo sincronizar con el validador:\n{err}")

    def _copy_table_to_clipboard(self) -> None:
        if self._has_debitos_sin_estado:
            QMessageBox.warning(
                self,
                "Acción bloqueada",
                "Hay débitos sin estado de seguimiento en esta recepción. "
                "Resolvelos en Débitos antes de usar Excluidos.",
            )
            return

        # Formato: TAB separated (ideal para pegar en Excel/Sheets)
        # Encabezados pedidos (sin "Etiqueta")
        headers = ["Nº Referencia", "Nº Receta", "Fecha", "Hora", "Total"]

        lines: list[str] = []
        lines.append("\t".join(headers))

        # Tomamos: ref(0) receta(1) fecha(2) hora(3) neto(4)
        for r in range(self.table.rowCount()):
            ref = self._item_text(r, 0)
            rec = self._item_text(r, 1)
            fecha = self._item_text(r, 2)
            hora = self._item_text(r, 3)
            neto = self._item_text(r, 4)
            lines.append("\t".join([ref, rec, fecha, hora, neto]))

        QGuiApplication.clipboard().setText("\n".join(lines))
        QMessageBox.information(self, "Copiado", "La tabla se copió al portapapeles.")

    def _item_text(self, row: int, col: int) -> str:
        it = self.table.item(row, col)
        return (it.text() if it else "").strip()

    @staticmethod
    def _fmt_ar(v: Decimal) -> str:
        # 69671,08 (coma decimal) como en tu ejemplo
        s = f"{Decimal(v):.2f}"
        return s.replace(".", ",")

    def _set(self, row: int, col: int, text: str, align_center: bool = False) -> None:
        it = QTableWidgetItem(text)
        it.setTextAlignment(
            (Qt.AlignmentFlag.AlignCenter if align_center else Qt.AlignmentFlag.AlignLeft)
            | Qt.AlignmentFlag.AlignVCenter
        )
        self.table.setItem(row, col, it)
