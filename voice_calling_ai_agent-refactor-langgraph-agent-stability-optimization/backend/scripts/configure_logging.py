#!/usr/bin/env python3
"""
Log Level Configuration Helper
==============================

This script helps you quickly configure logging levels for the application.
It provides an interactive way to set log levels without manually editing .env files.

Usage:
    python scripts/configure_logging.py
    
    # Or set specific levels directly:
    python scripts/configure_logging.py --console INFO --app INFO --ai DEBUG

Author: Advanced AI Systems Team
"""

import os
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))


VALID_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

ENV_VARS = {
    "console": "LOG_LEVEL_CONSOLE",
    "app": "LOG_LEVEL_APP",
    "ai": "LOG_LEVEL_AI",
    "error": "LOG_LEVEL_ERROR",
    "root": "LOG_LEVEL_ROOT"
}


def get_env_file_path() -> Path:
    """Get the path to the .env file."""
    backend_dir = Path(__file__).parent.parent
    env_file = backend_dir / ".env"
    
    if not env_file.exists():
        env_example = backend_dir / ".env.example"
        if env_example.exists():
            print(f"⚠️  .env file not found. Creating from .env.example...")
            import shutil
            shutil.copy(env_example, env_file)
            print(f"✅ Created .env file at {env_file}")
        else:
            print(f"❌ Error: Neither .env nor .env.example found in {backend_dir}")
            sys.exit(1)
    
    return env_file


def read_env_file(env_file: Path) -> dict:
    """Read the .env file and return a dictionary of key-value pairs."""
    env_vars = {}
    
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Parse key=value
            if '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    return env_vars


def write_env_file(env_file: Path, env_vars: dict) -> None:
    """Write environment variables back to the .env file."""
    # Read the original file to preserve comments and structure
    with open(env_file, 'r') as f:
        lines = f.readlines()
    
    # Update or add the log level variables
    updated_lines = []
    updated_keys = set()
    
    for line in lines:
        stripped = line.strip()
        
        # Check if this line contains one of our env vars
        is_log_var = False
        for key in ENV_VARS.values():
            if stripped.startswith(f"{key}=") or stripped.startswith(f"# {key}="):
                is_log_var = True
                # Update the value
                if key in env_vars:
                    updated_lines.append(f"{key}={env_vars[key]}\n")
                    updated_keys.add(key)
                else:
                    updated_lines.append(line)
                break
        
        if not is_log_var:
            updated_lines.append(line)
    
    # Add any new variables that weren't in the file
    for key, value in env_vars.items():
        if key in ENV_VARS.values() and key not in updated_keys:
            updated_lines.append(f"{key}={value}\n")
    
    # Write back to file
    with open(env_file, 'w') as f:
        f.writelines(updated_lines)


def get_current_settings(env_file: Path) -> dict:
    """Get current log level settings."""
    env_vars = read_env_file(env_file)
    
    settings = {}
    for short_name, env_var in ENV_VARS.items():
        settings[short_name] = env_vars.get(env_var, "Not set")
    
    return settings


def print_current_settings(settings: dict) -> None:
    """Print current log level settings."""
    print("\n📊 Current Log Level Settings:")
    print("=" * 50)
    for name, value in settings.items():
        print(f"  {name.upper():10} ({ENV_VARS[name]:20}): {value}")
    print("=" * 50)


def validate_log_level(level: str) -> bool:
    """Validate that the log level is valid."""
    return level.upper() in VALID_LOG_LEVELS


def interactive_mode() -> dict:
    """Run interactive configuration mode."""
    print("\n🔧 Interactive Log Level Configuration")
    print("=" * 50)
    print("Available log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL")
    print("Press Enter to keep current value")
    print("=" * 50)
    
    new_settings = {}
    
    for short_name, env_var in ENV_VARS.items():
        while True:
            current = os.getenv(env_var, "Not set")
            prompt = f"\n{short_name.upper()} (current: {current}): "
            value = input(prompt).strip()
            
            if not value:
                # Keep current value
                break
            
            if validate_log_level(value):
                new_settings[env_var] = value.upper()
                break
            else:
                print(f"❌ Invalid log level: {value}")
                print(f"   Valid options: {', '.join(VALID_LOG_LEVELS)}")
    
    return new_settings


