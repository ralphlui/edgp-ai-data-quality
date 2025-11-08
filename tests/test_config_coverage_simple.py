#!/usr/bin/env python3
"""
Targeted tests for config.py to improve code coverage.
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import config


class TestConfigCoverage:
    """Tests to improve config.py coverage."""
    
    def setup_method(self):
        """Reset global state before each test."""
        # Reset initialization flags
        config._openai_initialized = False
        config._langsmith_initialized = False
    
    def test_initialize_openai_config_already_initialized(self):
        """Test early return when OpenAI config already initialized."""
        config._openai_initialized = True
        
        with patch.object(config, 'logger') as mock_logger:
            config.initialize_openai_config()
            
        # Should not log anything since it returns early
        mock_logger.info.assert_not_called()
    
    def test_initialize_openai_config_env_variable_exists(self):
        """Test OpenAI config when environment variable already exists."""
        config._openai_initialized = False
        original_key = config.OPENAI_API_KEY
        config.OPENAI_API_KEY = "existing-api-key"
        
        try:
            with patch.object(config, 'logger') as mock_logger:
                config.initialize_openai_config()
                
                mock_logger.info.assert_any_call(
                    "✅ SUCCESS: OpenAI API key loaded from environment variable"
                )
                assert config._openai_initialized is True
                
        finally:
            config.OPENAI_API_KEY = original_key
    
    def test_initialize_openai_config_no_key_no_secrets_manager(self):
        """Test OpenAI config warning when no key and no secrets manager."""
        config._openai_initialized = False
        original_key = config.OPENAI_API_KEY
        original_secrets = config.USE_SECRETS_MANAGER
        config.OPENAI_API_KEY = None
        config.USE_SECRETS_MANAGER = False
        
        try:
            with patch.object(config, 'logger') as mock_logger:
                config.initialize_openai_config()
                
                mock_logger.warning.assert_any_call(
                    "⚠️ WARNING: OpenAI API key not configured"
                )
                assert config._openai_initialized is True
                
        finally:
            config.OPENAI_API_KEY = original_key
            config.USE_SECRETS_MANAGER = original_secrets
    
    def test_initialize_langsmith_config_already_initialized(self):
        """Test early return when LangSmith config already initialized."""
        config._langsmith_initialized = True
        
        with patch.object(config, 'logger') as mock_logger:
            config.initialize_langsmith_config()
            
        # Should not log anything since it returns early
        mock_logger.info.assert_not_called()
    
    def test_initialize_langsmith_config_env_variable_exists(self):
        """Test LangSmith config when environment variable already exists."""
        config._langsmith_initialized = False
        original_key = config.LANGCHAIN_API_KEY
        config.LANGCHAIN_API_KEY = "existing-langsmith-key"
        
        try:
            with patch.object(config, 'logger') as mock_logger:
                config.initialize_langsmith_config()
                
                mock_logger.info.assert_any_call(
                    "✅ SUCCESS: LangSmith API key loaded from environment variable"
                )
                
        finally:
            config.LANGCHAIN_API_KEY = original_key
    
    def test_initialize_langsmith_config_not_configured(self):
        """Test LangSmith config when not configured."""
        config._langsmith_initialized = False
        original_key = config.LANGCHAIN_API_KEY
        original_secrets = config.USE_SECRETS_MANAGER
        config.LANGCHAIN_API_KEY = None
        config.USE_SECRETS_MANAGER = False
        
        try:
            with patch.object(config, 'logger') as mock_logger:
                config.initialize_langsmith_config()
                
                mock_logger.info.assert_any_call(
                    "ℹ️ INFO: LangSmith API key not configured (optional)"
                )
                
        finally:
            config.LANGCHAIN_API_KEY = original_key
            config.USE_SECRETS_MANAGER = original_secrets
    
    @patch.dict(os.environ, {}, clear=True)
    def test_validate_config_with_langsmith_tracing_enabled(self):
        """Test validate_config with LangSmith tracing enabled."""
        # Set up required config
        original_tracing = config.LANGCHAIN_TRACING_V2
        original_project = config.LANGCHAIN_PROJECT
        config.LANGCHAIN_TRACING_V2 = True
        config.LANGCHAIN_PROJECT = "test-project"
        
        # Mock all required variables
        config.AWS_ACCESS_KEY_ID = "test-access-key"
        config.AWS_SECRET_ACCESS_KEY = "test-secret-key"
        config.WORKFLOW_DEDUPLICATION_REQUEST_SQS_URL = "test-request-url"
        config.WORKFLOW_DEDUPLICATION_RESPONSE_SQS_URL = "test-response-url"
        config.OPENAI_API_KEY = "test-openai-key"
        config.LANGCHAIN_API_KEY = "test-langchain-key"
        
        try:
            with patch('config.initialize_openai_config') as mock_openai_init, \
                 patch('config.initialize_langsmith_config') as mock_langsmith_init, \
                 patch.object(config, 'logger') as mock_logger:
                
                config.validate_config()
                
                # Verify initialization functions were called
                mock_openai_init.assert_called_once()
                mock_langsmith_init.assert_called_once()
                
                # Verify environment variables were set
                assert os.environ.get("LANGCHAIN_API_KEY") == "test-langchain-key"
                assert os.environ.get("LANGCHAIN_PROJECT") == "test-project"
                assert os.environ.get("LANGCHAIN_TRACING_V2") == "true"
                
                # Verify logging
                mock_logger.debug.assert_any_call(
                    "🔐 DEBUG: Set LANGCHAIN_API_KEY environment variable: test-langc..."
                )
                mock_logger.info.assert_any_call(
                    "🔍 LangSmith tracing enabled for project: test-project"
                )
        finally:
            config.LANGCHAIN_TRACING_V2 = original_tracing
            config.LANGCHAIN_PROJECT = original_project
    
    @patch.dict(os.environ, {}, clear=True)
    def test_validate_config_langsmith_key_none_warning(self):
        """Test validate_config warning when LangSmith key is None."""
        original_tracing = config.LANGCHAIN_TRACING_V2
        config.LANGCHAIN_TRACING_V2 = True
        config.LANGCHAIN_API_KEY = None
        
        # Mock required variables
        config.AWS_ACCESS_KEY_ID = "test-access-key"
        config.AWS_SECRET_ACCESS_KEY = "test-secret-key"
        config.WORKFLOW_DEDUPLICATION_REQUEST_SQS_URL = "test-request-url"
        config.WORKFLOW_DEDUPLICATION_RESPONSE_SQS_URL = "test-response-url"
        config.OPENAI_API_KEY = "test-openai-key"
        
        try:
            with patch('config.initialize_openai_config'), \
                 patch('config.initialize_langsmith_config'), \
                 patch.object(config, 'logger') as mock_logger:
                
                config.validate_config()
                
                mock_logger.warning.assert_any_call(
                    "⚠️ WARNING: LANGCHAIN_API_KEY is None or empty, not setting environment variable"
                )
        finally:
            config.LANGCHAIN_TRACING_V2 = original_tracing
    
    def test_validate_config_missing_required_vars(self):
        """Test validate_config with missing required variables."""
        # Save original values
        original_aws_key = config.AWS_ACCESS_KEY_ID
        original_openai_key = config.OPENAI_API_KEY
        
        # Clear required variables
        config.AWS_ACCESS_KEY_ID = None
        config.OPENAI_API_KEY = None
        
        try:
            with patch('config.initialize_openai_config'), \
                 pytest.raises(ValueError) as exc_info:
                
                config.validate_config()
            
            # Verify the error message contains missing variables
            assert "Missing required environment variables" in str(exc_info.value)
            assert "AWS_ACCESS_KEY_ID" in str(exc_info.value)
            assert "OPENAI_API_KEY" in str(exc_info.value)
        finally:
            config.AWS_ACCESS_KEY_ID = original_aws_key
            config.OPENAI_API_KEY = original_openai_key


if __name__ == "__main__":
    pytest.main([__file__, "-v"])