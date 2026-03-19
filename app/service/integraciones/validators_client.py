from __future__ import annotations

import os
from datetime import date
from typing import Any

import httpx


class ValidatorsClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout_s: float = 20.0,
        retries: int = 2,
    ) -> None:
        self.base_url = (
            base_url
            or os.getenv("VALIDATORS_API_BASE_URL")
            or "http://localhost:3000" #"https://recetas-api-production.up.railway.app"
        ).rstrip("/")
        self.retries = max(0, int(retries))
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"accept": "application/json", "content-type": "application/json"},
            timeout=httpx.Timeout(timeout_s),
        )

    def get_pendientes(
        self,
        *,
        validador: str,
        nro_prestador: int,
        cod_financiador: int,
        fecha_hasta: str | None = None,
    ) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {
            "validador": (validador or "").strip().lower(),
            "nroPrestador": int(nro_prestador),
            "codFinanciador": int(cod_financiador),
            "fechaHasta": (fecha_hasta or date.today().isoformat()),
        }

        attempts = 1 + self.retries
        last_exc: Exception | None = None

        for _ in range(attempts):
            try:
                r = self._client.post("/validators/pendientes", json=payload)
                r.raise_for_status()
                data = r.json()
                if isinstance(data, list):
                    return [x for x in data if isinstance(x, dict)]
                if isinstance(data, dict):
                    items = data.get("items") or data.get("data") or []
                    if isinstance(items, list):
                        return [x for x in items if isinstance(x, dict)]
                return []
            except (httpx.TimeoutException, httpx.HTTPStatusError) as e:
                last_exc = e
                if isinstance(e, httpx.HTTPStatusError):
                    body = ""
                    try:
                        body = e.response.text
                    except Exception:
                        body = ""
                    status = e.response.status_code
                    if status == 400:
                        raise ValueError(f"Error API Validators (400): {body}") from e
                    if status == 401:
                        raise ValueError("Error API Validators (401): acceso no autorizado.") from e
                continue
            except httpx.HTTPError as e:
                last_exc = e
                break

        raise last_exc if last_exc else RuntimeError("Error desconocido consultando Validators API")