def apply_preset(preset_name: str) -> dict:
    """Apply a preset configuration."""
    presets = {
        "development": {
            "LOG_LEVEL_CONSOLE": "DEBUG",
            "LOG_LEVEL_APP": "INFO",
            "LOG_LEVEL_AI": "INFO",
            "LOG_LEVEL_ERROR": "ERROR",
            "LOG_LEVEL_ROOT": "DEBUG"
        },
        "production": {
            "LOG_LEVEL_CONSOLE": "INFO",
            "LOG_LEVEL_APP": "INFO",
            "LOG_LEVEL_AI": "INFO",
            "LOG_LEVEL_ERROR": "ERROR",
            "LOG_LEVEL_ROOT": "INFO"
        },
        "quiet": {
            "LOG_LEVEL_CONSOLE": "ERROR",
            "LOG_LEVEL_APP": "INFO",
            "LOG_LEVEL_AI": "INFO",
            "LOG_LEVEL_ERROR": "ERROR",
            "LOG_LEVEL_ROOT": "INFO"
        },
        "debug": {
            "LOG_LEVEL_CONSOLE": "DEBUG",
            "LOG_LEVEL_APP": "DEBUG",
            "LOG_LEVEL_AI": "DEBUG",
            "LOG_LEVEL_ERROR": "WARNING",
            "LOG_LEVEL_ROOT": "DEBUG"
        }
    }
    
    return presets.get(preset_name.lower(), {})


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Configure logging levels for the application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python scripts/configure_logging.py
  
  # Set specific levels
  python scripts/configure_logging.py --console INFO --app DEBUG
  
  # Apply preset
  python scripts/configure_logging.py --preset production
  
  # Show current settings
  python scripts/configure_logging.py --show
        """
    )
    
    parser.add_argument("--console", help="Set console log level")
    parser.add_argument("--app", help="Set application log level")
    parser.add_argument("--ai", help="Set AI agent log level")
    parser.add_argument("--error", help="Set error log level")
    parser.add_argument("--root", help="Set root log level")
    parser.add_argument("--preset", choices=["development", "production", "quiet", "debug"],
                       help="Apply a preset configuration")
    parser.add_argument("--show", action="store_true", help="Show current settings and exit")
    
    args = parser.parse_args()
    
    # Get .env file path
    env_file = get_env_file_path()
    
    # Show current settings
    current_settings = get_current_settings(env_file)
    print_current_settings(current_settings)
    
    if args.show:
        return
    
    # Determine what to do
    new_settings = {}
    
    if args.preset:
        # Apply preset
        new_settings = apply_preset(args.preset)
        print(f"\n✅ Applying preset: {args.preset}")
    elif any([args.console, args.app, args.ai, args.error, args.root]):
        # Apply command-line arguments
        if args.console:
            if validate_log_level(args.console):
                new_settings["LOG_LEVEL_CONSOLE"] = args.console.upper()
            else:
                print(f"❌ Invalid console log level: {args.console}")
                return
        
        if args.app:
            if validate_log_level(args.app):
                new_settings["LOG_LEVEL_APP"] = args.app.upper()
            else:
                print(f"❌ Invalid app log level: {args.app}")
                return
        
        if args.ai:
            if validate_log_level(args.ai):
                new_settings["LOG_LEVEL_AI"] = args.ai.upper()
            else:
                print(f"❌ Invalid AI log level: {args.ai}")
                return
        
        if args.error:
            if validate_log_level(args.error):
                new_settings["LOG_LEVEL_ERROR"] = args.error.upper()
            else:
                print(f"❌ Invalid error log level: {args.error}")
                return
        
        if args.root:
            if validate_log_level(args.root):
                new_settings["LOG_LEVEL_ROOT"] = args.root.upper()
            else:
                print(f"❌ Invalid root log level: {args.root}")
                return
    else:
        # Interactive mode
        new_settings = interactive_mode()
    
    if not new_settings:
        print("\n⚠️  No changes made.")
        return
    
    # Apply settings
    print("\n📝 Applying new settings...")
    write_env_file(env_file, new_settings)
    
    # Show updated settings
    updated_settings = get_current_settings(env_file)
    print_current_settings(updated_settings)
    
    print("\n✅ Log level configuration updated!")
    print("⚠️  Remember to restart your application for changes to take effect.")


if __name__ == "__main__":
    main()
