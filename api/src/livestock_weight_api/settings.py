from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    lw_api_db_path: str = str(Path("data") / "livestock-weight.db")
    firebase_auth_enabled: bool = False
    google_cloud_project: str | None = None
    firestore_emulator_host: str | None = None
    # GOOGLE_APPLICATION_CREDENTIALS is read by Google libs from the environment;
    # we never embed credential material here.

    @property
    def db_path(self) -> Path:
        return Path(self.lw_api_db_path)


settings = Settings()
