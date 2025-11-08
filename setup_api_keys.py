#!/usr/bin/env python3
"""
Configuration setup script for prompt injection testing.
This script helps you configure OpenAI and LangSmith API keys properly.
"""

import os
import sys
from getpass import getpass

def setup_api_keys():
    """Interactive setup for API keys."""
    print("🔧 API KEY CONFIGURATION SETUP")
    print("=" * 50)
    print("This script will help you configure API keys for prompt injection testing.")
    print()
    
    # Check current directory
    current_dir = os.getcwd()
    env_file = os.path.join(current_dir, '.env.development')
    
    if not os.path.exists(env_file):
        print(f"❌ Error: .env.development not found in {current_dir}")
        print("Please run this script from the project root directory.")
        return False
    
    print(f"📁 Found environment file: {env_file}")
    print()
    
    # Get API keys from user
    print("🔑 Please provide your API keys:")
    print()
    
    # OpenAI API Key
    openai_key = getpass("Enter your OpenAI API Key (sk-...): ").strip()
    if not openai_key.startswith('sk-'):
        print("⚠️  Warning: OpenAI API key should start with 'sk-'")
        confirm = input("Continue anyway? (y/n): ").strip().lower()
        if confirm != 'y':
            print("❌ Setup cancelled.")
            return False
    
    # LangSmith API Key
    print()
    langsmith_key = getpass("Enter your LangSmith API Key (ls__...): ").strip()
    if not langsmith_key.startswith('ls__'):
        print("⚠️  Warning: LangSmith API key should start with 'ls__'")
        confirm = input("Continue anyway? (y/n): ").strip().lower()
        if confirm != 'y':
            print("❌ Setup cancelled.")
            return False
    
    # Read current env file
    try:
        with open(env_file, 'r') as f:
            content = f.read()
        
        # Update API keys
        lines = content.split('\n')
        updated_lines = []
        
        for line in lines:
            if line.startswith('OPENAI_API_KEY='):
                updated_lines.append(f'OPENAI_API_KEY={openai_key}')
                print(f"✅ Updated OpenAI API key")
            elif line.startswith('LANGCHAIN_API_KEY='):
                updated_lines.append(f'LANGCHAIN_API_KEY={langsmith_key}')
                print(f"✅ Updated LangSmith API key")
            else:
                updated_lines.append(line)
        
        # Write back to file
        with open(env_file, 'w') as f:
            f.write('\n'.join(updated_lines))
        
        print()
        print("🎉 API keys configured successfully!")
        print()
        print("📋 You can now run the prompt injection tests:")
        print("   python simple_prompt_injection_test.py")
        print("   or")
        print("   cd src && python prompt_injection_evaluator.py")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating configuration: {e}")
        return False

def verify_configuration():
    """Verify that the configuration is working."""
    print("\n🔍 VERIFYING CONFIGURATION")
    print("=" * 30)
    
    try:
        # Add src to path
        sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
        
        # Set environment
        os.environ['APP_ENV'] = 'development'
        
        # Import config
        import config
        
        print(f"📊 OpenAI API Key: {'✅ SET' if config.OPENAI_API_KEY else '❌ NOT SET'}")
        print(f"📊 LangSmith API Key: {'✅ SET' if config.LANGCHAIN_API_KEY else '❌ NOT SET'}")
        print(f"📊 OpenAI Model: {config.OPENAI_MODEL}")
        print(f"📊 LangSmith Project: {config.LANGCHAIN_PROJECT}")
        print(f"📊 Prompt Injection Test: {'✅ ENABLED' if config.ENABLE_PROMPT_INJECTION_TEST else '❌ DISABLED'}")
        print(f"📊 Dataset: {config.PROMPT_INJECTION_DATASET}")
        
        if config.OPENAI_API_KEY and config.LANGCHAIN_API_KEY:
            print("\n🎉 Configuration looks good! Ready to run tests.")
            return True
        else:
            print("\n❌ Some API keys are missing. Please run setup again.")
            return False
            
    except Exception as e:
        print(f"\n❌ Error verifying configuration: {e}")
        return False

def main():
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] == 'verify':
        verify_configuration()
    else:
        if setup_api_keys():
            verify_configuration()

if __name__ == "__main__":
    main()