"""
src/llm/factory.py

Fixed factory that returns raw ChatModel for LangGraph
"""

import os
import asyncio
from typing import Literal, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage


class LLMFactory:
    """Factory for creating LLM clients for LangGraph"""

    @staticmethod
    def create_chat_model(
        provider: Literal["anthropic", "openai", "google", "ollama"],
        model: Optional[str] = None,
        **kwargs,
    ) -> BaseChatModel:
        """
        Create a raw ChatModel for use with LangGraph.

        LangGraph doesn't need ToolEnabledLLMClient wrapper - it handles
        tool calling natively through the graph.
        """

        configs = {
            "anthropic": {
                "model": model or "claude-sonnet-4-20250514",
                "api_key": os.getenv("ANTHROPIC_API_KEY"),
                "import": "langchain_anthropic",
                "class": "ChatAnthropic",
            },
            "openai": {
                "model": model or "gpt-4o",
                "api_key": os.getenv("OPENAI_API_KEY"),
                "import": "langchain_openai",
                "class": "ChatOpenAI",
            },
            "google": {
                "model": model or "gemini-2.5-flash",
                "api_key": os.getenv("GOOGLE_API_KEY"),
                "import": "langchain_google_genai",
                "class": "ChatGoogleGenerativeAI",
            },
            "ollama": {
                "model": model or "llama3.1",
                "base_url": kwargs.get("base_url", "http://localhost:11434"),
                "import": "langchain_ollama",
                "class": "ChatOllama",
            },
        }

        if provider not in configs:
            raise ValueError(f"Unknown provider: {provider}")

        config = configs[provider]

        # Dynamic import
        module = __import__(config["import"], fromlist=[config["class"]])
        chat_class = getattr(module, config["class"])

        # Build kwargs for the chat model
        chat_kwargs = {
            "model": config["model"],
            "temperature": kwargs.get("temperature", 0.0),
        }

        # Add API key with provider-specific parameter name
        if "api_key" in config:
            key_param = f"{provider}_api_key"
            chat_kwargs[key_param] = kwargs.get("api_key", config["api_key"])

        # Handle token limits (different parameter names by provider)
        if provider == "google":
            chat_kwargs["max_output_tokens"] = kwargs.get("max_tokens", 4096)
        else:
            chat_kwargs["max_tokens"] = kwargs.get("max_tokens", 4096)

        # Ollama-specific config
        if provider == "ollama":
            chat_kwargs["base_url"] = config["base_url"]

        # Create and return the chat model
        return chat_class(**chat_kwargs)

    @staticmethod
    def create_from_provider(
        provider: Literal["anthropic", "openai", "google", "ollama"],
        model: Optional[str] = None,
        **kwargs,
    ) -> BaseChatModel:
        """
        Alias for create_chat_model for backward compatibility.
        Now returns BaseChatModel instead of ToolEnabledLLMClient.
        """
        return LLMFactory.create_chat_model(provider, model, **kwargs)

    @staticmethod
    async def validate_connection(
        provider: str, model: Optional[str] = None, **kwargs
    ) -> tuple[bool, str]:
        """
        Validate LLM connection by sending a simple test message.

        Returns:
            tuple[bool, str]: (is_valid, error_message)
        """
        try:
            chat_model = LLMFactory.create_chat_model(provider, model, **kwargs)
            # Send a simple test message
            test_message = HumanMessage(content="Hello")
            await chat_model.ainvoke([test_message])
            return True, ""
        except Exception as e:
            error_msg = str(e)
            # Provide more user-friendly error messages
            if "Resource has been exhausted" in error_msg or "429" in error_msg:
                return (
                    False,
                    f"Rate limit exceeded for {provider}. Please try again later.",
                )
            elif (
                "authentication" in error_msg.lower()
                or "invalid api key" in error_msg.lower()
            ):
                return (
                    False,
                    f"Invalid API key for {provider}. Please check your credentials.",
                )
            elif "connection" in error_msg.lower() or "connect" in error_msg.lower():
                return (
                    False,
                    f"Cannot connect to {provider} service. Please check your network.",
                )
            else:
                return False, f"Connection error with {provider}: {error_msg}"
