import base64
import binascii
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigError(RuntimeError):
    pass


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    master_secret: str = Field(default="", repr=False)
    jwt_secret: str = Field(default="", repr=False)
    database_url: str = "sqlite:///./awan.db"
    storage_dir: Path = Path("./storage")
    session_minutes: int = 60

    @property
    def master_secret_bytes(self) -> bytes:
        return base64.b64decode(self.master_secret, validate=True)


def validate_settings(settings: Settings) -> Settings:
    if not settings.master_secret.strip():
        raise ConfigError("MASTER_SECRET kosong. Isi di .env (lihat .env.example).")
    if not settings.jwt_secret.strip():
        raise ConfigError("JWT_SECRET kosong. Isi di .env (lihat .env.example).")
    try:
        raw = settings.master_secret_bytes
    except (binascii.Error, ValueError):
        raise ConfigError("MASTER_SECRET harus base64 yang valid.") from None
    if len(raw) != 32:
        raise ConfigError(f"MASTER_SECRET harus 32 byte setelah decode base64, sekarang {len(raw)} byte.")
    if settings.jwt_secret == settings.master_secret:
        raise ConfigError("JWT_SECRET tidak boleh sama dengan MASTER_SECRET.")
    if settings.session_minutes <= 0:
        raise ConfigError("SESSION_MINUTES harus lebih dari 0.")
    return settings


@lru_cache
def get_settings() -> Settings:
    return validate_settings(Settings())
