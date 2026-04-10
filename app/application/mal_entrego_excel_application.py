from __future__ import annotations

from dataclasses import dataclass

from app.service.debitos.view_debitos import ViewDebitos


@dataclass(frozen=True)
class ExportMalEntregoExcelIn:
    obra_social_id: int
    obra_social_nombre: str
    anio: int
    mes: int
    folder: str


@dataclass(frozen=True)
class ExportMalEntregoExcelOut:
    total: int
    file_path: str


class MalEntregoExcelApplication:
    @staticmethod
    def run(data: ExportMalEntregoExcelIn) -> ExportMalEntregoExcelOut:
        rows = ViewDebitos.list_wrong_debitos_month(
            obra_social_id=int(data.obra_social_id),
            anio=int(data.anio),
            mes=int(data.mes),
        )

        if not rows:
            raise ValueError("No hay débitos mal entregados para la obra social y período seleccionados.")

        file_path = ViewDebitos.export_wrong_debitos_excel(
            rows=rows,
            folder=str(data.folder),
            obra_social_nombre=str(data.obra_social_nombre or ""),
            anio=int(data.anio),
            mes=int(data.mes),
        )

        return ExportMalEntregoExcelOut(total=len(rows), file_path=file_path)
