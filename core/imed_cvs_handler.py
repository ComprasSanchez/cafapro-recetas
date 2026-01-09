from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TypedDict

import csv

from config.config_manager import ConfigManager


# =========================
# Tipos (encabezado IMED)
# =========================

IMED_HEADER = [
    "Beneficiario",
    "Orden Del Lote",
    "Fecha",
    "Hora",
    "Nro Referencia",
    "Nro Receta",
    "Importe Pami",
    "Importe Gral",
    "A Cargo Entidad",
]


class RecetaRow(TypedDict, total=False):
    Beneficiario: str
    Orden_Del_Lote: str
    Fecha: str
    Hora: str
    Nro_Referencia: str
    Nro_Receta: str
    Importe_Pami: str
    Importe_Gral: str
    A_Cargo_Entidad: str


class DetalleRow(TypedDict, total=False):
    cod_medic: Optional[str]
    nombre: Optional[str]
    presentacion: Optional[str]
    estado: Optional[str]
    nro_aut: Optional[str]
    cantidad: Optional[str]
    importe_gral: Optional[str]
    importe_pami: Optional[str]
    desc: Optional[str]

RecetasPorRef = Dict[str, RecetaRow]
DetallesPorRef = Dict[str, List[DetalleRow]]


# =========================
# Handler
# =========================

