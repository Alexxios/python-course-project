"""Environment configuration; settings never read .env implicitly."""

from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    database_url: str = "sqlite:///learning.sqlite3"
    access_token_seconds: int = Field(default=900, ge=60, le=86400)
    refresh_token_seconds: int = Field(default=604800, ge=300, le=2592000)
    quiz_generator: Literal["local", "openai"] = "local"
    openai_api_key: SecretStr | None = None
    openai_model: str | None = None
