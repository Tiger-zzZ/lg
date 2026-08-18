from app.config import Settings
from app.models import resolve_model_id


def test_resolve_model_id_adds_openai_prefix():
    assert resolve_model_id(Settings(openai_model="gpt-4o-mini")) == "openai:gpt-4o-mini"


def test_resolve_model_id_keeps_provider_prefix():
    assert (
        resolve_model_id(Settings(openai_model="openai:deepseek-chat"))
        == "openai:deepseek-chat"
    )
