"""Настройки приложения.

Значения читаются из переменных окружения или из файла .env
(pydantic-settings делает это автоматически).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./app.db"

    # В реальном проекте секрет обязательно задаётся через .env!
    secret_key: str = "dev-secret-key-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60


settings = Settings()
