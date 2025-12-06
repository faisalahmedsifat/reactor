from abc import ABC, abstractmethod
import json
import re
import structlog

logger = structlog.get_logger()


class BaseLLMClient(ABC):
    """Abstract LLM client - only responsible for invocation"""
    
    @abstractmethod
    async def invoke(self, system_prompt: str, user_prompt: str) -> str:
        """Invoke LLM and return raw response"""
        pass
    
    def extract_json(self, content: str) -> str:
        """Extract JSON from response"""
        content = content.strip()
        
        if "```json" in content:
            match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
            if match:
                return match.group(1)
        
        if "```" in content:
            match = re.search(r'```\s*(\{.*?\})\s*```', content, re.DOTALL)
            if match:
                return match.group(1)
        
        if "{" in content:
            start = content.index("{")
            depth = 0
            for i, char in enumerate(content[start:], start):
                if char == "{": depth += 1
                elif char == "}": depth -= 1; 
                if depth == 0: return content[start:i+1]
        
        return content
    
    def parse_json(self, content: str, model_class: type):
        """Parse and validate JSON"""
        try:
            json_str = self.extract_json(content)
            data = json.loads(json_str)
            return model_class(**data)
        except Exception as e:
            logger.error("json_parse_failed", error=str(e))
            raise