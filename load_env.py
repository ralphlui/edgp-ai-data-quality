#!/usr/bin/env python3
"""
Environment loader for EDGP AI Data Quality Engine.
Usage: python load_env.py [development|sit|production]
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv


def load_environment(env_name: str = None):
    """
    Load environment configuration based on environment name.
    
    Args:
        env_name: Environment name (development, sit, production)
                 If None, tries to get from ENV_NAME environment variable
                 If still None, defaults to development
    """
    # Get environment name
    if env_name is None:
        env_name = os.getenv('ENV_NAME', 'development')
    
    # Validate environment name
    valid_envs = ['development', 'sit', 'production']
    if env_name not in valid_envs:
        print(f"Error: Invalid environment '{env_name}'. Must be one of: {valid_envs}")
        sys.exit(1)
    
    # Get project root directory
    project_root = Path(__file__).parent
    env_file = project_root / f".env.{env_name}"
    
    # Check if environment file exists
    if not env_file.exists():
        print(f"Error: Environment file '{env_file}' not found")
        sys.exit(1)
    
    # Load environment file
    load_dotenv(env_file)
    print(f"✅ Loaded environment: {env_name}")
    print(f"📁 Environment file: {env_file}")
    print(f"🌍 Environment: {os.getenv('ENVIRONMENT', 'unknown')}")
    print(f"📊 Log Level: {os.getenv('LOG_LEVEL', 'INFO')}")
    print(f"🏷️  DynamoDB Table: {os.getenv('DYNAMODB_TABLE_NAME', 'unknown')}")
    
    return env_name


def main():
    """Main function to load environment from command line."""
    if len(sys.argv) > 2:
        print("Usage: python load_env.py [development|sit|production]")
        sys.exit(1)
    
    env_name = sys.argv[1] if len(sys.argv) == 2 else None
    load_environment(env_name)


if __name__ == "__main__":
    main()
