from app.infra.s3_storage import S3Storage, S3Cfg
from app.config.settings import settings


s3_storage = S3Storage(
            S3Cfg(
                bucket=settings.S3_BUCKET,
                region=settings.AWS_REGION,
                access_key_id=settings.AWS_ACCESS_KEY_ID,
                secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                cache_control=settings.S3_CACHE_CONTROL,
            )
        )