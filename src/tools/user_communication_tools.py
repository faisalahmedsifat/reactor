from langchain_core.tools import tool


def notify_user_and_end_task(
    message: str, summary: str = None, next_steps: list[str] = None
):
    """
    Sends a final message to the user, provides an optional summary and next steps,
    and signals the Agent framework to terminate the current task.

    This function is intended to be called when an agent has completed its objective
    and needs to communicate the outcome to the user before shutting down its current execution.

    Args:
        message (str): The primary message to be displayed to the user.
        summary (str, optional): A concise summary of the task completed.
        next_steps (list[str], optional): A list of suggested next actions or commands for the user.
    """
    print("\n--- Agent Notification ---")
    print(f"Message: {message}")
    if summary:
        print(f"Summary: {summary}")
    if next_steps:
        print("Next Steps:")
        for i, step in enumerate(next_steps):
            print(f"  {i+1}. {step}")
    print("--- End Agent Notification ---")

    # IMPORTANT META-INSTRUCTION FOR THE AGENT FRAMEWORK:
    # The Agent framework *must* interpret the successful return of this tool call
    # as a signal to immediately terminate the current agent's execution.
    # This Python function itself does not contain the termination logic,
    # but its invocation implies it.
