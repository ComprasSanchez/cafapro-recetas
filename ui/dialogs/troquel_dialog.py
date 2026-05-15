from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QSpinBox, QPushButton, QMessageBox
)

from ui.usecase.auditoria_visual_usecase import AuditoriaVisualUseCase


@dataclass(frozen=True)
class TroquelDialogResult:
    created_or_updated: bool
    troquel_id: Optional[int] = None


class TroquelDialog(QDialog):
    def __init__(
        self,
        *,
        mode: str,  # "create" | "update"
        asociacion_id: Optional[int] = None,
        troquel_id: Optional[int] = None,
        codigo_barra: str = "",
        cantidad: int = 0,
        parent=None,
    ):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._mode = (mode or "").strip().lower()
        self._asociacion_id = int(asociacion_id) if asociacion_id is not None else None
        self._troquel_id = int(troquel_id) if troquel_id is not None else None

        if self._mode not in ("create", "update"):
            raise ValueError("TroquelDialog: mode debe ser 'create' o 'update'")

        if self._mode == "create" and not self._asociacion_id:
            raise ValueError("TroquelDialog: asociacion_id requerido en create")

        if self._mode == "update" and not self._troquel_id:
            raise ValueError("TroquelDialog: troquel_id requerido en update")

        self._result = TroquelDialogResult(created_or_updated=False, troquel_id=None)

        self.setWindowTitle("Agregar troquel" if self._mode == "create" else "Editar cantidad")

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        self.in_codigo = QLineEdit((codigo_barra or "").strip())
        self.in_codigo.setPlaceholderText("EAN13 / código de barra")
        self.in_codigo.setMinimumHeight(28)

        self.in_cantidad = QSpinBox()
        self.in_cantidad.setMinimum(0)
        self.in_cantidad.setMaximum(999)
        self.in_cantidad.setValue(max(0, int(cantidad or 1)))
        self.in_cantidad.setMinimumHeight(28)

        form.addRow(QLabel("Código barra:"), self.in_codigo)
        form.addRow(QLabel("Cantidad:"), self.in_cantidad)

        root.addLayout(form)

        # En update: no dejamos editar código
        if self._mode == "update":
            self.in_codigo.setReadOnly(True)

        # Acciones
        actions = QHBoxLayout()
        actions.addStretch(1)

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setProperty("variant", "ghost")
        self.btn_cancel.setProperty("size", "md")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_ok = QPushButton("Guardar")
        self.btn_ok.setProperty("variant", "primary")
        self.btn_ok.setProperty("size", "md")
        self.btn_ok.clicked.connect(self._on_ok)

        actions.addWidget(self.btn_cancel, 0)
        actions.addWidget(self.btn_ok, 0)

        root.addLayout(actions)

    def result_data(self) -> TroquelDialogResult:
        return self._result

    # -------------------------
    # Handlers
    # -------------------------
    def _on_ok(self) -> None:
        codigo = (self.in_codigo.text() or "").strip()
        qty = int(self.in_cantidad.value())

        if not codigo:
            QMessageBox.warning(self, "Falta dato", "Tenés que ingresar un código de barra.")
            return

        if qty == 0:
            QMessageBox.warning(
                self,
                "Cantidad inválida",
                "La cantidad no puede ser cero."
            )
            return

        try:
            if self._mode == "create":
                asociacion_id = self._asociacion_id
                if asociacion_id is None:
                    raise ValueError("No se pudo determinar la asociación.")

                troquel_id = AuditoriaVisualUseCase.create_troquel(
                    asociacion_id=int(asociacion_id),
                    codigo_barra=codigo,
                    cantidad=qty,
                )
                self._result = TroquelDialogResult(created_or_updated=True, troquel_id=troquel_id)
            else:
                troquel_id = self._troquel_id
                if troquel_id is None:
                    raise ValueError("No se pudo determinar el troquel.")

                AuditoriaVisualUseCase.update_troquel(
                    troquel_id=int(troquel_id),
                    cantidad=qty,
                )
                self._result = TroquelDialogResult(created_or_updated=True, troquel_id=int(troquel_id))

            self.accept()

        except Exception as e:
            QMessageBox.warning(self, "No se pudo guardar", str(e))
