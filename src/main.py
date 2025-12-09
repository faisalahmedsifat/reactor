"""
Main entry point for the shell agent with TUI
"""

import asyncio
import os
import sys
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="ReACTOR")
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging and conversation history saving",
    )
    
    parser.add_argument(
        "--cli", 
        action="store_true", 
        help="Run in CLI mode instead of TUI"
    )
    
    parser.add_argument(
        "--provider", 
        choices=["anthropic", "openai", "google", "ollama"],
        help="Override LLM provider"
    )
    
    parser.add_argument(
        "--model", 
        help="Override LLM model name"
    )
    
    parser.add_argument(
        "--api-key", 
        help="Override API key for the selected provider"
    )
    
    # Headless mode
    parser.add_argument(
        "-p", "--prompt",
        help="Execute single prompt and exit (headless mode)"
    )
    
    # Agent and skill selection
    parser.add_argument(
        "--agent",
        help="Specify agent to use (e.g., web-researcher)"
    )
    
    parser.add_argument(
        "--skills",
        nargs="+",
        help="Specify skills to activate (e.g., frontend-dev backend-api)"
    )
    
    return parser.parse_args()


def save_configuration(args):
    """Save provided configuration to .env file"""
    # Only save if something was actually changed
    if not (args.provider or args.model or args.api_key):
        return

    updates = {}
    if args.provider:
        updates["LLM_PROVIDER"] = args.provider
    if args.model:
        updates["LLM_MODEL"] = args.model
    if args.api_key:
        # Determine variable name
        provider = args.provider or os.getenv("LLM_PROVIDER", "anthropic")
        mapping = {
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
            "google": "GOOGLE_API_KEY",
        }
        env_var = mapping.get(provider)
        if env_var:
            updates[env_var] = args.api_key

    # Read existing .env
    env_path = ".env"
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()

    # Update lines
    new_lines = []
    processed_keys = set()
    
    for line in lines:
        key = line.split("=")[0].strip()
        if key in updates:
            new_lines.append(f"{key}={updates[key]}\n")
            processed_keys.add(key)
        else:
            new_lines.append(line)
    
    # Append new keys
    for key, value in updates.items():
        if key not in processed_keys:
            if new_lines and not new_lines[-1].endswith("\n"):
                new_lines.append("\n")
            new_lines.append(f"{key}={value}\n")

    # Write back
    with open(env_path, "w") as f:
        f.writelines(new_lines)
    
    print("✅ Configuration updated in .env")


def configure_environment(args):
    """Inject configuration into environment variables"""
    if args.provider:
        os.environ["LLM_PROVIDER"] = args.provider
        
    if args.model:
        os.environ["LLM_MODEL"] = args.model
        
    if args.api_key:
        # Set the generic key based on provider
        provider = args.provider or os.getenv("LLM_PROVIDER", "anthropic")
        
        mapping = {
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
            "google": "GOOGLE_API_KEY",
        }
        
        # Determine variable name
        env_var = mapping.get(provider)
        if env_var:
            os.environ[env_var] = args.api_key

    # SMART DETECTION: If no provider is set in env, try to auto-detect from available keys
    if not os.getenv("LLM_PROVIDER"):
        if os.getenv("ANTHROPIC_API_KEY"):
            os.environ["LLM_PROVIDER"] = "anthropic"
        elif os.getenv("OPENAI_API_KEY"):
            os.environ["LLM_PROVIDER"] = "openai"
        elif os.getenv("GOOGLE_API_KEY"):
            os.environ["LLM_PROVIDER"] = "google"
    
    # MODEL ALIGNMENT: Ensure LLM_MODEL matches the provider if not explicitly set
    # This prevents the default "claude-sonnet..." from being sent to Google/OpenAI
    current_provider = os.getenv("LLM_PROVIDER")
    current_model = os.getenv("LLM_MODEL")

    # If model is not set, OR if we just switched connection info, let's pick a safe default
    # But we don't want to override if the user set it in .env. 
    # The issue is src/llm/client.py defaults to Claude if env var is missing.
    # to fix this, we MUST set LLM_MODEL in env if it is missing.
    
    if not current_model and current_provider:
        defaults = {
            "anthropic": "claude-4-5-sonnet-20240620",
            "openai": "gpt-4o",
            "google": "gemini-2.5-flash",
            "ollama": "llama3.1"
        }
        default_model = defaults.get(current_provider)
        if default_model:
            os.environ["LLM_MODEL"] = default_model


