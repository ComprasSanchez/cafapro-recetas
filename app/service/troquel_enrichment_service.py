from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.dto.medicamentos_dto import MedicamentoDTO
from app.service.medicamento_client import MedicamentoClient
from app.db.models import EstadoTroquelEnum


@dataclass(frozen=True)
class TroquelEnrichment:
    estado: EstadoTroquelEnum
    code_alfabeta: int
    presentacion: Optional[str]
    droga_concat: Optional[str]


class TroquelEnrichmentService:
    """
    Encapsula la decisión de negocio:
    - si encuentro medicamento: estado V + completar campos
    - si 404/no data: estado A
    - si error endpoint: estado A (pero no rompe procesamiento)
    """
    def __init__(self, client: Optional[MedicamentoClient] = None):
        self._client = client or MedicamentoClient()

    def enrich_by_codebar(self, codebar: str) -> TroquelEnrichment:
        codebar = (codebar or "").strip()

        try:
            dto: Optional[MedicamentoDTO] = self._client.get_by_codebar(codebar)
            if dto is None:
                return TroquelEnrichment(
                    estado=EstadoTroquelEnum.A,
                    code_alfabeta=0,
                    presentacion=None,
                    droga_concat=None,
                )

            return TroquelEnrichment(
                estado=EstadoTroquelEnum.V,
                code_alfabeta=dto.code_alfabeta or 0,
                presentacion=dto.presentacion,
                droga_concat=dto.drogas_concat,
            )

        except Exception:
            # Endpoint caído / timeout / 5xx:
            # No rompemos el proceso completo, dejamos incompleto.
            return TroquelEnrichment(
                estado=EstadoTroquelEnum.A,
                code_alfabeta=0,
                presentacion=None,
                droga_concat=None,
            )
