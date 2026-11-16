from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str
    database_host: str
    database_port: int
    database_name: str
    database_user: str
    database_password: SecretStr
    # Development default: only the local Vite dev server may call the API.
    cors_allowed_origins: list[str] = ["http://localhost:5173"]
    # Optional development aid: pause between background processing steps so
    # progress is visible in the UI. 0 (default) means no artificial delay.
    processing_step_delay_seconds: float = Field(default=0, ge=0, le=10)

    @property
    def database_url(self) -> URL:
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.database_user,
            password=self.database_password.get_secret_value(),
            host=self.database_host,
            port=self.database_port,
            database=self.database_name,
        )


settings = Settings()
