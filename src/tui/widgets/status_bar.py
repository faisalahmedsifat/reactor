from textual.widgets import Static
from textual.reactive import reactive
import random

JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "There are 10 types of people in the world: those who understand binary, and those who don't.",
    "A SQL query walks into a bar, walks up to two tables and asks... 'Can I join you?'",
    "How many programmers does it take to change a light bulb? None, that's a hardware problem.",
    "Refactoring: The art of clearing code without adding features.",
    "Debugging: Being the detective in a crime movie where you are also the murderer.",
    "Code never lies, comments sometimes do.",
    "Real programmers count from 0.",
    "I'd tell you a UDP joke, but you might not get it.",
    "Knock, knock. Who's there? ... fast Java deployment.",
    "3 billion devices run Java, and not one of them is a toaster that works.",
    "Warning: Keyboard not found. Press F1 to continue.",
    "A programmer puts two glasses on his bedside table before going to sleep. A full one, in case he gets thirsty, and an empty one, in case he doesn't.",
    "Java is to JavaScript what car is to Carpet.",
    "Algorithm: Word used by programmers when they don't want to explain what they did.",
]

SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


class StatusBar(Static):
    """Bottom status bar with spinner and jokes"""

    agent_state = reactive("idle")
    status = reactive("Ready")
    execution_mode = reactive("sequential")

    # Internal state for spinner
    spinner_index = reactive(0)
    current_joke = reactive("")

    def on_mount(self):
        """Start spinner interval"""
        self.set_interval(0.1, self.advance_spinner)

    def advance_spinner(self):
        """Rotate spinner frame"""
        if self.agent_state == "thinking":
            self.spinner_index = (self.spinner_index + 1) % len(SPINNER_FRAMES)

    def watch_agent_state(self, old_state, new_state):
        """Update joke when entering thinking state"""
        if new_state == "thinking" and old_state != "thinking":
            self.current_joke = random.choice(JOKES)

    def render(self):
        mode_display = (
            "⏩ Sequential" if self.execution_mode == "sequential" else "⚡ Parallel"
        )

        if self.agent_state == "thinking":
            spinner = SPINNER_FRAMES[self.spinner_index]
            # Show spinner + joke + mode
            return f" {spinner} {self.current_joke} | State: {self.agent_state} | Mode: {mode_display} "
        else:
            # Show standard status
            return f" {self.status} | State: {self.agent_state} | Mode: {mode_display} "
