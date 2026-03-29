from __future__ import annotations

from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem


def set_table_cell(tbl: QTableWidget, row: int, col: int, text: str) -> None:
    it = QTableWidgetItem(text)
    it.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
    tbl.setItem(row, col, it)


def render_troqueles_table(
    tbl_troqueles: QTableWidget,
    *,
    rows,
    estado_troquel_verde: str,
    estado_troquel_amarillo: str,
    estado_troquel_rojo: str,
    fmt_money,
) -> None:
    tbl_troqueles.setUpdatesEnabled(False)
    tbl_troqueles.setRowCount(len(rows))

    for i, t in enumerate(rows):
        estado = getattr(t, "estado", "")
        estado_code = str(getattr(estado, "value", estado) or "")

        set_table_cell(tbl_troqueles, i, 0, str(getattr(t, "codigo_barra", "") or ""))
        set_table_cell(tbl_troqueles, i, 1, str(getattr(t, "presentacion", "") or ""))
        set_table_cell(tbl_troqueles, i, 2, str(getattr(t, "cantidad", "") or ""))
        set_table_cell(tbl_troqueles, i, 3, str(getattr(t, "droga", "") or ""))
        set_table_cell(tbl_troqueles, i, 4, str(getattr(t, "code_alfabeta", "") or ""))
        set_table_cell(tbl_troqueles, i, 5, fmt_money(Decimal(str(getattr(t, "monto", 0) or 0))))
        set_table_cell(tbl_troqueles, i, 6, estado_code)

        troq_id = int(getattr(t, "troquel_id", 0) or 0)
        it0 = tbl_troqueles.item(i, 0)
        if it0 and troq_id:
            it0.setData(Qt.ItemDataRole.UserRole, troq_id)

        color = None
        if estado_code == estado_troquel_verde:
            color = QColor(17, 151, 59)
        elif estado_code == estado_troquel_amarillo:
            color = QColor(228, 245, 44)
        elif estado_code == estado_troquel_rojo:
            color = QColor(165, 32, 25)

        if color is not None:
            brush = QBrush(color)
            for c in range(tbl_troqueles.columnCount()):
                it = tbl_troqueles.item(i, c)
                if it:
                    it.setData(Qt.BackgroundRole, brush)

    tbl_troqueles.setUpdatesEnabled(True)


def render_archivo_detalle_table(tbl_arch_det: QTableWidget, *, rows, fmt_money) -> None:
    tbl_arch_det.setUpdatesEnabled(False)
    tbl_arch_det.setRowCount(len(rows))

    for i, d in enumerate(rows):
        set_table_cell(tbl_arch_det, i, 0, str(getattr(d, "codigo_barra", "") or ""))
        set_table_cell(tbl_arch_det, i, 1, str(getattr(d, "cod_medic", "") or ""))
        set_table_cell(tbl_arch_det, i, 2, str(getattr(d, "nombre", "") or ""))
        set_table_cell(tbl_arch_det, i, 3, str(getattr(d, "presentacion", "") or ""))
        set_table_cell(tbl_arch_det, i, 4, str(getattr(d, "estado", "") or ""))
        set_table_cell(tbl_arch_det, i, 5, str(getattr(d, "nro_autorizacion", "") or ""))
        set_table_cell(tbl_arch_det, i, 6, str(getattr(d, "cantidad", "") or ""))
        set_table_cell(tbl_arch_det, i, 7, fmt_money(Decimal(str(getattr(d, "importe_bruto", 0) or 0))))
        set_table_cell(tbl_arch_det, i, 8, fmt_money(Decimal(str(getattr(d, "importe_cobertura", 0) or 0))))
        set_table_cell(tbl_arch_det, i, 9, str(getattr(d, "descuento", "") or ""))

    tbl_arch_det.setUpdatesEnabled(True)


def render_header_fields(
    *,
    data,
    in_prescripcion,
    in_emision,
    in_venta,
    lb_big,
    lb_autorizacion,
    btn_debitada,
    fmt_date,
) -> None:
    in_prescripcion.setText(fmt_date(getattr(data.receta, "fecha_prescripcion", None)))
    in_emision.setText(fmt_date(getattr(data.receta, "fecha_emision", None)))
    in_venta.setText(fmt_date(getattr(data.receta, "fecha_venta", None)))

    lb_big.setText(str(getattr(data.archivo, "orden_lote", "") or "—"))
    lb_autorizacion.setText(str(getattr(data.archivo, "fecha", "") or "—"))
    btn_debitada.setVisible(bool(getattr(data, "has_historial_debitada", False)))


def render_resumen_fields(*, data, lb_a_cargo, lb_imp_obs, lb_imp_neto, fmt_money) -> None:
    lb_a_cargo.setText(
        fmt_money(Decimal(str(getattr(data.archivo, "importe_cobertura", 0) or 0)))
    )
    lb_imp_obs.setText(
        fmt_money(Decimal(str(getattr(data.archivo, "importe_afiliado", 0) or 0)))
    )
    lb_imp_neto.setText(
        fmt_money(Decimal(str(getattr(data.archivo, "importe_bruto", 0) or 0)))
    )


def render_navigation_label(*, lb_pos, idx: int, total: int) -> None:
    lb_pos.setText(f"{idx + 1} / {total}")
