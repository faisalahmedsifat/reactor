import datetime
from pathlib import Path


class ConversationLogger:
    """Simple logger to track conversation history"""

    def __init__(self, log_file: str = "conversation_history.md"):
        self.log_file = Path(log_file)
        self._ensure_file()

    def _ensure_file(self):
        if not self.log_file.exists():
            with open(self.log_file, "w") as f:
                f.write("# Conversation History\n\n")

    def log_turn(self, role: str, content: str):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file, "a") as f:
            f.write(f"### {role.capitalize()} ({timestamp})\n")
            f.write(f"{content}\n\n")


# Global instance
chat_logger = ConversationLogger()
