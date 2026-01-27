from __future__ import annotations

import os
from typing import Optional

import httpx

from app.dto.medicamentos_dto import MedicamentoDTO


class MedicamentoClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout_s: float = 3.0,
        retries: int = 1,
    ):
        self.base_url = (base_url or os.getenv("MEDICAMENTOS_API_BASE_URL") or "https://quantio-api-production.up.railway.app").rstrip("/")
        self.retries = max(0, int(retries))

        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"accept": "application/json"},
            timeout=httpx.Timeout(timeout_s),
        )

        # cache: codebar -> DTO o None (si 404)
        self._cache: dict[str, Optional[MedicamentoDTO]] = {}

    @staticmethod
    def _is_valid_codebar(codebar: str) -> bool:
        codebar = (codebar or "").strip()
        return bool(codebar) and codebar.isdigit() and len(codebar) == 13

    def get_by_codebar(self, codebar: str) -> Optional[MedicamentoDTO]:
        codebar = (codebar or "").strip()

        # caso límite: inválido
        if not self._is_valid_codebar(codebar):
            return None

        if codebar in self._cache:
            return self._cache[codebar]

        attempts = 1 + self.retries
        last_exc: Optional[Exception] = None

        for _ in range(attempts):
            try:
                r = self._client.get(f"/medicamentos/codebar/{codebar}")

                if r.status_code == 404:
                    self._cache[codebar] = None
                    return None

                # Si 5xx: cae al raise_for_status y permite retry
                r.raise_for_status()

                data = r.json()
                if not isinstance(data, dict):
                    self._cache[codebar] = None
                    return None

                dto = MedicamentoDTO.from_json(data)
                self._cache[codebar] = dto
                return dto

            except (httpx.TimeoutException, httpx.HTTPStatusError) as e:
                # retry solo si fue timeout o status error (incluye 5xx)
                last_exc = e
                continue
            except httpx.HTTPError as e:
                # otro error de transporte, no insistimos demasiado
                last_exc = e
                break

        # Importante: no cacheamos errores transitorios (para que en otra corrida pueda funcionar)
        raise last_exc if last_exc else RuntimeError("Error desconocido consultando endpoint de medicamentos")
