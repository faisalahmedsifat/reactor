"""
Conversation compaction utilities.
Automatically summarizes long conversations to manage token usage.
"""
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from typing import List, Dict
from src.nodes.llm_nodes import get_llm_client


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


async def compact_conversation(messages: List[BaseMessage], target_tokens: int = 10000) -> List[BaseMessage]:
    """
    Compact a long conversation by summarizing it.
    
    Strategy:
    1. Keep system message
    2. Summarize old messages into a context summary
    3. Keep recent N messages intact
    4. Return: [SystemMessage, ContextSummary, Recent Messages...]
    
    Args:
        messages: Full message history
        target_tokens: Target token count after compaction (default: 10k)
    
    Returns:
        Compacted message list with summary
    """
    if estimate_token_count(messages) < target_tokens:
        return messages
    
    print(f"[COMPACTION] Starting conversation compaction...")
    
    # Separate system message
    system_msg = None
    other_messages = []
    
    for msg in messages:
        if isinstance(msg, SystemMessage) and system_msg is None:
            system_msg = msg
        else:
            other_messages.append(msg)
    
    # Keep recent 10 messages intact
    recent_messages = other_messages[-10:]
    messages_to_summarize = other_messages[:-10]
    
    if not messages_to_summarize:
        return messages
    
    # Create summary prompt
    llm = get_llm_client()
    from src.prompts import get_prompt
    
    summary_prompt = get_prompt("compaction.summarize") + f"\n\nConversation to summarize:\n{format_messages_for_summary(messages_to_summarize)}"
    
    try:
        summary_response = await llm.ainvoke([HumanMessage(content=summary_prompt)])
        summary_text = summary_response.content
        
        # Create context message
        context_msg = AIMessage(content=f"""📝 **Conversation Summary (Auto-Compacted)**

{summary_text}

---
*Recent conversation continues below...*""")
        
        # Build compacted history
        compacted = []
        if system_msg:
            compacted.append(system_msg)
        compacted.append(context_msg)
        compacted.extend(recent_messages)
        
        original_tokens = estimate_token_count(messages)
        new_tokens = estimate_token_count(compacted)
        
        print(f"[COMPACTION] Reduced {original_tokens:,} → {new_tokens:,} tokens (saved {original_tokens - new_tokens:,})")
        
        return compacted
        
    except Exception as e:
        print(f"[COMPACTION] Error during compaction: {e}")
        return messages


def format_messages_for_summary(messages: List[BaseMessage]) -> str:
    """Format messages for summarization"""
    formatted = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            formatted.append(f"User: {msg.content[:500]}")
        elif isinstance(msg, AIMessage):
            formatted.append(f"Agent: {msg.content[:500]}")
    return "\n\n".join(formatted)


def should_compact(messages: List[BaseMessage], threshold_tokens: int = 50000) -> bool:
    """
    Check if conversation should be compacted.
    
    Args:
        messages: Message list
        threshold_tokens: Token threshold to trigger compaction (default: 50k)
    
    Returns:
        True if should compact
    """
    current_tokens = estimate_token_count(messages)
    return current_tokens > threshold_tokens
