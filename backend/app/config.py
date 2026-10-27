from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT / ".env", ROOT / "backend/.env"), extra="ignore"
    )
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = "gemini-3.1-flash-lite"
    gemini_free_tier_confirmed: bool = False
    answer_mode: Literal["gemini", "extractive"] = "gemini"
    admin_api_key: SecretStr = SecretStr("")
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_backend: str = "onnx"
    data_dir: Path = ROOT / "data"
    source_config: Path = ROOT / "config/approved_sources.yaml"
    cors_origins: list[str] = ["http://localhost:3000"]
    rate_limit_per_minute: int = Field(default=12, ge=1, le=120)
    global_generation_per_day: int = Field(default=150, ge=1)
    retrieval_k: int = Field(default=7, ge=1, le=15)
    min_similarity: float = 0.30
    request_timeout: float = 25.0
    serve_frontend: bool = True
    frontend_dir: Path = ROOT / "frontend/out"
    log_unanswered: bool = True

    @property
    def generation_enabled(self) -> bool:
        return (
            bool(self.gemini_api_key.get_secret_value())
            and self.gemini_free_tier_confirmed
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
