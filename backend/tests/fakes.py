from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel


class FakeToolChatModel(FakeMessagesListChatModel):
    """FakeMessagesListChatModel plus bind_tools, which create_agent requires."""

    def bind_tools(self, tools, **kwargs):  # noqa: ARG002
        return self
