"""
Entry point wrapper for the reactor CLI.
This allows the entry point to be in src/ while keeping main.py at root.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import and run main
from main import main

if __name__ == "__main__":
    sys.exit(main())
