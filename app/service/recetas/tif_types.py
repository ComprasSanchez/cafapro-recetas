from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set

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
    con_header: int = 0
    sin_header: int = 0
    revision_por_sin_match: int = 0
    revision_por_ya_asociado: int = 0
    revision_por_header_vacio: int = 0
    revision_por_header_sin_match: int = 0
    revision_por_duplicado_lote_ref: int = 0
    revision_por_duplicado_lote_receta: int = 0
    reintentos_modo_seguro: int = 0
    render_total_seconds: float = 0.0
    upload_total_seconds: float = 0.0
    revision_muestras: List[str] = field(default_factory=list)
    errores: List[str] = field(default_factory=list)
    stats: Optional["ProcesarStats"] = None

    def merge(self, other: "ProcesarResumen") -> None:
        self.ok += other.ok
        self.sin_match += other.sin_match
        self.duplicados += other.duplicados
        self.ya_asociado += other.ya_asociado
        self.con_header += other.con_header
        self.sin_header += other.sin_header
        self.revision_por_sin_match += other.revision_por_sin_match
        self.revision_por_ya_asociado += other.revision_por_ya_asociado
        self.revision_por_header_vacio += other.revision_por_header_vacio
        self.revision_por_header_sin_match += other.revision_por_header_sin_match
        self.revision_por_duplicado_lote_ref += other.revision_por_duplicado_lote_ref
        self.revision_por_duplicado_lote_receta += other.revision_por_duplicado_lote_receta
        self.reintentos_modo_seguro += other.reintentos_modo_seguro
        self.render_total_seconds += float(other.render_total_seconds or 0.0)
        self.upload_total_seconds += float(other.upload_total_seconds or 0.0)
        if other.revision_muestras:
            limit = 20
            left = max(0, limit - len(self.revision_muestras))
            if left > 0:
                self.revision_muestras.extend(other.revision_muestras[:left])
        self.errores.extend(other.errores)
        if other.stats is not None:
            self.stats = other.stats


@dataclass(frozen=True)
class ProcesarStats:
    total_items: int = 0
    processed_items: int = 0
    chunk_count: int = 0
    elapsed_seconds: float = 0.0
    items_per_minute: float = 0.0
    seconds_per_item: float = 0.0
    chunk_min_seconds: float = 0.0
    chunk_avg_seconds: float = 0.0
    chunk_max_seconds: float = 0.0
    con_header: int = 0
    sin_header: int = 0
    revision_por_sin_match: int = 0
    revision_por_ya_asociado: int = 0
    revision_por_header_vacio: int = 0
    revision_por_header_sin_match: int = 0
    revision_por_duplicado_lote_ref: int = 0
    revision_por_duplicado_lote_receta: int = 0
    reintentos_modo_seguro: int = 0
    render_total_seconds: float = 0.0
    upload_total_seconds: float = 0.0


@dataclass(frozen=True)
class _MatchResult:
    ref_to_archivo: Dict[str, Optional[Archivo]]
    duplicated_refs: Set[str]
    missing_refs: Set[str]


@dataclass(frozen=True)
class _ScannedItem:
    it: ProcesarItemIn
    scan: ScanOut
    pages: List[Any] | None = None


@dataclass(frozen=True)
class _WorkItem:
    it: ProcesarItemIn
    scan: ScanOut
    archivo_id: int
    pages: List[Any] | None = None
    replace_receta_id: int | None = None


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
