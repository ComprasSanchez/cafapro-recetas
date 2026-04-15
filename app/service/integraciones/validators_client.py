from __future__ import annotations

import os
import time
from datetime import date
from typing import Any

import httpx


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return float(default)
    try:
        return float(str(raw).strip())
    except Exception:
        return float(default)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return int(default)
    try:
        return int(str(raw).strip())
    except Exception:
        return int(default)


class ValidatorsClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout_s: float = 180.0,
        retries: int = 1,
    ) -> None:
        self.base_url = (
            base_url
            or os.getenv("VALIDATORS_API_BASE_URL")
            or "https://recetas-api-production.up.railway.app"
        ).rstrip("/")

        self.retries = max(0, _env_int("VALIDATORS_RETRIES", retries))
        self._timeout_connect_s = _env_float("VALIDATORS_TIMEOUT_CONNECT_S", 10.0)
        self._timeout_read_s = _env_float("VALIDATORS_TIMEOUT_READ_S", timeout_s)
        self._timeout_write_s = _env_float("VALIDATORS_TIMEOUT_WRITE_S", 30.0)
        self._timeout_pool_s = _env_float("VALIDATORS_TIMEOUT_POOL_S", 30.0)

        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"accept": "application/json", "content-type": "application/json"},
            timeout=httpx.Timeout(
                connect=self._timeout_connect_s,
                read=self._timeout_read_s,
                write=self._timeout_write_s,
                pool=self._timeout_pool_s,
            ),
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

        for i in range(attempts):
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
            except httpx.TimeoutException as e:
                last_exc = e
                if i + 1 < attempts:
                    time.sleep(0.8 * (i + 1))
                continue
            except httpx.HTTPStatusError as e:
                last_exc = e
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

                if i + 1 < attempts:
                    time.sleep(0.8 * (i + 1))
                continue
            except httpx.HTTPError as e:
                last_exc = e
                break

        if isinstance(last_exc, httpx.TimeoutException):
            raise TimeoutError(
                "La API de validadores tardó demasiado en responder "
                f"(timeout de lectura: {int(self._timeout_read_s)}s)."
            ) from last_exc

        raise last_exc if last_exc else RuntimeError("Error desconocido consultando Validators API")

    def incluir_excluir_recetas(
        self,
        *,
        validador: str,
        nro_prestador: int,
        cod_financiador: int,
        accion: str,
        referencias: list[str],
    ) -> dict[str, Any]:
        accion_norm = (accion or "").strip().upper()
        if accion_norm not in {"E", "I"}:
            raise ValueError("Accion invalida. Debe ser 'E' (Excluir) o 'I' (Incluir).")

        refs_limpias: list[str] = []
        seen: set[str] = set()
        for ref in referencias or []:
            value = str(ref or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            refs_limpias.append(value)

        payload: dict[str, Any] = {
            "validador": (validador or "").strip().lower(),
            "nroPrestador": int(nro_prestador),
            "codFinanciador": int(cod_financiador),
            "accion": accion_norm,
            "referencias": refs_limpias,
        }

        attempts = 1 + self.retries
        last_exc: Exception | None = None

        for i in range(attempts):
            try:
                r = self._client.post("/validators/incluir_excluir_recetas", json=payload)
                r.raise_for_status()

                data = r.json()
                if isinstance(data, dict):
                    return data
                if isinstance(data, list):
                    return {"items": data}
                return {"ok": True}
            except httpx.TimeoutException as e:
                last_exc = e
                if i + 1 < attempts:
                    time.sleep(0.8 * (i + 1))
                continue
            except httpx.HTTPStatusError as e:
                last_exc = e
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

                if i + 1 < attempts:
                    time.sleep(0.8 * (i + 1))
                continue
            except httpx.HTTPError as e:
                last_exc = e
                break

        if isinstance(last_exc, httpx.TimeoutException):
            raise TimeoutError(
                "La API de validadores tardó demasiado en responder "
                f"(timeout de lectura: {int(self._timeout_read_s)}s)."
            ) from last_exc

        raise last_exc if last_exc else RuntimeError("Error desconocido consultando Validators API")
