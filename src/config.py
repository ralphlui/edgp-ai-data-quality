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

# LangSmith Configuration
LANGCHAIN_TRACING_V2: bool = os.getenv('LANGCHAIN_TRACING_V2', 'false').lower() == 'true'
LANGCHAIN_API_KEY: Optional[str] = os.getenv('LANGCHAIN_API_KEY')
LANGCHAIN_PROJECT: str = os.getenv('LANGCHAIN_PROJECT', f'edgp-ai-data-quality-{os.getenv("ENVIRONMENT", "development")}')

# Prompt Injection Testing Configuration
ENABLE_PROMPT_INJECTION_TEST: bool = os.getenv('ENABLE_PROMPT_INJECTION_TEST', 'false').lower() == 'true'
PROMPT_INJECTION_DATASET: str = os.getenv('PROMPT_INJECTION_DATASET', 'ds-impassioned-soda-62')

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

# Cache flags to prevent multiple initializations
_openai_initialized = False
_langsmith_initialized = False

def initialize_openai_config():
    """Initialize OpenAI configuration, retrieving API key from Secrets Manager if needed."""
    global OPENAI_API_KEY, _openai_initialized
    
    # Return early if already initialized
    if _openai_initialized:
        return
    
    if not OPENAI_API_KEY and USE_SECRETS_MANAGER:
        logger.info("🔐 THINK: OpenAI API key not found in environment, retrieving from AWS Secrets Manager...")
        try:
            # Import here to avoid circular import
            # Try different import strategies for different execution contexts
            try:
                from .secrets_manager import get_openai_api_key
            except ImportError:
                try:
                    from secrets_manager import get_openai_api_key  
                except ImportError:
                    # If running from root directory, add parent directory to path and import
                    import sys
                    import os
                    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    if parent_dir not in sys.path:
                        sys.path.insert(0, parent_dir)
                    from src.secrets_manager import get_openai_api_key
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
    
    # Mark as initialized to prevent duplicate calls
    _openai_initialized = True


def initialize_langsmith_config():
    """Initialize LangSmith configuration, retrieving API key from Secrets Manager if needed."""
    global LANGCHAIN_API_KEY, _langsmith_initialized
    
    # Return early if already initialized
    if _langsmith_initialized:
        return
    
    if not LANGCHAIN_API_KEY and USE_SECRETS_MANAGER:
        logger.info("🔐 THINK: LangSmith API key not found in environment, retrieving from AWS Secrets Manager...")
        try:
            # Import here to avoid circular import
            # Try different import strategies for different execution contexts
            try:
                from .secrets_manager import get_langsmith_api_key
            except ImportError:
                try:
                    from secrets_manager import get_langsmith_api_key
                except ImportError:
                    # If running from root directory, add parent directory to path and import
                    import sys
                    import os
                    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    if parent_dir not in sys.path:
                        sys.path.insert(0, parent_dir)
                    from src.secrets_manager import get_langsmith_api_key
            LANGCHAIN_API_KEY = get_langsmith_api_key()
            if LANGCHAIN_API_KEY:
                logger.info("✅ SUCCESS: LangSmith API key loaded from AWS Secrets Manager")
            else:
                logger.info("ℹ️ INFO: LangSmith API key not found in Secrets Manager (optional)")
        except ImportError as e:
            logger.error(f"❌ ERROR: Cannot import secrets_manager module: {e}")
        except Exception as e:
            logger.warning(f"⚠️ WARNING: Failed to initialize LangSmith API key from Secrets Manager: {e}")
    elif LANGCHAIN_API_KEY:
        logger.info("✅ SUCCESS: LangSmith API key loaded from environment variable")
    else:
        logger.info("ℹ️ INFO: LangSmith API key not configured (optional)")
    
    # Mark as initialized to prevent duplicate calls
    _langsmith_initialized = True


def validate_config():
    """Validate that required configuration values are set."""
    # Initialize OpenAI config first
    initialize_openai_config()
    
    # Initialize LangSmith config if tracing is enabled
    if LANGCHAIN_TRACING_V2:
        initialize_langsmith_config()
        # Set LangSmith environment variables for LangChain tracing
        if LANGCHAIN_API_KEY:
            os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
            logger.debug(f"🔐 DEBUG: Set LANGCHAIN_API_KEY environment variable: {LANGCHAIN_API_KEY[:10]}...")
        else:
            logger.warning("⚠️ WARNING: LANGCHAIN_API_KEY is None or empty, not setting environment variable")
        if LANGCHAIN_PROJECT:
            os.environ["LANGCHAIN_PROJECT"] = LANGCHAIN_PROJECT
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        logger.info(f"🔍 LangSmith tracing enabled for project: {LANGCHAIN_PROJECT}")
    
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
