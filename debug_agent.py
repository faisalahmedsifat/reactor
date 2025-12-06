
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
    print("🚀 Starting Debug Run with Thinking Node...")
    
    agent = create_simple_shell_agent()
    
    initial_state = {
        "messages": [HumanMessage(content="list the files in src directory")],
        "user_input": "list the files in src directory",
        "system_info": None
    }
    
    config = {"configurable": {"thread_id": "debug-2"}}
    
    print("Graph created. Starting stream...")
    async for event in agent.astream(initial_state, config, stream_mode="updates"):
        for node, output in event.items():
            print(f"\n>>> NODE: {node} <<<")
            if "messages" in output:
                msgs = output["messages"]
                if not isinstance(msgs, list):
                    msgs = [msgs]
                
                for m in msgs:
                    print(f"Type: {type(m).__name__}")
                    print(f"Content: {repr(m.content)}")
                    if hasattr(m, "tool_calls"):
                        print(f"Tool Calls: {m.tool_calls}")

if __name__ == "__main__":
    asyncio.run(main())
