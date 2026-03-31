from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "RefuPass API"
    database_url: str = "sqlite:///./refupass.db"
    allowed_origins: str = "http://localhost:5173,http://localhost:4173"
    inji_verify_mode: str = "stub"
    inji_verify_api_url: str = "http://localhost:18080/v1/verify"
    inji_web_url: str = "http://localhost:3001"
    inji_verify_ui_url: str = "http://localhost:13000"
    demo_beneficiary_subject: str = "5860356276"
    esignet_ui_url: str = "http://localhost:3000"
    esignet_api_url: str = "http://localhost:8088"
    esignet_callback_url: str = "http://127.0.0.1:8000/platform/identity/esignet/callback"
    esignet_client_name: str = "RefuPass Platform Verification"
    esignet_client_logo_url: str = "https://example.com/refupass-logo.png"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
