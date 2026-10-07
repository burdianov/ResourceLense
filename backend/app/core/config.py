from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ResourceLense API"
    environment: str = "development"
    debug: bool = True

    database_url: str = (
        "postgresql+psycopg://resourcelense:resourcelense@localhost:5432/resourcelense"
    )

    jwt_secret_key: str
    access_token_expire_minutes: int = 480

    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
