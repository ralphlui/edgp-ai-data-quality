#!/usr/bin/env python3
"""
Demo script to test AWS Secrets Manager integration.
"""

import os
import sys

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src import config
from src.secrets_manager import get_openai_api_key


def main():
    """Demonstrate Secrets Manager integration."""
    print("🤖 EDGP AI Data Quality Engine - Secrets Manager Demo")
    print("=" * 60)
    
    # Display current environment
    print(f"📍 Environment: {config.app_env}")
    print(f"🔧 Use Secrets Manager: {config.USE_SECRETS_MANAGER}")
    print(f"🌍 AWS Region: {config.AWS_REGION}")
    
    # Check current OpenAI API key configuration
    print(f"\n📋 Current OpenAI API Key from env file: {'SET' if config.OPENAI_API_KEY else 'NOT SET'}")
    
    if config.USE_SECRETS_MANAGER and not config.OPENAI_API_KEY:
        print("\n🔐 Attempting to retrieve OpenAI API key from AWS Secrets Manager...")
        
        try:
            # Initialize OpenAI configuration (this will trigger Secrets Manager lookup)
            config.initialize_openai_config()
            
            if config.OPENAI_API_KEY:
                # Mask the key for security
                masked_key = f"{config.OPENAI_API_KEY[:8]}...{config.OPENAI_API_KEY[-4:]}" if len(config.OPENAI_API_KEY) > 12 else "***"
                print(f"✅ SUCCESS: API key retrieved: {masked_key}")
                print(f"🎯 OpenAI Model: {config.OPENAI_MODEL}")
            else:
                print("❌ FAILED: Could not retrieve API key from Secrets Manager")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    elif config.OPENAI_API_KEY:
        print("ℹ️  Using OpenAI API key from environment variable")
        masked_key = f"{config.OPENAI_API_KEY[:8]}...{config.OPENAI_API_KEY[-4:]}" if len(config.OPENAI_API_KEY) > 12 else "***"
        print(f"🔑 API Key: {masked_key}")
    
    else:
        print("⚠️  OpenAI API key not configured and Secrets Manager is disabled")
    
    print("\n📊 Configuration Summary:")
    print(f"   Environment: {config.app_env}")
    print(f"   AWS Region: {config.AWS_REGION}")
    print(f"   DynamoDB Table: {config.DYNAMODB_TABLE_NAME}")
    print(f"   OpenAI Model: {config.OPENAI_MODEL}")
    print(f"   Use Secrets Manager: {config.USE_SECRETS_MANAGER}")
    print(f"   GPT Confidence Threshold: {config.GPT_CONFIDENCE_THRESHOLD}")
    
    print("\n🔍 Environment-specific secret mapping:")
    if config.app_env.lower() in ['development', 'sit']:
        print("   Secret Name: sit/edgp/secret")
        print("   Secret ARN: arn:aws:secretsmanager:ap-southeast-1:292344568326:secret:sit/edgp/secret-xcCVSV")
    elif config.app_env.lower() in ['prd', 'production']:
        print("   Secret Name: prod/edgp/secret")
        print("   Secret ARN: arn:aws:secretsmanager:ap-southeast-1:292344568326:secret:prod/edgp/secret-LbQL87")
    
    print("   Secret Key: ai_agent_api_key")
    
    print("\n✨ Demo completed!")


if __name__ == "__main__":
    main()