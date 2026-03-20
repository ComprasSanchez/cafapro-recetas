from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import unicodedata

from PySide6.QtCore import Qt, QSignalBlocker, QMarginsF, QThreadPool
from PySide6.QtGui import QTextDocument, QPageSize, QPageLayout, QPdfWriter
from PySide6.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton, QMessageBox,
    QTableWidget, QTableWidgetItem, QAbstractItemView,
    QHeaderView, QFrame, QSizePolicy, QWidget, QLineEdit, QFileDialog, QProgressDialog
)

from app.db.session import session_scope
from app.db.models import Periodo, Recepcion
from app.service.recetas.estado_seguimiento_service import EstadoSeguimientoService
from app.service.recetas.recetas_service import RecetaService
from app.service.debitos.view_debitos import ViewDebitos
from ui.dialogs.recepcion_pick_dialog import RecepcionPickDialog
from ui.usecase.download_wrong_debitos_usecase import DownloadDebitosUseCase, DownloadDebitosIn
from ui.utils.worker import Worker

class NoWheelComboBox(QComboBox):

    def wheelEvent(self, event):
        event.ignore()


class ListadoDebitosWindow(QDialog):
    ROW_H = 38
    COMBO_H = 28

    def __init__(
        self,
        parent=None,
        recepcion_id: int | None = None,
        recepcion_numero: str | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Débitos por recepción")
        self.setMinimumSize(1100, 650)
        self.setModal(True)

        self._estados: list[tuple[int, str]] = []
        self._recepcion_id: int | None = int(recepcion_id) if recepcion_id is not None else None
        self._recepcion_numero = str(recepcion_numero or "").strip()
        self._recepcion_fija = recepcion_id is not None

        self._all_rows = []
        self.filtrados = []
        self._wrong_rows_ctx = []
        self._wrong_folder_ctx: str | None = None

        self._build_ui()
        self._load_estados()

        if self._recepcion_id:
            self._set_recepcion_label(self._recepcion_numero or str(self._recepcion_id))
            self.btn_reload.setEnabled(True)

            if self._recepcion_fija:
                self.btn_pick.setVisible(False)
                self.btn_pick.setEnabled(False)

            self._reload()
            return

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

        # Campo fecha auditoría
        self.in_fecha = QLineEdit()
        self.in_fecha.setPlaceholderText("Fecha auditoría (dd/MM/yyyy)")
        self.in_fecha.setInputMask("00/00/0000")
        self.in_fecha.setMinimumHeight(32)
        hc.addWidget(self.in_fecha, 0)

        self.in_fecha.editingFinished.connect(self._apply_table_filter)

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
            "Fecha Auditoria",
            "Total",
            "A cargo OBS",
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

        self.btn_preview = QPushButton("Vista previa")
        self.btn_preview.setMinimumHeight(32)
        self.btn_preview.clicked.connect(self._print_filtered)

        self.btn_print = QPushButton("Imprimir todo")
        self.btn_print.setMinimumHeight(32)
        self.btn_print.clicked.connect(self._print_all)

        footer.addWidget(self.btn_preview)
        footer.addWidget(self.btn_print)

        btn_close = QPushButton("Cerrar")
        btn_close.setProperty("variant", "ghost")
        btn_close.setMinimumHeight(32)
        btn_close.clicked.connect(self.close)

        self.btn_download = QPushButton("Descargar + PDF Mal Entregados")
        self.btn_download.setMinimumHeight(32)
        self.btn_download.clicked.connect(self._download_wrong_debitos)

        footer.addWidget(self.btn_download)


        footer.addWidget(btn_close)
        root.addLayout(footer)

    # ---------------- data loaders ----------------
    def _load_estados(self) -> None:
        with session_scope() as s:
            rows = EstadoSeguimientoService.list(s)
        self._estados = [(int(r.estado_seguimiento_id), str(r.descripcion)) for r in rows]

    # ---------------- recepción (patrón Excluidos) ----------------
    def _pick_recepcion(self) -> None:
        dlg = RecepcionPickDialog(self, show_closed=False, enable_filter=True)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        rid, numero = dlg.selected()
        if not rid:
            return

        self._recepcion_id = int(rid)
        self._set_recepcion_label(numero)
        self.btn_reload.setEnabled(True)
        self._reload()

    def _set_recepcion_label(self, numero: str) -> None:
        value = str(numero or "").strip()
        self.lb_recepcion.setText(f"Recepción: {value or '—'}")

    def _set_empty_state(self) -> None:
        self.tbl.setRowCount(0)

        if self._recepcion_fija and self._recepcion_id:
            self._set_recepcion_label(self._recepcion_numero or str(self._recepcion_id))
            self.btn_reload.setEnabled(True)
            return

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
                fecha_auditoria=None,
            )

            self._all_rows = rows
            self.filtrados = rows
            self._render(rows)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar los débitos.\n\n{e}")

    def _render(self, rows) -> None:
        self.tbl.setRowCount(len(rows))

        for i, r in enumerate(rows):
            self.tbl.setRowHeight(i, self.ROW_H)

            self._set_item(i, 0, str(getattr(r, "recepcion_numero", "") or ""))
            self._set_item(i, 1, str(getattr(r, "orden_lote", "") or "-"))
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

            self._set_item(i, 4, self._fmt_money(getattr(r, "importe_bruto", "-")))
            self._set_item(i, 5, self._fmt_money(getattr(r, "importe_cobertura", "-")))
            self._set_item(i, 6, str(getattr(r, "descripcion_debito", "") or "-"))

            # 7 Estado seguimiento (Combo)
            receta_id = int(getattr(r, "receta_id", 0) or 0)

            cb = NoWheelComboBox()
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
            cell_l = QHBoxLayout(cell)
            cell_l.setContentsMargins(0, 0, 0, 0)
            cell_l.setSpacing(0)
            cb.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

            cell_l.addWidget(cb)

            self.tbl.setCellWidget(i, 7, cell)

            self._set_item(i, 8, str(getattr(r, "detalle", "") or ""))

    def _on_estado_changed(self) -> None:
        cb = self.sender()
        if not isinstance(cb, NoWheelComboBox):
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

    def _apply_table_filter(self) -> None:

        if not self._all_rows:
            self.filtrados = []
            self._render([])
            return

        fecha_txt = self.in_fecha.text().strip()
        fecha_limpia = fecha_txt.replace("/", "")

        if not fecha_limpia or len(fecha_limpia) != 8:
            self.filtrados = self._all_rows
            self._render(self._all_rows)
            return

        try:
            fecha_filtro = datetime.strptime(fecha_txt, "%d/%m/%Y").date()
        except ValueError:
            self.filtrados = self._all_rows
            self._render(self._all_rows)
            return

        self.filtrados = [
            r for r in self._all_rows
            if getattr(r, "creado_en", None)
               and r.creado_en.date() == fecha_filtro
        ]

        self._render(self.filtrados)

    def _generate_html(self, rows):
        ahora = datetime.now().strftime("%d/%m/%Y %H:%M")

        auditores = sorted(
            {r.auditor_nombre for r in rows if getattr(r, "auditor_nombre", None)}
        )

        auditores_txt = " - ".join(auditores) if auditores else ""

        periodo_texto = self.lb_recepcion.text()

        fecha_filtro = self.in_fecha.text().strip()

        fecha_auditoria_html = ""

        obs = ""

        if rows:
            obs = getattr(rows[0], "obs", "") or ""

        if fecha_filtro and len(fecha_filtro.replace("/", "")) == 8:
            fecha_auditoria_html = f"""
                <div class="fecha_auditoria">
                    Fecha Auditoría: {fecha_filtro}
                </div>
            """

        html = f"""
        <html>
        <head>
            <style>

                body {{
                    font-family: Arial;
                    font-size: 6pt;
                    margin: 0;
                    padding: 0;
                }}

                .container {{
                    width: 100%;
                    margin: 0;
                    padding: 0;
                }}

                .titulo {{
                    text-align: center;
                    font-size: 10pt;
                    font-weight: bold;
                    margin-bottom: 2px;
                }}

                .subtitulo {{
                    text-align: center;
                    font-size: 8pt;
                    margin-bottom: 4px;
                }}

                .auditores {{
                    text-align: center;
                    font-size: 8pt;
                    margin-bottom: 6px;
                }}
                
                .fecha_auditoria {{
                    text-align: center;
                    font-size: 6pt;
                    margin-bottom: 6px;
                }}

                .fecha {{
                    text-align: right;
                    font-size: 6pt;
                    margin-bottom: 6px;
                }}
                
                .obs {{
                    text-align: center;
                    font-size: 8pt;
                    margin-bottom: 4px;
                }}

                table {{
                    width: 100%;
                    border-collapse: collapse;
                    table-layout: fixed;  /* 🔥 clave para separar columnas */
                }}

                th {{
                    text-align: left;
                    font-weight: bold;
                    padding: 4px 6px;
                    border-bottom: 1px solid #000;
                }}

                td {{
                    padding: 4px 6px;
                    vertical-align: top;
                    word-wrap: break-word;
                }}

                .right {{
                    text-align: right;
                }}

            </style>
        </head>

        <body>

            <div class="container">

                <div class="titulo">
                    CAMARA DE FARMACEUTICA Y PROPIETARIOS DE FARMACIAS
                </div>

                <div class="subtitulo">
                    {periodo_texto}
                </div>
                
                <div class="obs">
                    Obra Social: {obs}
                </div>
                
                {fecha_auditoria_html}

                <div class="auditores">
                    Auditores: {auditores_txt}
                </div>

                <div class="fecha">
                    Generado: {ahora}
                </div>

                <table>

                    <!-- 🔥 Definimos ancho real de columnas -->
                    <colgroup>
                        <col style="width:18%">
                        <col style="width:8%">
                        <col style="width:10%">
                        <col style="width:10%">
                        <col style="width:10%">
                        <col style="width:18%">
                        <col style="width:12%">
                        <col style="width:7%">
                        <col style="width:7%">
                    </colgroup>

                    <tr>
                        <th>Farmacia</th>
                        <th>Lote</th>
                        <th>Receta</th>
                        <th class="right">Total</th>
                        <th class="right">A cargo OBS</th>
                        <th>Débito</th>
                        <th>Detalle</th>
                        <th>Estado</th>
                        <th>Vendedor</th>
                        <th>Fecha Auditoría</th>
                    </tr>
        """

        for r in rows:
            html += f"""
                    <tr>
                        <td>{r.prestador_nombre or ''}</td>
                        <td>{r.orden_lote or ''}</td>
                        <td>{r.nro_receta or ''}</td>
                        <td class="right">{r.importe_bruto or ''}</td>
                        <td class="right">{r.importe_cobertura or ''}</td>
                        <td>{r.descripcion_debito or ''}</td>
                        <td>{r.detalle or ''}</td>
                        <td>{r.estado_seguimiento or ''}</td>
                        <td>{r.vendedor_nombre or ''}</td>
                        <td>{r.creado_en.strftime("%d/%m/%Y") if r.creado_en else ''}</td>
                    </tr>
            """

        html += """
                </table>

            </div>

        </body>
        </html>
        """

        return html

    def _print_filtered(self):
        self._preview_rows(self.filtrados)

    def _print_all(self):
        self._print_rows(self._all_rows)

    def _preview_rows(self, rows):

        if not rows:
            QMessageBox.information(self, "Sin datos", "No hay datos para imprimir.")
            return

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setPageOrientation(QPageLayout.Orientation.Landscape)
        printer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)

        preview = QPrintPreviewDialog(printer, self)
        preview.paintRequested.connect(lambda p: self._render_print(p, rows))

        preview.exec()

    def _print_rows(self, rows):

        if not rows:
            QMessageBox.information(self, "Sin datos", "No hay datos para imprimir.")
            return

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setPageOrientation(QPageLayout.Orientation.Landscape)
        printer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)

        dlg = QPrintDialog(printer, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        self._render_print(printer, rows)

    def _render_print(self, printer, rows):

        html = self._generate_html(rows)

        doc = QTextDocument()
        doc.setDocumentMargin(0)

        page_rect = printer.pageLayout().paintRect(QPageLayout.Unit.Point)
        doc.setPageSize(page_rect.size())

        doc.setHtml(html)
        doc.print_(printer)

    def _download_wrong_debitos(self):
        rows = self._get_wrong_rows()

        if not rows:
            QMessageBox.information(
                self,
                "Sin datos",
                "No hay débitos mal entregados."
            )
            return

        folder = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar carpeta"
        )

        if not folder:
            return

        self._wrong_rows_ctx = list(rows)
        self._wrong_folder_ctx = folder

        self.progress = QProgressDialog(
            "Descargando imágenes...",
            None,
            0,
            0,
            self
        )

        self.progress.show()

        worker = Worker(
            DownloadDebitosUseCase.run,
            data=DownloadDebitosIn(
                rows=rows,
                folder=folder
            )
        )

        worker.signals.finished.connect(self._download_finished)
        worker.signals.error.connect(self._download_error)

        QThreadPool.globalInstance().start(worker)

    def _download_finished(self, out):

        self.progress.close()

        pdf_path = None
        pdf_error = None

        try:
            if self._wrong_rows_ctx and self._wrong_folder_ctx:
                pdf_path = self._export_wrong_pdf(self._wrong_rows_ctx, self._wrong_folder_ctx)
        except Exception as e:
            pdf_error = str(e)

        msg = f"Imágenes descargadas: {out.total}"
        if pdf_path:
            msg += f"\nPDF generado:\n{pdf_path}"

        if pdf_error:
            msg += f"\n\nNo se pudo generar el PDF:\n{pdf_error}"

        QMessageBox.information(
            self,
            "Mal entregados",
            msg,
        )

        self._wrong_rows_ctx = []
        self._wrong_folder_ctx = None

    def _download_error(self, err):

        self.progress.close()

        self._wrong_rows_ctx = []
        self._wrong_folder_ctx = None

        QMessageBox.critical(
            self,
            "Error",
            err
        )

    def _get_wrong_rows(self):
        return [
            r for r in self._all_rows
            if getattr(r, "motivo_debito_id", None) == 9
        ]

    def _export_wrong_pdf(self, rows, folder: str) -> str:
        filename = self._wrong_pdf_filename(rows)
        output_path = Path(folder) / filename

        pdf = QPdfWriter(str(output_path))
        pdf.setResolution(300)
        pdf.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        pdf.setPageOrientation(QPageLayout.Orientation.Landscape)
        pdf.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)

        html = self._generate_html(rows)
        doc = QTextDocument()
        doc.setDocumentMargin(0)

        page_rect = pdf.pageLayout().paintRect(QPageLayout.Unit.Point)
        doc.setPageSize(page_rect.size())
        doc.setHtml(html)
        doc.print_(pdf)

        return str(output_path)

    def _wrong_pdf_filename(self, rows) -> str:
        first = rows[0] if rows else None
        obs = self._slug_part(getattr(first, "obs", ""), fallback="sin-obs")
        prestador = self._slug_part(getattr(first, "prestador_nombre", ""), fallback="sin-prestador")
        periodo = self._slug_part(self._periodo_label(), fallback="sin-periodo")
        return f"{obs}-{prestador}-{periodo}-mal-entregado".upper() + ".PDF"

    def _periodo_label(self) -> str:
        if not self._recepcion_id:
            return "sin-periodo"

        try:
            with session_scope() as s:
                row = (
                    s.query(Periodo.anio, Periodo.mes, Periodo.quincena)
                    .join(Recepcion, Recepcion.periodo_id == Periodo.periodo_id)
                    .filter(Recepcion.recepcion_id == int(self._recepcion_id))
                    .first()
                )

            if not row:
                return "sin-periodo"

            anio, mes, quincena = row
            return f"{int(anio):04d}-{int(mes):02d}-q{int(quincena)}"
        except Exception:
            return "sin-periodo"

    @staticmethod
    def _slug_part(value, *, fallback: str) -> str:
        text = str(value or "").strip().lower()
        if not text:
            return fallback

        text = unicodedata.normalize("NFD", text)
        text = text.encode("ascii", "ignore").decode("utf-8")
        text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
        return text or fallback
