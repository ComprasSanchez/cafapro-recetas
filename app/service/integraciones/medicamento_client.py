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
        self.base_url = (
            base_url
            or os.getenv("MEDICAMENTOS_API_BASE_URL")
            or "https://quantio-api-production.up.railway.app"
        ).rstrip("/")

        self.retries = max(0, int(retries))

        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"accept": "application/json"},
            timeout=httpx.Timeout(timeout_s),
        )

    @staticmethod
    def _is_valid_codebar(codebar: str) -> bool:
        codebar = (codebar or "").strip()
        return bool(codebar) and codebar.isdigit() and len(codebar) == 13

    def get_by_codebar(self, codebar: str) -> Optional[MedicamentoDTO]:
        """
        Devuelve:
          - MedicamentoDTO si existe (200)
          - None si no existe (404) o si el codebar es inválido
        Lanza excepción si hay errores transitorios (timeout/5xx) luego de reintentos.
        """
        codebar = (codebar or "").strip()

        # inválido => lo tratamos como "no encontrado"
        if not self._is_valid_codebar(codebar):
            return None

        attempts = 1 + self.retries
        last_exc: Optional[Exception] = None

        for _ in range(attempts):
            try:
                r = self._client.get(f"/medicamentos/codebar/{codebar}")

                if r.status_code == 404:
                    return None

                r.raise_for_status()

                data = r.json()
                if not isinstance(data, dict):
                    return None

                dto = MedicamentoDTO.from_json(data)
                return dto

            except (httpx.TimeoutException, httpx.HTTPStatusError) as e:
                last_exc = e
                continue
            except httpx.HTTPError as e:
                last_exc = e
                break

        raise last_exc if last_exc else RuntimeError(
            "Error desconocido consultando endpoint de medicamentos"
        )

    def get_many_by_codebars(self, codebars: list[str]) -> dict[str, Optional[MedicamentoDTO]]:
        """
        Consulta múltiples codebars en un solo request batch.
        Devuelve un dict: { codebar: MedicamentoDTO | None }
        """

        # limpiar + validar
        clean = [
            cb.strip()
            for cb in codebars
            if self._is_valid_codebar(cb)
        ]

        if not clean:
            return {}

        # eliminar duplicados
        unique = list(set(clean))

        r = self._client.post(
            "/medicamentos/codebar/batch",
            json={"codebars": unique},
        )

        r.raise_for_status()

        data = r.json()

        result: dict[str, Optional[MedicamentoDTO]] = {}

        for cb in unique:
            raw = data.get(cb)

            if raw is None:
                result[cb] = None
            else:
                result[cb] = MedicamentoDTO.from_json(raw)

        return result

