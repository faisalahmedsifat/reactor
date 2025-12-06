"""
Message trimming utilities to manage conversation history and avoid rate limits.
"""
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage
from typing import List


def trim_messages(messages: List[BaseMessage], max_messages: int = 20, keep_system: bool = True) -> List[BaseMessage]:
    """
    Trim message history to avoid rate limits.
    
    Strategy:
    - Always keep system message (if exists)
    - Keep most recent max_messages
    - Ensure message pairs are complete (Human + AI)
    
    Args:
        messages: Full message history
        max_messages: Maximum number of messages to keep (default: 20)
        keep_system: Whether to always keep system message
    
    Returns:
        Trimmed message list
    """
    if len(messages) <= max_messages:
        return messages
    
    # Separate system message from rest
    system_msg = None
    other_messages = []
    
    for msg in messages:
        if isinstance(msg, SystemMessage) and keep_system and system_msg is None:
            system_msg = msg
        else:
            other_messages.append(msg)
    
    # Keep most recent messages
    trimmed = other_messages[-max_messages:]
    
    # Add system message back at start
    if system_msg:
        return [system_msg] + trimmed
    
    return trimmed


def trim_tool_results(messages: List[BaseMessage], max_chars: int = 2000) -> List[BaseMessage]:
    """
    Trim long tool result messages to reduce token usage.
    
    Args:
        messages: Message history
        max_chars: Maximum characters per tool result
    
    Returns:
        Messages with trimmed tool results
    """
    trimmed = []
    
    for msg in messages:
        if isinstance(msg, ToolMessage):
            content = str(msg.content)
            if len(content) > max_chars:
                # Truncate and add marker
                truncated = content[:max_chars] + f"\n\n... [Truncated {len(content) - max_chars} chars]"
                msg = ToolMessage(
                    content=truncated,
                    tool_call_id=msg.tool_call_id
                )
        trimmed.append(msg)
    
    return trimmed


def estimate_token_count(messages: List[BaseMessage]) -> int:
    """
    Rough estimate of token count (4 chars ≈ 1 token).
    
    Args:
        messages: Message list
    
    Returns:
        Estimated token count
    """
    total_chars = sum(len(str(msg.content)) for msg in messages)
    return total_chars // 4
