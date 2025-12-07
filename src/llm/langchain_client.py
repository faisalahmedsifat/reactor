from .base import BaseLLMClient
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.language_models.chat_models import BaseChatModel


class LangChainLLMClient(BaseLLMClient):
    """LangChain wrapper - pure invocation logic"""

    def __init__(self, chat_model: BaseChatModel):
        self.chat_model = chat_model

    async def invoke(self, system_prompt: str, user_prompt: str) -> str:
        """Invoke LangChain model"""
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        response = await self.chat_model.ainvoke(messages)
        return response.content
