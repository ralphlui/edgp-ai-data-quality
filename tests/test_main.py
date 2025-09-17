#!/usr/bin/env python3
"""
Comprehensive tests for main.py to improve code coverage.
"""

import pytest
import json
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from uuid import uuid4

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import process_sqs_message, main
from models import CustomerRecord, ProcessedRecord
from deduplication_engine import DeduplicationEngine


class TestMainModule:
    """Comprehensive tests for main.py functions."""
    
    @pytest.fixture
    def sample_sqs_message_body(self):
        """Create a sample SQS message body."""
        return json.dumps({
            "data_entry": {
                "data_type": "tabular",
                "domain_name": "customer",
                "file_id": str(uuid4()),
                "policy_id": str(uuid4()),
                "data": {
                    "firstname": "John",
                    "lastname": "Smith",
                    "age": 35,
                    "email": "john.smith@example.com",
                    "phone": "+1-555-0123",
                    "country": "USA",
                    "address": "123 Main Street",
                    "gender": "Male",
                    "status": "active",
                    "id": str(uuid4()),
                    "organization_id": str(uuid4()),
                    "policy_id": str(uuid4()),
                    "uploaded_by": "test_user",
                    "uploaded_date": datetime.now().isoformat(),
                    "domain_name": "customer",
                    "file_id": str(uuid4())
                }
            }
        })
    
    @pytest.fixture
    def mock_dedup_engine(self):
        """Create a mock deduplication engine."""
        mock_engine = Mock(spec=DeduplicationEngine)
        mock_result = ProcessedRecord(
            file_id="test-file",
            policy_id="test-policy",
            data_type="tabular",
            status="success",
            domain_name="customer",
            data={"id": "test-id"},
            failed_validations=[]
        )
        mock_engine.process_record.return_value = mock_result
        return mock_engine
    
    def test_process_sqs_message_success(self, sample_sqs_message_body, mock_dedup_engine):
        """Test successful SQS message processing."""
        result = process_sqs_message(sample_sqs_message_body, mock_dedup_engine)
        
        assert isinstance(result, ProcessedRecord)
        assert result.status in ["success", "fail"]
        assert result.domain_name == "customer"
        assert result.data_type == "tabular"
        
        # Verify deduplication engine was called
        mock_dedup_engine.process_record.assert_called_once()
    
    def test_process_sqs_message_duplicate_found(self, sample_sqs_message_body, mock_dedup_engine):
        """Test SQS message processing when duplicate is found."""
        # Mock duplicate result
        mock_result = ProcessedRecord(
            file_id="test-file",
            policy_id="test-policy",
            data_type="tabular",
            status="fail",
            domain_name="customer",
            data={"id": "test-id"},
            failed_validations=[{
                "rule_name": "NoRecordDuplication",
                "column_name": None,
                "error_message": "Exact match found with 100% confidence",
                "status": "fail"
            }]
        )
        mock_dedup_engine.process_record.return_value = mock_result
        
        result = process_sqs_message(sample_sqs_message_body, mock_dedup_engine)
        
        assert result.status == "fail"
        assert len(result.failed_validations) == 1
        assert result.failed_validations[0]["rule_name"] == "NoRecordDuplication"
    
    def test_process_sqs_message_invalid_json(self, mock_dedup_engine):
        """Test SQS message processing with invalid JSON."""
        invalid_json = "This is not valid JSON"
        
        result = process_sqs_message(invalid_json, mock_dedup_engine)
        
        assert result.status == "fail"
        assert len(result.failed_validations) == 1
        assert result.failed_validations[0]["rule_name"] == "ProcessingError"
        assert "Processing error:" in result.failed_validations[0]["error_message"]
    
    def test_process_sqs_message_missing_data_entry(self, mock_dedup_engine):
        """Test SQS message processing with missing data_entry."""
        message_body = json.dumps({"invalid": "structure"})
        
        result = process_sqs_message(message_body, mock_dedup_engine)
        
        assert result.status == "fail"
        assert len(result.failed_validations) == 1
        assert result.failed_validations[0]["rule_name"] == "ProcessingError"
    
    def test_process_sqs_message_missing_customer_data(self, mock_dedup_engine):
        """Test SQS message processing with missing customer data."""
        message_body = json.dumps({
            "data_entry": {
                "data_type": "tabular",
                "domain_name": "customer",
                "file_id": "test-file"
                # Missing 'data' field
            }
        })
        
        result = process_sqs_message(message_body, mock_dedup_engine)
        
        assert result.status == "fail"
        assert len(result.failed_validations) == 1
        assert result.failed_validations[0]["rule_name"] == "ProcessingError"
    
    def test_process_sqs_message_invalid_customer_data(self, mock_dedup_engine):
        """Test SQS message processing with invalid customer data."""
        message_body = json.dumps({
            "data_entry": {
                "data_type": "tabular",
                "domain_name": "customer",
                "file_id": "test-file",
                "policy_id": "test-policy",
                "data": {
                    "firstname": "John",
                    # Missing required fields like lastname, email, etc.
                }
            }
        })
        
        result = process_sqs_message(message_body, mock_dedup_engine)
        
        assert result.status == "fail"
        assert len(result.failed_validations) == 1
        assert result.failed_validations[0]["rule_name"] == "ProcessingError"
    
    def test_process_sqs_message_dedup_engine_exception(self, sample_sqs_message_body, mock_dedup_engine):
        """Test SQS message processing when deduplication engine raises exception."""
        mock_dedup_engine.process_record.side_effect = Exception("Engine error")
        
        result = process_sqs_message(sample_sqs_message_body, mock_dedup_engine)
        
        assert result.status == "fail"
        assert len(result.failed_validations) == 1
        assert result.failed_validations[0]["rule_name"] == "ProcessingError"
        assert "Engine error" in result.failed_validations[0]["error_message"]
    
    def test_process_sqs_message_metadata_preservation(self, mock_dedup_engine):
        """Test that metadata from SQS message is preserved in response."""
        test_file_id = "test-file-123"
        test_policy_id = "test-policy-456"
        test_domain = "test-domain"
        test_data_type = "test-type"
        
        message_body = json.dumps({
            "data_entry": {
                "data_type": test_data_type,
                "domain_name": test_domain,
                "file_id": test_file_id,
                "policy_id": test_policy_id,
                "data": {
                    "firstname": "John",
                    "lastname": "Smith",
                    "age": 35,
                    "email": "john@test.com",
                    "phone": "+1-555-0123",
                    "country": "USA",
                    "address": "123 Main St",
                    "gender": "Male",
                    "status": "active",
                    "id": str(uuid4()),
                    "organization_id": str(uuid4()),
                    "policy_id": str(uuid4()),
                    "uploaded_by": "test",
                    "uploaded_date": datetime.now().isoformat(),
                    "domain_name": "customer",
                    "file_id": str(uuid4())
                }
            }
        })
        
        result = process_sqs_message(message_body, mock_dedup_engine)
        
        assert result.file_id == test_file_id
        assert result.policy_id == test_policy_id
        assert result.domain_name == test_domain
        assert result.data_type == test_data_type
    
    @patch('main.setup_logging')
    @patch('main.config.validate_config')
    @patch('main.SQSService')
    @patch('main.DynamoDBService')
    @patch('main.DeduplicationEngine')
    def test_main_successful_initialization(self, mock_dedup_engine, mock_dynamodb, mock_sqs, mock_validate, mock_logging):
        """Test successful main function initialization."""
        # Mock logger
        mock_logger = Mock()
        mock_logging.return_value = mock_logger
        
        # Mock services
        mock_sqs_instance = Mock()
        mock_sqs.return_value = mock_sqs_instance
        mock_sqs_instance.receive_messages.return_value = []  # No messages
        
        mock_dynamodb_instance = Mock()
        mock_dynamodb.return_value = mock_dynamodb_instance
        
        mock_dedup_instance = Mock()
        mock_dedup_engine.return_value = mock_dedup_instance
        
        # Mock config validation
        mock_validate.return_value = None
        
        # Test initialization phase only
        with patch('main.time.sleep', side_effect=KeyboardInterrupt):  # Exit after first iteration
            try:
                main()
            except KeyboardInterrupt:
                pass
        
        # Verify services were initialized
        mock_sqs.assert_called_once()
        mock_dynamodb.assert_called_once()
        mock_dedup_engine.assert_called_once()
        mock_validate.assert_called_once()
    
    @patch('main.setup_logging')
    @patch('main.config.validate_config')
    def test_main_config_validation_error(self, mock_validate, mock_logging):
        """Test main function with configuration validation error."""
        mock_logger = Mock()
        mock_logging.return_value = mock_logger
        
        # Mock config validation error
        mock_validate.side_effect = ValueError("Missing environment variable")
        
        # Call main function
        main()
        
        # Verify error was logged and function returned early
        mock_validate.assert_called_once()
        mock_logger.error.assert_called()
    
    @patch('main.setup_logging')
    @patch('main.config.validate_config')
    @patch('main.SQSService')
    def test_main_service_initialization_error(self, mock_sqs, mock_validate, mock_logging):
        """Test main function with service initialization error."""
        mock_logger = Mock()
        mock_logging.return_value = mock_logger
        
        # Mock config validation success
        mock_validate.return_value = None
        
        # Mock service initialization error
        mock_sqs.side_effect = Exception("AWS connection error")
        
        # Call main function
        main()
        
        # Verify error was logged and function returned early
        mock_logger.error.assert_called()
    
    @patch('main.setup_logging')
    @patch('main.config.validate_config')
    @patch('main.SQSService')
    @patch('main.DynamoDBService')
    @patch('main.DeduplicationEngine')
    @patch('main.time.sleep')
    def test_main_message_processing_loop(self, mock_sleep, mock_dedup_engine, mock_dynamodb, mock_sqs, mock_validate, mock_logging):
        """Test main function message processing loop."""
        mock_logger = Mock()
        mock_logging.return_value = mock_logger
        
        # Mock services
        mock_sqs_instance = Mock()
        mock_sqs.return_value = mock_sqs_instance
        
        mock_dynamodb_instance = Mock()
        mock_dynamodb.return_value = mock_dynamodb_instance
        
        mock_dedup_instance = Mock()
        mock_dedup_engine.return_value = mock_dedup_instance
        
        # Mock config validation
        mock_validate.return_value = None
        
        # Mock message processing
        test_message = {
            'Body': json.dumps({
                "data_entry": {
                    "data_type": "tabular",
                    "domain_name": "customer",
                    "file_id": "test-file",
                    "policy_id": "test-policy",
                    "data": {
                        "firstname": "John",
                        "lastname": "Smith",
                        "age": 35,
                        "email": "john@test.com",
                        "phone": "+1-555-0123",
                        "country": "USA",
                        "address": "123 Main St",
                        "gender": "Male",
                        "status": "active",
                        "id": str(uuid4()),
                        "organization_id": str(uuid4()),
                        "policy_id": str(uuid4()),
                        "uploaded_by": "test",
                        "uploaded_date": datetime.now().isoformat(),
                        "domain_name": "customer",
                        "file_id": str(uuid4())
                    }
                }
            }),
            'ReceiptHandle': 'test-receipt-handle'
        }
        
        # Return message once, then empty list, then raise KeyboardInterrupt
        mock_sqs_instance.receive_messages.side_effect = [
            [test_message],  # First call returns message
            [],  # Second call returns empty
            KeyboardInterrupt()  # Third call raises interrupt
        ]
        
        mock_sqs_instance.send_result.return_value = True
        mock_sqs_instance.delete_message.return_value = True
        
        # Call main function
        try:
            main()
        except KeyboardInterrupt:
            pass
        
        # Verify message processing
        assert mock_sqs_instance.receive_messages.call_count >= 1
        mock_sqs_instance.send_result.assert_called_once()
        mock_sqs_instance.delete_message.assert_called_once_with('test-receipt-handle')
    
    @patch('main.logging.getLogger')
    @patch('main.setup_logging')
    @patch('main.config.validate_config')
    @patch('main.SQSService')
    @patch('main.DynamoDBService')
    @patch('main.DeduplicationEngine')
    def test_main_message_processing_error(self, mock_dedup_engine, mock_dynamodb, mock_sqs, mock_validate, mock_logging, mock_get_logger):
        """Test main function with message processing error."""
        # Mock logger
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        # Mock services
        mock_sqs_instance = Mock()
        mock_sqs.return_value = mock_sqs_instance
        
        mock_dynamodb_instance = Mock()
        mock_dynamodb.return_value = mock_dynamodb_instance
        
        mock_dedup_instance = Mock()
        mock_dedup_engine.return_value = mock_dedup_instance
        
        # Mock config validation
        mock_validate.return_value = None
        
        # Mock message with processing error
        test_message = {
            'Body': "Invalid JSON",
            'ReceiptHandle': 'test-receipt-handle'
        }
        
        # Return message once, then raise KeyboardInterrupt
        mock_sqs_instance.receive_messages.side_effect = [
            [test_message],  # First call returns invalid message
            KeyboardInterrupt()  # Second call raises interrupt
        ]
        
        # Call main function
        try:
            main()
        except KeyboardInterrupt:
            pass
        
        # Verify error was logged but processing continued
        mock_logger.error.assert_called()
    
    @patch('main.setup_logging')
    @patch('main.config.validate_config')
    @patch('main.SQSService')
    @patch('main.DynamoDBService')
    @patch('main.DeduplicationEngine')
    @patch('main.time.sleep')
    def test_main_unexpected_error_in_loop(self, mock_sleep, mock_dedup_engine, mock_dynamodb, mock_sqs, mock_validate, mock_logging):
        """Test main function with unexpected error in main loop."""
        mock_logger = Mock()
        mock_logging.return_value = mock_logger
        
        # Mock services
        mock_sqs_instance = Mock()
        mock_sqs.return_value = mock_sqs_instance
        
        mock_dynamodb_instance = Mock()
        mock_dynamodb.return_value = mock_dynamodb_instance
        
        mock_dedup_instance = Mock()
        mock_dedup_engine.return_value = mock_dedup_instance
        
        # Mock config validation
        mock_validate.return_value = None
        
        # Mock unexpected error, then KeyboardInterrupt
        mock_sqs_instance.receive_messages.side_effect = [
            Exception("Unexpected error"),  # First call raises unexpected error
            KeyboardInterrupt()  # Second call raises interrupt after sleep
        ]
        
        # Mock sleep to avoid delay in test
        mock_sleep.side_effect = [None, KeyboardInterrupt()]
        
        # Call main function
        try:
            main()
        except KeyboardInterrupt:
            pass
        
        # Verify error was logged and sleep was called
        mock_logger.error.assert_called()
        mock_sleep.assert_called_with(10)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])