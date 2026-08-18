from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel

from app.config import Settings, get_settings


def resolve_model_id(settings: Settings) -> str:
    model = (settings.openai_model or "gpt-4o-mini").strip()
    if ":" in model:
        return model
    return f"openai:{model}"


def get_chat_model(settings: Settings | None = None) -> BaseChatModel:
    """OpenAI-compatible Chat Completions via langchain.chat_models.init_chat_model.

    Config (backend/.env):
      OPENAI_API_KEY   required for real calls
      OPENAI_BASE_URL  optional; SiliconFlow / DeepSeek / ModelScope 等兼容网关
      OPENAI_MODEL     `gpt-4o-mini` or `openai:gpt-4o-mini`
    """
    settings = settings or get_settings()
    kwargs: dict = {
        "api_key": settings.openai_api_key or "not-set",
        "temperature": 0,
    }
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return init_chat_model(resolve_model_id(settings), **kwargs)
