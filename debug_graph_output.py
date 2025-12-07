
import asyncio
import os
import sys
from langchain_core.messages import HumanMessage

# Add src to path
sys.path.append(os.getcwd())

from src.graph import create_simple_shell_agent

async def main():
    print("🚀 Starting Debug Graph Output...")
    
    graph = create_simple_shell_agent()
    
    initial_state = {
        "messages": [HumanMessage(content="What is in the current directory?")],
        "user_input": "What is in the current directory?",
    }
    
    config = {"configurable": {"thread_id": "debug-test"}, "recursion_limit": 10}
    
    async for event in graph.astream(initial_state, config, stream_mode="updates"):
        for node_name, node_output in event.items():
            print(f"\n{'='*40}")
            print(f"NODE: {node_name}")
            print(f"{'='*40}")
            print(f"Type: {type(node_output)}")
            print(f"Keys: {node_output.keys()}")
            
            if "messages" in node_output:
                msgs = node_output["messages"]
                print(f"Messages count: {len(msgs)}")
                if msgs:
                    last_msg = msgs[-1]
                    print(f"Last Msg Type: {type(last_msg)}")
                    print(f"Last Msg Content Type: {type(last_msg.content)}")
                    print(f"Last Msg Content: {last_msg.content}")
                    
                    # Simulate bridge parsing
                    content_text = ""
                    if hasattr(last_msg, "content"):
                        if isinstance(last_msg.content, str):
                            content_text = last_msg.content
                        elif isinstance(last_msg.content, list):
                            content_text = str(last_msg.content) # Simplified
                    
                    print(f"\n[BRIDGE PARSER SIMULATION]: '{content_text}'")

if __name__ == "__main__":
    asyncio.run(main())