def validate_config():
    """Validate that necessary configuration exists"""
    # Check if provider is set at all first
    provider = os.getenv("LLM_PROVIDER")
    
    # If explicitly set (or auto-detected), validate it
    if provider:
        required_vars = {
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
            "google": "GOOGLE_API_KEY",
        }
        
        if provider == "ollama":
            return True
            
        env_var = required_vars.get(provider)
        if env_var and not os.getenv(env_var):
            print(f"\n❌ Error: Missing API Key for provider '{provider}'")
            print(f"👉 Please set {env_var} in your .env file")
            print(f"   OR pass it via CLI: --api-key <key>")
            return False
        return True

    # If NO provider set (and no auto-detect succeed), check default fallback (anthropic)
    # But wait, we want to be "open" to any.
    # If we are here, it means LLM_PROVIDER is unset AND no known keys were found in configure_environment.
    
    print("\n❌ Error: No LLM Provider configured.")
    print("👉 Please set one of the following in your .env file:")
    print("   - ANTHROPIC_API_KEY (for Claude)")
    print("   - OPENAI_API_KEY    (for GPT)")
    print("   - GOOGLE_API_KEY    (for Gemini)")
    print("\nOr start with specific provider:")
    print("   python src/main.py --provider google --api-key ...")
    return False


def main():
    """Run the agent with TUI or CLI"""
    args = parse_args()
    configure_environment(args)
    
    # Auto-save if any config args are present
    if args.provider or args.model or args.api_key:
        save_configuration(args)
    
    if not validate_config():
        return 1

    # HEADLESS MODE (-p flag)
    if args.prompt:
        from src.graph import run_simple_agent
        
        async def headless_execute():
            """Execute single prompt and exit"""
            print(f"🤖 ReACTOR (Headless Mode)")
            print(f"   Provider: {os.getenv('LLM_PROVIDER', 'anthropic')}")
            print(f"   Model: {os.getenv('LLM_MODEL', 'default')}")
            
            if args.agent:
                print(f"   Agent: {args.agent}")
            if args.skills:
                print(f"   Skills: {', '.join(args.skills)}")
            
            print(f"\n{'='*60}")
            print(f"Executing: {args.prompt}")
            print(f"{'='*60}\n")
            
            try:
                # Execute workflow with agent/skills
                await run_simple_agent(
                    args.prompt,
                    agent_name=args.agent,
                    skill_names=args.skills or []
                )
                return 0  # Success
            except Exception as e:
                print(f"\n❌ Error: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                return 1  # Error
        
        return asyncio.run(headless_execute())
    
    # INTERACTIVE CLI MODE (--cli flag)
    elif args.cli:
        # Run CLI version
        from src.graph import run_simple_agent

        async def cli_loop():
            print(f"🤖 ReACTOR (CLI Mode)")
            print(f"   Provider: {os.getenv('LLM_PROVIDER', 'anthropic')}")
            print(f"   Model:    {os.getenv('LLM_MODEL', 'default')}")
            
            if args.agent:
                print(f"   Agent: {args.agent}")
            if args.skills:
                print(f"   Skills: {', '.join(args.skills)}")
            
            while True:
                try:
                    user_input = input("\n> ")
                    if user_input.lower() in ["exit", "quit"]:
                        break
                    if not user_input.strip():
                        continue
                    await run_simple_agent(
                        user_input,
                        agent_name=args.agent,
                        skill_names=args.skills or []
                    )
                except KeyboardInterrupt:
                    break

        return asyncio.run(cli_loop())
    
    # TUI MODE (default)
    else:
        # Run TUI version (default)
        # Note: Agent and skill selection in TUI is done via slash commands
        from src.tui.app import run_tui

        run_tui(debug_mode=args.debug)
        return 0


if __name__ == "__main__":
    sys.exit(main())
