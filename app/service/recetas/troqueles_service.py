from __future__ import annotations

from decimal import Decimal
from typing import Dict, Optional, Set, Tuple

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.models import (
    Asociacion,
    ArchivoDetalle,
    Troqueles,
    EstadoTroquelEnum,
)
from app.service.recetas.troquel_enrichment_service import (
    TroquelEnrichmentService,
    TroquelEnrichment,
)


class TroquelesService:
    def __init__(self, enrich: Optional[TroquelEnrichmentService] = None) -> None:
        self._enrich = enrich or TroquelEnrichmentService()

    # -------------------------
    # Public API
    # -------------------------
    def create(self, s: Session, asociacion_id: int, codigo_barra: str, cantidad: int) -> Troqueles:
        """
        Crea un troquel MANUAL en Auditoría Visual.
        Regla: SOLO se crea si queda VERDE (V). Si da A o R -> NO se crea.
        - contexto por asociacion_id -> receta_id + archivo_id
        - ArchivoDetalle del archivo -> cods_detalle + importe_por_cod
        - API enrichment -> code_alfabeta, droga, presentacion, estado (A)
        - estado final: A si API A; V si match; R si no match
        - monto: importe_obs del ArchivoDetalle que matchea (code_alfabeta)
        """
        codigo_barra = (codigo_barra or "").strip()
        if not codigo_barra:
            raise ValueError("codigo_barra es requerido")

        if int(cantidad) <= 0:
            raise ValueError("cantidad debe ser > 0")

        # 1) Contexto: asociacion -> receta_id, archivo_id
        asoc = s.execute(
            select(Asociacion).where(Asociacion.asociacion_id == int(asociacion_id))
        ).scalar_one_or_none()
        if not asoc:
            raise ValueError(f"Asociacion {asociacion_id} no existe")

        receta_id = int(asoc.receta_id)
        archivo_id = int(asoc.archivo_id)

        # 2) “Esperados” del archivo
        cods_detalle, importe_por_cod = self._load_archivo_detalle_expectations(s, archivo_id)

        # 3) Enrichment API
        enr = self._enrich.enrich_by_codebar(codigo_barra)

        # 4) Calcular estado final (V/A/R)
        estado = self._calc_estado(enr=enr, cods_detalle=cods_detalle)

        # 5) REGLA NEGOCIO: solo permitir V
        if estado == EstadoTroquelEnum.A:
            raise ValueError("No se puede agregar: código no encontrado en la API (A).")
        if estado == EstadoTroquelEnum.R:
            raise ValueError("No se puede agregar: el medicamento no coincide con el detalle del archivo (R).")

        # 6) Monto (sale del ArchivoDetalle que matchea)
        monto = self._calc_monto(enr=enr, importe_por_cod=importe_por_cod)

        troq = Troqueles(
            receta_id=receta_id,
            codigo_barra=codigo_barra,
            droga=enr.droga_concat,
            presentacion=enr.presentacion,
            code_alfabeta=int(enr.code_alfabeta or 0),
            monto=monto,
            cantidad=int(cantidad),
            estado=EstadoTroquelEnum.V,  # por regla, siempre V acá
        )
        s.add(troq)
        s.flush()  # para troquel_id
        return troq

    @staticmethod
    def update(s: Session, troquel_id: int, cantidad: int) -> None:
        """
        SOLO actualiza cantidad. No recalcula estado/monto/info.
        """
        if int(cantidad) < 0:
            raise ValueError("cantidad debe ser >= 0")

        troq = s.get(Troqueles, int(troquel_id))
        if not troq:
            raise ValueError(f"Troquel {troquel_id} no existe")

        troq.cantidad = int(cantidad)
        s.flush()

    # -------------------------
    # Helpers
    # -------------------------
    @staticmethod
    def _norm_str(x) -> str:
        return str(x).strip() if x is not None else ""

    def _load_archivo_detalle_expectations(
        self, s: Session, archivo_id: int
    ) -> Tuple[Set[str], Dict[str, Decimal]]:
        """
        - cods_detalle: set de cod_medic no vacíos
        - importe_por_cod: suma de importe_obs por cod_medic
        """
        dets = s.execute(
            select(ArchivoDetalle).where(ArchivoDetalle.archivo_id == int(archivo_id))
        ).scalars().all()

        cods: Set[str] = set()
        imp: Dict[str, Decimal] = {}

        for d in dets:
            ca = self._norm_str(getattr(d, "cod_medic", None))
            if not ca:
                continue
            cods.add(ca)

            v = getattr(d, "importe_obs", None)
            v = Decimal(str(v)) if v is not None else Decimal("0")
            imp[ca] = imp.get(ca, Decimal("0")) + v

        return cods, imp

    def _calc_estado(self, enr: TroquelEnrichment, cods_detalle: Set[str]) -> EstadoTroquelEnum:
        # Amarillo si API dice A (no encontrado / sin info)
        if enr.estado == EstadoTroquelEnum.A:
            return EstadoTroquelEnum.A

        # Verde si code_alfabeta matchea cod_medic, sino Rojo
        ca = self._norm_str(enr.code_alfabeta)
        if ca and ca in cods_detalle:
            return EstadoTroquelEnum.V
        return EstadoTroquelEnum.R

    def _calc_monto(self, enr: TroquelEnrichment, importe_por_cod: Dict[str, Decimal]) -> Decimal:
        """
        monto = importe_obs del ArchivoDetalle que matchea (code_alfabeta)
        (si no hay match, sería 0, pero por regla create() solo llega acá si es V)
        """
        ca = self._norm_str(enr.code_alfabeta)
        if not ca:
            return Decimal("0")
        return importe_por_cod.get(ca, Decimal("0"))
