from __future__ import annotations

from decimal import Decimal
from typing import Dict, Optional, Set, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Asociacion,
    ArchivoDetalle,
    Troqueles,
    EstadoTroquelEnum,
)
from app.dto.medicamentos_dto import MedicamentoDTO
from app.service.integraciones.medicamento_client import MedicamentoClient


class TroquelesService:
    def __init__(self, client: Optional[MedicamentoClient] = None) -> None:
        # ✅ Directo a la API
        self._client = client or MedicamentoClient()

    # -------------------------
    # Public API
    # -------------------------
    def create(self, s: Session, asociacion_id: int, codigo_barra: str, cantidad: int) -> Troqueles:
        """
        Crea un troquel MANUAL en Auditoría Visual.

        Reglas:
        - A = API 404 (dto None) -> NO se crea
        - V = API OK y code_alfabeta coincide con algún cod_medic del ArchivoDetalle -> se crea
        - R = API OK y NO coincide -> NO se crea

        Monto:
        - SOLO si V: suma importe_obs del/los ArchivoDetalle cuyo cod_medic == code_alfabeta
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

        # 3) API (404 => None)
        dto: Optional[MedicamentoDTO] = self._client.get_by_codebar(codigo_barra)

        # 4) Estado final A/V/R
        estado = self._calc_estado(dto=dto, cods_detalle=cods_detalle)

        # 5) REGLA NEGOCIO: solo permitir V
        if estado == EstadoTroquelEnum.A:
            raise ValueError("No se puede agregar: código no encontrado en la API (A / 404).")
        if estado == EstadoTroquelEnum.R:
            raise ValueError("No se puede agregar: el medicamento no coincide con el detalle del archivo (R).")

        # 6) Monto (solo si V)
        monto = self._calc_monto(dto=dto, importe_por_cod=importe_por_cod)

        troq = Troqueles(
            receta_id=receta_id,
            codigo_barra=codigo_barra,
            droga=(dto.drogas_concat if dto else None),
            presentacion=(dto.presentacion if dto else None),
            code_alfabeta=int(dto.code_alfabeta or 0) if dto else 0,
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

        troq.cantidad = int(cantidad) #Hacer validacion de cantidad con archvio detalle
        troq.estado = EstadoTroquelEnum.V
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

    def _calc_estado(self, dto: Optional[MedicamentoDTO], cods_detalle: Set[str]) -> EstadoTroquelEnum:
        # A si API no encontró (404 => dto None)
        if dto is None:
            return EstadoTroquelEnum.A

        # V si code_alfabeta matchea cod_medic, sino R
        ca = self._norm_str(dto.code_alfabeta)
        if ca and ca in cods_detalle:
            return EstadoTroquelEnum.V
        return EstadoTroquelEnum.R

    def _calc_monto(self, dto: Optional[MedicamentoDTO], importe_por_cod: Dict[str, Decimal]) -> Decimal:
        """
        monto = importe_obs del ArchivoDetalle que matchea (code_alfabeta)
        (si no hay match, es 0; pero create() solo llega acá si es V)
        """
        if dto is None:
            return Decimal("0")

        ca = self._norm_str(dto.code_alfabeta)
        if not ca:
            return Decimal("0")

        return importe_por_cod.get(ca, Decimal("0"))