def _parse_code_name_present(raw0: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    raw0: "54640 - DESLORAMAR 5 MG COMP.X 14 [MAR]"
    -> ("54640", "DESLORAMAR", "5 MG COMP.X 14 [MAR]")
    """
    s = (raw0 or "").strip()
    if not s:
        return None, None, None

    code = None
    rest = s

    if " - " in s:
        a, b = s.split(" - ", 1)
        code = a.strip() or None
        rest = b.strip()

    # nombre + presentación (separación simple: primer token como nombre, el resto presentación)
    # si tu “nombre” puede tener espacios, lo ajustamos con otra regla (por ej. hasta dos espacios o hasta el primer número).
    parts = rest.split()
    if not parts:
        return code, None, None

    nombre = parts[0].strip() or None
    present = " ".join(parts[1:]).strip() or None
    return code, nombre, present


def parse_detalle_row(fila: List[str]) -> DetalleRow:
    cod, nombre, present = _parse_code_name_present(fila[0] if len(fila) > 0 else "")

    return {
        "cod_medic": cod,
        "nombre": nombre,
        "presentacion": present,
        "estado": fila[2].strip() if len(fila) > 2 and fila[2] else None,
        "nro_aut": fila[3].strip() if len(fila) > 3 and fila[3] else None,
        "cantidad": fila[4].strip() if len(fila) > 4 and fila[4] else None,
        "importe_pami": fila[5].strip() if len(fila) > 5 and fila[5] else None,
        "desc": fila[6].strip() if len(fila) > 6 and fila[6] else None,
        "importe_gral": fila[7].strip() if len(fila) > 7 and fila[7] else None,
    }

class ImedCvsHandler:
    """
    Lee CSV IMED con este formato:
      - Sección "recetas": encabezado fijo (Beneficiario;Orden Del Lote;...)
      - Sección "detalles": líneas que empiezan con "DETALLE_<NRO_REF>"
        y luego filas de detalle por columnas posicionales.
    """
    def __init__(self, parent: Any | None = None) -> None:
        self.parent = parent
        self._config = ConfigManager()

        config_loaded = self._config.load()
        if not config_loaded:
            self._config.ask_for_folders(parent=self.parent)

        imed_folder = self._config.get("imed_folder")
        if not imed_folder:
            raise ValueError("imed_folder no está configurado. Vuelva a ejecutar la configuración.")

        self.imed_folder: Path = Path(imed_folder)

    # -------------------------
    # Utils parsing
    # -------------------------
    @staticmethod
    def _norm_spaces(s: str) -> str:
        return s.strip()

    @staticmethod
    def _yyyymmdd_from_date(date_str: str) -> str:
        s = date_str.strip()
        if s.isdigit() and len(s) == 8:
            return s
        # DD/MM/YYYY -> YYYYMMDD
        try:
            dd, mm, yyyy = s.split("/")
            if len(dd) == 1:
                dd = f"0{dd}"
            if len(mm) == 1:
                mm = f"0{mm}"
            return f"{yyyy}{mm}{dd}"
        except ValueError:
            raise ValueError(f"Formato de fecha inválido: '{date_str}'. Use 'YYYYMMDD' o 'DD/MM/YYYY'.")

    @staticmethod
    def parse_decimal(v: Any) -> Decimal:
        """
        Convierte strings tipo:
          - '1.234,56' -> 1234.56
          - '1234,56'  -> 1234.56
          - '1234.56'  -> 1234.56
        """
        if v is None:
            return Decimal("0")
        s = str(v).strip()
        if not s:
            return Decimal("0")

        # si tiene coma, asumimos formato AR: '.' miles y ',' decimal
        if "," in s:
            s = s.replace(".", "").replace(",", ".")
        try:
            return Decimal(s)
        except (InvalidOperation, ValueError):
            return Decimal("0")

    # -------------------------
    # Paths
    # -------------------------
    def get_path_cvs(self, imed: str, date: str) -> Path:
        yyyymmdd = self._yyyymmdd_from_date(date)
        filename = f"a_{imed.strip()}_{yyyymmdd}.csv"
        path = (self.imed_folder / filename).resolve()

        if not path.exists():
            raise FileNotFoundError(f"No se encontró el archivo IMED: {path}")

        return path

    # -------------------------
    # Lectura CSV
    # -------------------------
    def read_cvs_by_imed_and_date(self, imed: str, date: str) -> Tuple[RecetasPorRef, DetallesPorRef]:
        path = self.get_path_cvs(imed, date)
        return self.read_cvs(path)

    def read_cvs(self, path: str | Path) -> Tuple[RecetasPorRef, DetallesPorRef]:
        path = Path(path)

        recetas_por_ref: RecetasPorRef = {}
        detalles_por_ref: DetallesPorRef = {}

        # newline="" recomendado en Windows
        with path.open(encoding="utf-8", newline="") as f:
            reader = csv.reader(f, delimiter=";")

            encabezado: Optional[List[str]] = None
            buffer_detalles: List[List[str]] = []

            # 1) Recetas hasta DETALLE_
            for fila in reader:
                if not fila or all((c or "").strip() == "" for c in fila):
                    continue

                first = (fila[0] or "").strip()
                if first.startswith("DETALLE_"):
                    buffer_detalles.append(fila)
                    break

                if encabezado is None:
                    # Normalizamos encabezado
                    encabezado = [self._norm_spaces(x) for x in fila]
                    self._validar_encabezado(encabezado)
                    continue

                receta_dict = self._fila_a_receta(encabezado, fila)
                nro_ref = receta_dict.get("Nro_Referencia")
                if not nro_ref:
                    continue

                recetas_por_ref[nro_ref] = receta_dict

            # 2) Restante: detalles
            for fila in reader:
                buffer_detalles.append(fila)

        self._procesar_detalles(buffer_detalles, detalles_por_ref)

        return recetas_por_ref, detalles_por_ref

    # -------------------------
    # Helpers internos
    # -------------------------
    def _validar_encabezado(self, header: List[str]) -> None:
        """
        Valida que contenga las columnas mínimas esperadas.
        No falla si hay columnas extra, pero sí si faltan las core.
        """
        expected = set(IMED_HEADER)
        got = set(header)
        missing = [h for h in IMED_HEADER if h not in got]
        if missing:
            raise ValueError(
                "El CSV no tiene el encabezado esperado.\n"
                f"Faltan columnas: {missing}\n"
                f"Encabezado encontrado: {header}"
            )

    @staticmethod
    def _fila_a_receta(header: List[str], fila: List[str]) -> RecetaRow:
        # zip corta al menor largo; completamos con "" si faltan columnas
        if len(fila) < len(header):
            fila = fila + [""] * (len(header) - len(fila))

        raw = dict(zip(header, fila))

        # Mapear a claves "seguras" (sin espacios) para tu app
        receta: RecetaRow = {
            "Beneficiario": (raw.get("Beneficiario") or "").strip(),
            "Orden_Del_Lote": (raw.get("Orden Del Lote") or "").strip(),
            "Fecha": (raw.get("Fecha") or "").strip(),
            "Hora": (raw.get("Hora") or "").strip(),
            "Nro_Referencia": (raw.get("Nro Referencia") or "").strip(),
            "Nro_Receta": (raw.get("Nro Receta") or "").strip(),
            "Importe_Pami": (raw.get("Importe Pami") or "").strip(),
            "Importe_Gral": (raw.get("Importe Gral") or "").strip(),
            "A_Cargo_Entidad": (raw.get("A Cargo Entidad") or "").strip(),
        }
        return receta

    @staticmethod
    def _procesar_detalles(buffer: List[List[str]], out: DetallesPorRef) -> None:
        current_ref: Optional[str] = None

        for fila in buffer:
            if not fila or all((c or "").strip() == "" for c in fila):
                continue

            head = (fila[0] or "").strip()
            # Línea tipo DETALLE_<NRO_REF>
            if head.startswith("DETALLE_"):
                current_ref = head.replace("DETALLE_", "").strip()
                out.setdefault(current_ref, [])
                continue

            if current_ref is None:
                continue

            d = parse_detalle_row(fila)
            out[current_ref].append(d)
