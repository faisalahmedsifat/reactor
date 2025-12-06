"""
src/nodes/approval_nodes.py

Proper human-in-the-loop implementation
"""

from langgraph.types import interrupt
from langchain_core.messages import AIMessage, HumanMessage
from src.state import ShellAgentState


async def request_approval_node(state: ShellAgentState) -> ShellAgentState:
    """Node: Request human approval (proper interruption)"""
    
    plan = state["execution_plan"]
    idx = state["current_command_index"]
    current_cmd = plan.commands[idx]
    
    # Create approval message
    approval_msg = f"""🛑 APPROVAL REQUIRED

Command: {current_cmd.cmd}
Description: {current_cmd.description}
Risk Level: {current_cmd.risk_level}
Reversible: {current_cmd.reversible}

Reasoning: {current_cmd.reasoning}

Reply with:
- 'approve' to execute
- 'reject' to skip
- 'modify: <new_command>' to change command
"""
    
    state["messages"].append(AIMessage(content=approval_msg))
    
    # THIS IS THE KEY: LangGraph will pause execution here
    # and wait for user input via update_state()
    user_response = interrupt(approval_msg)
    
    # Process user response (this runs AFTER user responds)
    if user_response:
        response_lower = user_response.lower().strip()
        
        if response_lower == "approve":
            state["approved"] = True
            state["requires_approval"] = False
            state["messages"].append(
                HumanMessage(content="approve"),
                AIMessage(content="✓ Approved. Proceeding with execution...")
            )
        
        elif response_lower == "reject":
            state["approved"] = False
            state["current_command_index"] += 1  # Skip this command
            state["messages"].append(
                HumanMessage(content="reject"),
                AIMessage(content="✗ Rejected. Skipping command...")
            )
        
        elif response_lower.startswith("modify:"):
            new_cmd = response_lower.replace("modify:", "").strip()
            state["execution_plan"].commands[idx].cmd = new_cmd
            state["approved"] = True
            state["requires_approval"] = False
            state["messages"].append(
                HumanMessage(content=user_response),
                AIMessage(content=f"✓ Modified command to: {new_cmd}")
            )
    
    return state


# Usage example with proper streaming
async def run_with_approval():
    """Example: Run agent with human approval"""
    from src.graph import create_complete_shell_agent as create_shell_agent_graph
    
    graph = create_shell_agent_graph()
    
    initial_state = {
        "messages": [HumanMessage(content="Delete all .pyc files")],
        "user_input": "Delete all .pyc files",
        # ... other state
    }
    
    config = {"configurable": {"thread_id": "session-123"}}
    
    # Stream execution
    async for event in graph.astream(initial_state, config):
        for node_name, node_state in event.items():
            print(f"\n[{node_name}]")
            
            # Check if interrupted
            if "__interrupt__" in node_state:
                # Graph is waiting for approval
                print("\n⏸️  Execution paused for approval")
                print("Waiting for user input...")
                
                # Get user input (in CLI or web UI)
                user_input = input("Your response: ")
                
                # Resume execution with user input
                graph.update_state(
                    config,
                    {"approved": user_input.lower() == "approve"},
                    as_node="request_approval"
                )
                
                # Continue streaming
                continue