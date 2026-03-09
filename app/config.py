from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    spotify_client_id: str
    spotify_client_secret: str
    spotify_redirect_uri: str = "http://localhost:8000/auth/callback"

    # Neon / PostgreSQL (sync)
    database_url: str = "postgresql://user:pass@host/dbname"

    secret_key: str = "change-me"
    frontend_url: str = "http://localhost:5173"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
