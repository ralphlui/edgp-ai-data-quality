"""
Configuration settings for the Customer Record Deduplication AI Agent.
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv

# Set up basic logging for configuration loading
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment-specific .env file based on APP_ENV
app_env = os.getenv('APP_ENV', 'development')
env_file_map = {
    'development': '.env.development',
    'sit': '.env.sit', 
    'prd': '.env.production'
}

env_file = env_file_map.get(app_env, '.env.development')
print(f"🤖 AGENT INIT: Loading environment configuration from '{env_file}' for APP_ENV='{app_env}'")
load_dotenv(env_file)


# AWS Configuration
AWS_ACCESS_KEY_ID: Optional[str] = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION: str = os.getenv('AWS_REGION', 'ap-southeast-1')

# SQS Configuration
WORKFLOW_DEDUPLICATION_REQUEST_SQS_URL: Optional[str] = os.getenv('WORKFLOW_DEDUPLICATION_REQUEST_SQS_URL')
WORKFLOW_DEDUPLICATION_RESPONSE_SQS_URL: Optional[str] = os.getenv('WORKFLOW_DEDUPLICATION_RESPONSE_SQS_URL')

# DynamoDB Configuration
DYNAMODB_TABLE_NAME: str = os.getenv('DYNAMODB_TABLE_NAME', 'customerSIT')
BLOCK_KEY_GSI_NAME: str = os.getenv('BLOCK_KEY_GSI_NAME', 'block_key-index')

# OpenAI Configuration
# Try to get from environment first (for local development), fallback to Secrets Manager
OPENAI_API_KEY: Optional[str] = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL: str = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

# Secrets Manager Configuration
USE_SECRETS_MANAGER: bool = os.getenv('USE_SECRETS_MANAGER', 'true').lower() == 'true'

# Deduplication Configuration
SIMILARITY_THRESHOLD: float = float(os.getenv('SIMILARITY_THRESHOLD', '0.85'))
FUZZY_SIMILARITY_THRESHOLD_HIGH: float = float(os.getenv('FUZZY_SIMILARITY_THRESHOLD_HIGH', '85.0'))
FUZZY_SIMILARITY_THRESHOLD_LOW: float = float(os.getenv('FUZZY_SIMILARITY_THRESHOLD_LOW', '60.0'))
GPT_CONFIDENCE_THRESHOLD: float = float(os.getenv('GPT_CONFIDENCE_THRESHOLD', '0.75'))

# Logging Configuration
LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')

# Field Weights for Similarity Calculation
FIELD_WEIGHTS = {
    'firstname': 0.20,
    'lastname': 0.20,
    'email': 0.20,
    'phone': 0.15,
    'address': 0.10,
    'organization_id': 0.10,
    'country': 0.03,
    'gender': 0.02
}

def initialize_openai_config():
    """Initialize OpenAI configuration, retrieving API key from Secrets Manager if needed."""
    global OPENAI_API_KEY
    
    if not OPENAI_API_KEY and USE_SECRETS_MANAGER:
        logger.info("🔐 THINK: OpenAI API key not found in environment, retrieving from AWS Secrets Manager...")
        try:
            # Import here to avoid circular import
            from secrets_manager import get_openai_api_key
            OPENAI_API_KEY = get_openai_api_key()
            if OPENAI_API_KEY:
                logger.info("✅ SUCCESS: OpenAI API key loaded from AWS Secrets Manager")
            else:
                logger.error("❌ ERROR: Failed to retrieve OpenAI API key from Secrets Manager")
        except ImportError as e:
            logger.error(f"❌ ERROR: Cannot import secrets_manager module: {e}")
        except Exception as e:
            logger.error(f"❌ ERROR: Failed to initialize OpenAI API key from Secrets Manager: {e}")
    elif OPENAI_API_KEY:
        logger.info("✅ SUCCESS: OpenAI API key loaded from environment variable")
    else:
        logger.warning("⚠️ WARNING: OpenAI API key not configured")


def validate_config():
    """Validate that required configuration values are set."""
    # Initialize OpenAI config first
    initialize_openai_config()
    
    required_vars = [
        ('AWS_ACCESS_KEY_ID', AWS_ACCESS_KEY_ID),
        ('AWS_SECRET_ACCESS_KEY', AWS_SECRET_ACCESS_KEY),
        ('WORKFLOW_DEDUPLICATION_REQUEST_SQS_URL', WORKFLOW_DEDUPLICATION_REQUEST_SQS_URL),
        ('WORKFLOW_DEDUPLICATION_RESPONSE_SQS_URL', WORKFLOW_DEDUPLICATION_RESPONSE_SQS_URL),
        ('OPENAI_API_KEY', OPENAI_API_KEY),
    ]
    
    missing_vars = [name for name, value in required_vars if not value]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
