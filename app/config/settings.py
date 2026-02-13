from __future__ import annotations

from pathlib import Path
import sys

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _app_dir() -> Path:
    """
    Dev: carpeta del proyecto (archivo que ejecutás).
    EXE: carpeta donde está el .exe (Inno instala en {app}).
    """
    return Path(sys.argv[0]).resolve().parent


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
    # DB
    # -----------------------
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5434/cafapro_db"
    )

    # -----------------------
    # AWS / S3 / CloudFront
    # -----------------------
    AWS_REGION: str = Field(default="us-east-1")
    S3_BUCKET: str = Field(default="")

    CLOUDFRONT_BASE_URL: str = Field(default="")  # ej: https://dxxxx.cloudfront.net

    AWS_ACCESS_KEY_ID: str = Field(default="")
    AWS_SECRET_ACCESS_KEY: str = Field(default="")

    # 60 días
    S3_CACHE_CONTROL: str = Field(
        default="public, max-age=5184000, s-maxage=5184000"
    )

    # -----------------------
    # Helpers
    # -----------------------
    def validate_required(self) -> None:
        """
        Llamalo al inicio de la app para fallar con mensaje claro.
        """
        missing: list[str] = []

        if not self.DATABASE_URL.strip():
            missing.append("DATABASE_URL")

        # Si querés habilitar AWS por feature-flag, lo hacemos.
        # Por ahora lo consideramos requerido.
        if not self.S3_BUCKET.strip():
            missing.append("S3_BUCKET")
        if not self.CLOUDFRONT_BASE_URL.strip():
            missing.append("CLOUDFRONT_BASE_URL")
        if not self.AWS_ACCESS_KEY_ID.strip():
            missing.append("AWS_ACCESS_KEY_ID")
        if not self.AWS_SECRET_ACCESS_KEY.strip():
            missing.append("AWS_SECRET_ACCESS_KEY")

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
        key = key.lstrip("/")
        return f"{self.CLOUDFRONT_BASE_URL.rstrip('/')}/{key}"


settings = Settings()

