"""
Tests for AWS Secrets Manager integration.
"""

import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import Mock, patch, MagicMock
import json
from botocore.exceptions import ClientError

from src.secrets_manager import SecretsManagerService, get_openai_api_key


class TestSecretsManagerService:
    """Test cases for Secrets Manager service."""
    
    @pytest.fixture
    def mock_secrets_client(self):
        """Create a mock Secrets Manager client."""
        return Mock()
    
    @pytest.fixture
    def secrets_service(self, mock_secrets_client):
        """Create a Secrets Manager service with mocked client."""
        with patch('src.secrets_manager.boto3.client', return_value=mock_secrets_client):
            service = SecretsManagerService()
            service.client = mock_secrets_client
            return service
    
    def test_get_secret_success(self, secrets_service):
        """Test successful secret retrieval."""
        # Mock response
        mock_response = {
            'SecretString': json.dumps({
                'ai_agent_api_key': 'sk-test123456789',
                'database_password': 'db_secret'
            })
        }
        secrets_service.client.get_secret_value.return_value = mock_response
        
        # Call the method
        result = secrets_service.get_secret('test/secret')
        
        # Verify
        assert result is not None
        assert result['ai_agent_api_key'] == 'sk-test123456789'
        assert result['database_password'] == 'db_secret'
        secrets_service.client.get_secret_value.assert_called_once_with(SecretId='test/secret')
    
    def test_get_secret_not_found(self, secrets_service):
        """Test secret not found error."""
        # Mock client error
        error = ClientError(
            error_response={'Error': {'Code': 'ResourceNotFoundException'}},
            operation_name='GetSecretValue'
        )
        secrets_service.client.get_secret_value.side_effect = error
        
        # Call the method
        result = secrets_service.get_secret('nonexistent/secret')
        
        # Verify
        assert result is None
    
    def test_get_secret_invalid_json(self, secrets_service):
        """Test invalid JSON in secret."""
        # Mock response with invalid JSON
        mock_response = {
            'SecretString': 'invalid json content'
        }
        secrets_service.client.get_secret_value.return_value = mock_response
        
        # Call the method
        result = secrets_service.get_secret('test/secret')
        
        # Verify
        assert result is None
    
    def test_get_secret_value_success(self, secrets_service):
        """Test successful retrieval of specific secret key."""
        # Mock the get_secret method
        secret_dict = {
            'ai_agent_api_key': 'sk-test123456789',
            'other_key': 'other_value'
        }
        secrets_service.get_secret = Mock(return_value=secret_dict)
        
        # Call the method
        result = secrets_service.get_secret_value('test/secret', 'ai_agent_api_key')
        
        # Verify
        assert result == 'sk-test123456789'
        secrets_service.get_secret.assert_called_once_with('test/secret')
    
    def test_get_secret_value_key_not_found(self, secrets_service):
        """Test key not found in secret."""
        # Mock the get_secret method
        secret_dict = {
            'other_key': 'other_value'
        }
        secrets_service.get_secret = Mock(return_value=secret_dict)
        
        # Call the method
        result = secrets_service.get_secret_value('test/secret', 'nonexistent_key')
        
        # Verify
        assert result is None
    
    @patch('src.secrets_manager.config')
    def test_get_openai_api_key_development(self, mock_config):
        """Test OpenAI API key retrieval for development environment."""
        # Mock config
        mock_config.app_env = 'development'
        
        # Mock SecretsManagerService
        with patch('src.secrets_manager.SecretsManagerService') as mock_service_class:
            mock_service = Mock()
            mock_service.get_secret_value.return_value = 'sk-dev123456789'
            mock_service_class.return_value = mock_service
            
            # Call the function
            result = get_openai_api_key()
            
            # Verify
            assert result == 'sk-dev123456789'
            mock_service.get_secret_value.assert_called_once_with('sit/edgp/secret', 'ai_agent_api_key')
    
    @patch('src.secrets_manager.config')
    def test_get_openai_api_key_production(self, mock_config):
        """Test OpenAI API key retrieval for production environment."""
        # Mock config
        mock_config.app_env = 'prd'
        
        # Mock SecretsManagerService
        with patch('src.secrets_manager.SecretsManagerService') as mock_service_class:
            mock_service = Mock()
            mock_service.get_secret_value.return_value = 'sk-prod123456789'
            mock_service_class.return_value = mock_service
            
            # Call the function
            result = get_openai_api_key()
            
            # Verify
            assert result == 'sk-prod123456789'
            mock_service.get_secret_value.assert_called_once_with('prod/edgp/secret', 'ai_agent_api_key')
    
    @patch('src.secrets_manager.config')
    def test_get_openai_api_key_unknown_environment(self, mock_config):
        """Test OpenAI API key retrieval for unknown environment."""
        # Mock config
        mock_config.app_env = 'unknown'
        
        # Mock SecretsManagerService
        with patch('src.secrets_manager.SecretsManagerService') as mock_service_class:
            mock_service = Mock()
            mock_service.get_secret_value.return_value = 'sk-sit123456789'
            mock_service_class.return_value = mock_service
            
            # Call the function
            result = get_openai_api_key()
            
            # Verify
            assert result == 'sk-sit123456789'
            # Should default to SIT secret for unknown environments
            mock_service.get_secret_value.assert_called_once_with('sit/edgp/secret', 'ai_agent_api_key')
    
    @patch('src.secrets_manager.config')
    def test_get_openai_api_key_service_failure(self, mock_config):
        """Test OpenAI API key retrieval when service fails."""
        # Mock config
        mock_config.app_env = 'development'
        
        # Mock SecretsManagerService to raise exception
        with patch('src.secrets_manager.SecretsManagerService') as mock_service_class:
            mock_service_class.side_effect = Exception("Service initialization failed")
            
            # Call the function
            result = get_openai_api_key()
            
            # Verify
            assert result is None