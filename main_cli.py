"""
Main entry point for the shell agent
"""

import asyncio
import os
"""
Main entry point for the shell agent
"""

import asyncio
import os
from dotenv import load_dotenv
from src.graph import run_agent_interactive

# Load environment variables
load_dotenv()

async def main():
    """Run the agent"""
    
    # Check for API key
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ Error: GOOGLE_API_KEY not found in environment")
        print("Set it with: export GOOGLE_API_KEY='your-key-here'")
        return
    
    print("🤖 Shell Automation Agent")
    print("=" * 60)
    print("Type 'exit' or 'quit' to stop\n")
    
    # Continuous loop
    while True:
        try:
            # Get user input
            user_request = input("\nWhat would you like me to do? ")
            
            # Check for exit commands
            if user_request.strip().lower() in ['exit', 'quit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            if not user_request.strip():
                print("No request provided. Please try again.")
                continue
            
            # Run agent
            await run_agent_interactive(user_request)
            
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            print("\n↻ Ready for next command...")

if __name__ == "__main__":
    asyncio.run(main())