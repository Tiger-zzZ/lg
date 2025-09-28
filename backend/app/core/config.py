from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """应用配置"""

    # 基础配置
    PROJECT_NAME: str = "LG Platform"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # 安全配置
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # 数据库配置
    DATABASE_URL: str = "postgresql://lg_user:lg_password@localhost:5432/lg_platform"
    REDIS_URL: str = "redis://localhost:6378/0"

    # 向量数据库配置
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001

    # OpenAI配置 (用于嵌入和LLM)
    OPENAI_API_KEY: str = ""

    # CORS配置
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    ALLOWED_HOSTS: List[str] = ["*"]

    # 日志配置
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True


# 全局设置实例
settings = Settings()