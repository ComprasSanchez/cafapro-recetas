from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional, Set

from core.process_tif import ScanOut

from app.db.models import Archivo, EstadoTroquelEnum


@dataclass(frozen=True)
class ProcesarItemIn:
    file_name: str
    full_path: str


@dataclass
class ProcesarResumen:
    ok: int = 0
    sin_match: int = 0
    duplicados: int = 0
    ya_asociado: int = 0
    errores: List[str] = field(default_factory=list)

    def merge(self, other: "ProcesarResumen") -> None:
        self.ok += other.ok
        self.sin_match += other.sin_match
        self.duplicados += other.duplicados
        self.ya_asociado += other.ya_asociado
        self.errores.extend(other.errores)


@dataclass(frozen=True)
class _MatchResult:
    ref_to_archivo: Dict[str, Optional[Archivo]]
    duplicated_refs: Set[str]
    missing_refs: Set[str]


@dataclass(frozen=True)
class _ScannedItem:
    it: ProcesarItemIn
    scan: ScanOut


@dataclass(frozen=True)
class _WorkItem:
    it: ProcesarItemIn
    scan: ScanOut
    archivo_id: int


@dataclass(frozen=True)
class _UploadResult:
    work: _WorkItem
    front_key: Optional[str]
    back_key: Optional[str]


@dataclass(frozen=True)
class _DetalleContext:
    cods_detalle: Set[str]
    cant_por_cod: Dict[str, int]
    importe_por_cod: Dict[str, Decimal]


@dataclass(frozen=True)
class _TroquelEval:
    codebar: str
    cantidad_scan: int
    estado: EstadoTroquelEnum
    code_alfabeta: int
    droga_concat: Optional[str]
    presentacion: Optional[str]
    monto: Decimal
