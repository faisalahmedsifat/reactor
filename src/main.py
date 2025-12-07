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
    parser = argparse.ArgumentParser(description="Reactive Shell Agent")
    
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
    
    # --save is now default behavior, flag removed
    
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


def validate_config():
    """Validate that necessary configuration exists"""
    provider = os.getenv("LLM_PROVIDER", "anthropic")
    
    # Map provider to required env var
    required_vars = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "google": "GOOGLE_API_KEY",
    }
    
    # Ollama usually doesn't need a key, just a URL which defaults
    if provider == "ollama":
        return True
        
    env_var = required_vars.get(provider)
    if not env_var:
        return True # Unknown provider, let it fail downstream or assume custom setup
        
    if not os.getenv(env_var):
        print(f"\n❌ Error: Missing API Key for provider '{provider}'")
        print(f"👉 Please set {env_var} in your .env file")
        print(f"   OR pass it via CLI: --api-key <key>")
        print(f"\nExample: python src/main.py --provider {provider} --api-key sk-...\n")
        return False
        
    return True


def main():
    """Run the agent with TUI or CLI"""
    args = parse_args()
    configure_environment(args)
    
    # Auto-save if any config args are present
    if args.provider or args.model or args.api_key:
        save_configuration(args)
    
    if not validate_config():
        return 1

    # Check for CLI flag
    if args.cli:
        # Run CLI version
        from src.graph import run_simple_agent

        async def cli_loop():
            print(f"🤖 Reactive Shell Agent (CLI Mode)")
            print(f"   Provider: {os.getenv('LLM_PROVIDER', 'anthropic')}")
            print(f"   Model:    {os.getenv('LLM_MODEL', 'default')}")
            
            while True:
                try:
                    user_input = input("\n> ")
                    if user_input.lower() in ["exit", "quit"]:
                        break
                    if not user_input.strip():
                        continue
                    await run_simple_agent(user_input)
                except KeyboardInterrupt:
                    break

        return asyncio.run(cli_loop())
    else:
        # Run TUI version (default)
        from src.tui.app import run_tui

        run_tui()
        return 0


if __name__ == "__main__":
    sys.exit(main())
