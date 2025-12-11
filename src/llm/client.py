"""
src/llm/client.py

Provides the LLM client instance for the application.
"""

from functools import lru_cache
from langchain_core.language_models.chat_models import BaseChatModel
from src.llm.factory import LLMFactory
import os


@lru_cache(maxsize=1)
def get_llm_client() -> BaseChatModel:
    """
    Lazy load LLM client - cached for performance.
    Returns raw BaseChatModel for LangGraph.

    Configuration is read from environment variables:
    - LLM_PROVIDER (default: anthropic)
    - LLM_MODEL (default: claude-sonnet-4-20250514)
    """
    provider = os.getenv("LLM_PROVIDER", "anthropic")
    model = os.getenv("LLM_MODEL", "claude-sonnet-4-20250514")

    # Use factory to create the model
    return LLMFactory.create_chat_model(provider, model)
