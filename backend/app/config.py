from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = Field(default="", description="OpenAI-compatible API key")
    openai_base_url: str | None = Field(
        default=None,
        description="Optional Chat Completions base URL, e.g. https://api.siliconflow.cn/v1",
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        description="Model id, optionally prefixed with provider, e.g. openai:gpt-4o-mini",
    )
    database_url: str | None = None
    workspace_dir: str = Field(
        default=".workspace",
        description="FilesystemBackend root for /workspace/ (relative to backend cwd)",
    )
    mcp_enabled: bool = Field(
        default=False,
        description="Load official filesystem + fetch MCP servers at startup",
    )
    allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
