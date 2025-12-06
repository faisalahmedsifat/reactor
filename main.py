"""
Main entry point for the shell agent with TUI
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def main():
    """Run the agent with TUI or CLI"""
    
    # Check for API key
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ Error: GOOGLE_API_KEY not found in environment")
        print("Set it with: export GOOGLE_API_KEY='your-key-here'")
        return 1
    
    # Check for CLI flag
    if "--cli" in sys.argv:
        # Run CLI version
        from main_cli import main as cli_main
        return asyncio.run(cli_main())
    else:
        # Run TUI version (default)
        from src.tui.app import run_tui
        run_tui()
        return 0


if __name__ == "__main__":
    sys.exit(main())