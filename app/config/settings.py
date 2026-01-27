from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ✅ default para que el exe arranque aunque no haya .env
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5434/cafapro_db"

settings = Settings()
