from __future__ import annotations

from pathlib import Path
import sys

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _app_dir() -> Path:
    # 1) Donde estás parado al ejecutar (dev / scripts)
    # 2) Si es exe, igual sirve porque el cwd suele ser {app} o lo podés setear
    return Path.cwd()


def _env_file_path() -> str:
    """
    Usamos siempre el .env al lado del ejecutable.
    """
    return str(_app_dir() / ".env")


class Settings(BaseSettings):
    """
    Settings centralizado para Desktop.
    Lee .env en {app}/.env (mismo folder del exe).
    """
    model_config = SettingsConfigDict(
        env_file=_env_file_path(),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # -----------------------
    # API
    # -----------------------
    API_CAFAPRO: str = Field(default="http://localhost:3000")

    # -----------------------
    # CloudFront
    # -----------------------
    CLOUDFRONT_BASE_URL: str = Field(default="")  # ej: https://dxxxx.cloudfront.net

    # -----------------------
    # TIFF processing
    # -----------------------
    TIFF_CHUNK_SIZE: int = Field(default=20)
    TIFF_SCAN_WORKERS: int = Field(default=2)
    TIFF_UPLOAD_WORKERS: int = Field(default=1)
    TIFF_CHUNK_PAUSE_MS: int = Field(default=0)
    TIFF_UPLOAD_PAUSE_MS: int = Field(default=0)
    TIFF_PIPELINE_MODE: str = Field(default="chunk")  # item|chunk

    # -----------------------
    # Helpers
    # -----------------------
    def validate_required(self) -> None:
        """
        Llamalo al inicio de la app para fallar con mensaje claro.
        """
        missing: list[str] = []

        if not self.API_CAFAPRO.strip():
            missing.append("API_CAFAPRO")

        # Si querés habilitar AWS por feature-flag, lo hacemos.
        # Por ahora lo consideramos requerido.
        if not self.CLOUDFRONT_BASE_URL.strip():
            missing.append("CLOUDFRONT_BASE_URL")

        if missing:
            env_path = _env_file_path()

            raise RuntimeError(
                "Faltan variables en el .env.\n"
                f"Ruta .env: {env_path}\n"
                "Faltan:\n - " + "\n - ".join(missing)
            )

    def cloudfront_url(self, key: str | None) -> str | None:
        if not key:
            return None
        v = key.strip()
        if v.startswith("http://") or v.startswith("https://"):
            return v
        base = (self.CLOUDFRONT_BASE_URL or "").strip()
        base = base.replace("https://", "").replace("http://", "").strip().rstrip("/")
        if not base:
            return None
        return f"https://{base}/{v.lstrip('/')}"


settings = Settings()

