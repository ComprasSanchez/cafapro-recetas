from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import boto3
from botocore.config import Config


@dataclass(frozen=True)
class S3Cfg:
    bucket: str
    region: str
    access_key_id: str
    secret_access_key: str
    cache_control: str = "public, max-age=1296000, s-maxage=1296000"  # 15 días por default


class S3Storage:
    """
    Storage mínimo: subir bytes a S3 con metadata HTTP útil para CloudFront cache.
    """

    def __init__(self, cfg: S3Cfg) -> None:
        self.cfg = cfg

        self._client = boto3.client(
            "s3",
            region_name=cfg.region,
            aws_access_key_id=cfg.access_key_id,
            aws_secret_access_key=cfg.secret_access_key,
            config=Config(retries={"max_attempts": 5, "mode": "standard"}),
        )

    def put_jpg(self, key: str, data: bytes, *, content_disposition: Optional[str] = None) -> None:
        key = (key or "").lstrip("/")
        if not key:
            raise ValueError("S3 key vacía")

        extra = {
            "Bucket": self.cfg.bucket,
            "Key": key,
            "Body": data,
            "ContentType": "image/jpeg",
            "CacheControl": self.cfg.cache_control,
        }
        if content_disposition:
            extra["ContentDisposition"] = content_disposition

        self._client.put_object(**extra)
