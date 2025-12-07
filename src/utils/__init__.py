"""
src/utils/__init__.py
Shared utilities for the agent
"""

import json
import re
import logging

logger = logging.getLogger(__name__)


def extract_json_from_text(text: str) -> dict:
    """
    Robustly extract JSON from text, handling markdown code blocks and preambles.

    Args:
        text (str): The raw text output from an LLM.

    Returns:
        dict: The parsed JSON object.

    Raises:
        json.JSONDecodeError: If no valid JSON can be found.
    """
    cleaned_text = text.strip()

    # 1. Try direct parse
    try:
        return json.loads(cleaned_text)
    except json.JSONDecodeError:
        pass

    # 2. Try extracting from markdown code blocks
    # Matchest ```json ... ``` or just ``` ... ```
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass  # Continue to regex strategy

    # 3. Regex search for object { ... }
    # Finds the first '{' and the last '}'
    start_idx = cleaned_text.find("{")
    end_idx = cleaned_text.rfind("}")

    if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
        potential_json = cleaned_text[start_idx : end_idx + 1]
        try:
            return json.loads(potential_json)
        except json.JSONDecodeError:
            pass

    # 4. Failed
    logger.error(f"Failed to extract JSON from text: {text[:200]}...")
    raise json.JSONDecodeError("Could not find valid JSON in text", text, 0)
