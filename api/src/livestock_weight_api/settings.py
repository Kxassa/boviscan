from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    lw_api_db_path: str = str(Path("data") / "livestock-weight.db")
    firebase_auth_enabled: bool = False
    # Default examples for BoviScan — override via env; never commit secrets
    google_cloud_project: str | None = "boviscan-c2430"
    firebase_project_id: str | None = "boviscan-c2430"
    firestore_emulator_host: str | None = None
    # GOOGLE_APPLICATION_CREDENTIALS is read by Google libs from the environment;
    # we never embed credential material here.
    # LIS bridge (optional outbound) — see docs/INTEGRATION_LIS.md
    lis_ingest_url: str | None = None
    lis_device_token: str | None = None
    lis_ingest_token: str | None = None  # alias for lis_device_token

    @property
    def db_path(self) -> Path:
        return Path(self.lw_api_db_path)


settings = Settings()
