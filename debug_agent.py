
import asyncio
import os
import sys
from pprint import pprint
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.append(os.getcwd())

from src.graph_simple import create_simple_shell_agent
from langchain_core.messages import HumanMessage

async def main():
    print("🚀 Starting Debug Run...")
    
    agent = create_simple_shell_agent()
    
    initial_state = {
        "messages": [HumanMessage(content="list the files in src directory")],
        "user_input": "list the files in src directory",
        "system_info": None
    }
    
    config = {"configurable": {"thread_id": "debug-1"}}
    
    async for event in agent.astream(initial_state, config, stream_mode="updates"):
        for node, output in event.items():
            print(f"\n--- NODE: {node} ---")
            if "messages" in output:
                msgs = output["messages"]
                if not isinstance(msgs, list):
                    msgs = [msgs]
                
                for m in msgs:
                    print(f"Type: {type(m).__name__}")
                    print(f"Content: {repr(m.content)}")
                    
                    if hasattr(m, "tool_calls") and m.tool_calls:
                        print("Tool Calls:")
                        pprint(m.tool_calls)
                    
                    if hasattr(m, "artifact") and m.artifact:
                        print("Artifact (Tool Output):")
                        # Truncate if too long
                        safe_artifact = str(m.artifact)
                        print(safe_artifact[:500] + "..." if len(safe_artifact) > 500 else safe_artifact)

if __name__ == "__main__":
    asyncio.run(main())
