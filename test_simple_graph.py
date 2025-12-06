"""
Test the simplified graph directly
"""
import asyncio
from src.graph_simple import run_simple_agent

async def main():
    # Test the simplified agent with a search query
    await run_simple_agent("where have I defined the graph for this project?")

if __name__ == "__main__":
    asyncio.run(main())
