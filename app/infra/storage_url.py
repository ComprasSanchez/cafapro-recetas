from __future__ import annotations

from app.config.settings import settings


def build_public_url(key_or_url: str) -> str:
    """
    Si ya es URL (http/https) la devuelve tal cual.
    Si es key S3 -> arma CloudFront URL.
    """
    s = (key_or_url or "").strip()
    if not s:
        return ""

    if s.startswith("http://") or s.startswith("https://"):
        return s

    base = settings.CLOUDFRONT_BASE_URL
    if not base:
        raise RuntimeError("Falta CLOUDFRONT_BASE_URL en el .env")

    base = base.replace("https://", "").replace("http://", "").strip("/")

    key = s.lstrip("/")
    return f"https://{base}/{key}"