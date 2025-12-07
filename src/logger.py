import datetime
from pathlib import Path


class ConversationLogger:
    """Simple logger to track conversation history"""

    def __init__(self, log_file: str = None):
        if log_file:
            self.log_file = Path(log_file)
            self._ensure_file()
        else:
            self.log_file = None

    def _ensure_file(self):
        if self.log_file and not self.log_file.exists():
            with open(self.log_file, "w") as f:
                f.write("# Conversation History\n\n")

    def log_turn(self, role: str, content: str):
        if self.log_file:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.log_file, "a") as f:
                f.write(f"### {role.capitalize()} ({timestamp})\n")
                f.write(f"{content}\n\n")


# Global instance
chat_logger = ConversationLogger(log_file=None)
