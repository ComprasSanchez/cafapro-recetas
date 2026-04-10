from __future__ import annotations

from app.application.mal_entrego_excel_application import (
    ExportMalEntregoExcelIn,
    ExportMalEntregoExcelOut,
    MalEntregoExcelApplication,
)


class MalEntregoExcelUseCase(MalEntregoExcelApplication):
    pass


__all__ = [
    "MalEntregoExcelUseCase",
    "ExportMalEntregoExcelIn",
    "ExportMalEntregoExcelOut",
]
