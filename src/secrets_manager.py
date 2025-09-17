"""
AWS Secrets Manager service for secure configuration management.
"""

import json
import logging
import boto3
from botocore.exceptions import ClientError
from typing import Optional, Dict, Any
import config

logger = logging.getLogger(__name__)


class SecretsManagerService:
    """Service for retrieving secrets from AWS Secrets Manager."""
    
    def __init__(self):
        """Initialize Secrets Manager client."""
        try:
            self.client = boto3.client(
                'secretsmanager',
                region_name=config.AWS_REGION,
                aws_access_key_id=config.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY
            )
            logger.info("🔐 AGENT INIT: AWS Secrets Manager client initialized successfully")
        except Exception as e:
            logger.error(f"❌ ERROR: Failed to initialize Secrets Manager client: {e}")
            raise
    
    def get_secret(self, secret_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a secret from AWS Secrets Manager.
        
        Args:
            secret_name: Name or ARN of the secret to retrieve
            
        Returns:
            Dictionary containing the secret values, or None if failed
        """
        try:
            logger.debug(f"🔐 THINK: Retrieving secret from AWS Secrets Manager: {secret_name}")
            
            response = self.client.get_secret_value(SecretId=secret_name)
            
            # Parse the secret string as JSON
            secret_dict = json.loads(response['SecretString'])
            
            logger.info(f"✅ SUCCESS: Successfully retrieved secret: {secret_name}")
            logger.debug(f"🔐 OBSERVE: Secret contains {len(secret_dict)} key(s)")
            
            return secret_dict
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                logger.error(f"❌ ERROR: Secret not found: {secret_name}")
            elif error_code == 'InvalidRequestException':
                logger.error(f"❌ ERROR: Invalid request for secret: {secret_name}")
            elif error_code == 'InvalidParameterException':
                logger.error(f"❌ ERROR: Invalid parameter for secret: {secret_name}")
            elif error_code == 'DecryptionFailureException':
                logger.error(f"❌ ERROR: Cannot decrypt secret: {secret_name}")
            elif error_code == 'InternalServiceErrorException':
                logger.error(f"❌ ERROR: Internal service error retrieving secret: {secret_name}")
            else:
                logger.error(f"❌ ERROR: Unexpected error retrieving secret {secret_name}: {e}")
            return None
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ ERROR: Failed to parse secret as JSON: {e}")
            return None
            
        except Exception as e:
            logger.error(f"❌ ERROR: Unexpected error retrieving secret {secret_name}: {e}")
            return None
    
    def get_secret_value(self, secret_name: str, key: str) -> Optional[str]:
        """
        Retrieve a specific key value from a secret.
        
        Args:
            secret_name: Name or ARN of the secret
            key: The key within the secret to retrieve
            
        Returns:
            The secret value as string, or None if not found
        """
        secret_dict = self.get_secret(secret_name)
        if secret_dict and key in secret_dict:
            logger.debug(f"🔐 SUCCESS: Retrieved key '{key}' from secret '{secret_name}'")
            return secret_dict[key]
        else:
            logger.error(f"❌ ERROR: Key '{key}' not found in secret '{secret_name}'")
            return None


def get_openai_api_key() -> Optional[str]:
    """
    Get OpenAI API key from AWS Secrets Manager based on environment.
    
    Returns:
        OpenAI API key string, or None if retrieval fails
    """
    # Determine secret name based on environment
    app_env = config.app_env.lower()
    
    if app_env in ['development', 'sit']:
        secret_name = 'sit/edgp/secret'
    elif app_env in ['prd', 'production']:
        secret_name = 'prod/edgp/secret'
    else:
        logger.warning(f"⚠️ WARNING: Unknown environment '{app_env}', defaulting to SIT secret")
        secret_name = 'sit/edgp/secret'
    
    logger.info(f"🔐 THINK: Retrieving OpenAI API key from secret '{secret_name}' for environment '{app_env}'")
    
    try:
        secrets_service = SecretsManagerService()
        api_key = secrets_service.get_secret_value(secret_name, 'ai_agent_api_key')
        
        if api_key:
            logger.info("✅ SUCCESS: OpenAI API key retrieved from AWS Secrets Manager")
            # Mask the key in logs for security
            masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
            logger.debug(f"🔐 OBSERVE: API key retrieved: {masked_key}")
            return api_key
        else:
            logger.error("❌ ERROR: Failed to retrieve OpenAI API key from Secrets Manager")
            return None
            
    except Exception as e:
        logger.error(f"❌ ERROR: Exception while retrieving API key: {e}")
        return None