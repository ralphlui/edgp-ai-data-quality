#!/usr/bin/env python3
"""
Comprehensive tests for AWS services to improve code coverage.
"""

import pytest
import json
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from uuid import uuid4
from botocore.exceptions import ClientError

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models import CustomerRecord
from aws_services import DynamoDBService, SQSService
import config


class TestDynamoDBService:
    """Comprehensive tests for DynamoDBService."""
    
    @pytest.fixture
    def sample_customer_record(self):
        """Create a sample customer record for testing."""
        return CustomerRecord(
            firstname="John",
            lastname="Smith",
            age=35,
            email="john.smith@example.com",
            phone="+1-555-0123",
            country="USA",
            address="123 Main Street, Anytown, USA",
            gender="Male",
            status="active",
            id=uuid4(),
            organization_id=uuid4(),
            policy_id=uuid4(),
            uploaded_by="test_user",
            uploaded_date=datetime.now(),
            domain_name="customer",
            file_id=uuid4()
        )
    
    @patch('aws_services.boto3')
    def test_dynamodb_service_initialization(self, mock_boto3):
        """Test DynamoDB service initialization."""
        mock_resource = Mock()
        mock_table = Mock()
        mock_boto3.resource.return_value = mock_resource
        mock_resource.Table.return_value = mock_table
        
        service = DynamoDBService()
        
        mock_boto3.resource.assert_called_once_with('dynamodb', region_name=config.AWS_REGION)
        mock_resource.Table.assert_called_once_with(config.DYNAMODB_TABLE_NAME)
        assert service.dynamodb == mock_resource
        assert service.table == mock_table
    
    @patch('aws_services.boto3')
    def test_create_table_if_not_exists_table_exists(self, mock_boto3):
        """Test table creation when table already exists."""
        mock_resource = Mock()
        mock_table = Mock()
        mock_boto3.resource.return_value = mock_resource
        mock_resource.Table.return_value = mock_table
        
        # Table exists - no exception
        mock_table.load.return_value = None
        
        service = DynamoDBService()
        service.create_table_if_not_exists()
        
        mock_table.load.assert_called_once()
    
    @patch('aws_services.boto3')
    def test_create_table_if_not_exists_create_new_table(self, mock_boto3):
        """Test table creation when table doesn't exist."""
        mock_resource = Mock()
        mock_table = Mock()
        mock_new_table = Mock()
        mock_boto3.resource.return_value = mock_resource
        mock_resource.Table.return_value = mock_table
        mock_resource.create_table.return_value = mock_new_table
        
        # Table doesn't exist - raise ResourceNotFoundException
        client_error = ClientError(
            error_response={'Error': {'Code': 'ResourceNotFoundException'}},
            operation_name='load'
        )
        mock_table.load.side_effect = client_error
        
        service = DynamoDBService()
        service.create_table_if_not_exists()
        
        mock_table.load.assert_called_once()
        mock_resource.create_table.assert_called_once()
        mock_new_table.wait_until_exists.assert_called_once()
    
    @patch('aws_services.boto3')
    def test_create_table_if_not_exists_other_error(self, mock_boto3):
        """Test table creation with unexpected error."""
        mock_resource = Mock()
        mock_table = Mock()
        mock_boto3.resource.return_value = mock_resource
        mock_resource.Table.return_value = mock_table
        
        # Other error - should be re-raised
        client_error = ClientError(
            error_response={'Error': {'Code': 'AccessDenied'}},
            operation_name='load'
        )
        mock_table.load.side_effect = client_error
        
        service = DynamoDBService()
        
        with pytest.raises(ClientError):
            service.create_table_if_not_exists()
    
    @patch('aws_services.boto3')
    def test_exact_match_found(self, mock_boto3, sample_customer_record):
        """Test exact match when record is found."""
        mock_resource = Mock()
        mock_table = Mock()
        mock_boto3.resource.return_value = mock_resource
        mock_resource.Table.return_value = mock_table
        
        # Mock successful response
        mock_response = {
            'Item': {
                'full_hash': 'test_hash',
                'firstname': 'John',
                'lastname': 'Smith'
            }
        }
        mock_table.get_item.return_value = mock_response
        
        service = DynamoDBService()
        result = service.exact_match(sample_customer_record)
        
        assert result == mock_response['Item']
        mock_table.get_item.assert_called_once()
    
    @patch('aws_services.boto3')
    def test_exact_match_not_found(self, mock_boto3, sample_customer_record):
        """Test exact match when record is not found."""
        mock_resource = Mock()
        mock_table = Mock()
        mock_boto3.resource.return_value = mock_resource
        mock_resource.Table.return_value = mock_table
        
        # Mock response with no item
        mock_response = {}
        mock_table.get_item.return_value = mock_response
        
        service = DynamoDBService()
        result = service.exact_match(sample_customer_record)
        
        assert result is None
        mock_table.get_item.assert_called_once()
    
    @patch('aws_services.boto3')
    def test_exact_match_error(self, mock_boto3, sample_customer_record):
        """Test exact match with client error."""
        mock_resource = Mock()
        mock_table = Mock()
        mock_boto3.resource.return_value = mock_resource
        mock_resource.Table.return_value = mock_table
        
        # Mock client error
        client_error = ClientError(
            error_response={'Error': {'Code': 'ProvisionedThroughputExceededException'}},
            operation_name='get_item'
        )
        mock_table.get_item.side_effect = client_error
        
        service = DynamoDBService()
        
        with pytest.raises(ClientError):
            service.exact_match(sample_customer_record)
    
    @patch('aws_services.boto3')
    def test_fetch_candidates_success(self, mock_boto3, sample_customer_record):
        """Test successful candidate fetching."""
        mock_resource = Mock()
        mock_table = Mock()
        mock_boto3.resource.return_value = mock_resource
        mock_resource.Table.return_value = mock_table
        
        # Mock successful response
        mock_response = {
            'Items': [
                {'full_hash': 'hash1', 'firstname': 'John'},
                {'full_hash': 'hash2', 'firstname': 'Jane'}
            ]
        }
        mock_table.query.return_value = mock_response
        
        service = DynamoDBService()
        result = service.fetch_candidates(sample_customer_record)
        
        assert result == mock_response['Items']
        assert len(result) == 2
        mock_table.query.assert_called_once()
    
    @patch('aws_services.boto3')
    def test_fetch_candidates_no_items(self, mock_boto3, sample_customer_record):
        """Test candidate fetching with no results."""
        mock_resource = Mock()
        mock_table = Mock()
        mock_boto3.resource.return_value = mock_resource
        mock_resource.Table.return_value = mock_table
        
        # Mock response with no items
        mock_response = {}
        mock_table.query.return_value = mock_response
        
        service = DynamoDBService()
        result = service.fetch_candidates(sample_customer_record)
        
        assert result == []
        mock_table.query.assert_called_once()
    
    @patch('aws_services.boto3')
    def test_fetch_candidates_error(self, mock_boto3, sample_customer_record):
        """Test candidate fetching with client error."""
        mock_resource = Mock()
        mock_table = Mock()
        mock_boto3.resource.return_value = mock_resource
        mock_resource.Table.return_value = mock_table
        
        # Mock client error
        client_error = ClientError(
            error_response={'Error': {'Code': 'ProvisionedThroughputExceededException'}},
            operation_name='query'
        )
        mock_table.query.side_effect = client_error
        
        service = DynamoDBService()
        
        with pytest.raises(ClientError):
            service.fetch_candidates(sample_customer_record)
    
    @patch('aws_services.boto3')
    def test_store_record_success(self, mock_boto3, sample_customer_record):
        """Test successful record storage."""
        mock_resource = Mock()
        mock_table = Mock()
        mock_boto3.resource.return_value = mock_resource
        mock_resource.Table.return_value = mock_table
        
        # Mock successful put_item
        mock_table.put_item.return_value = {}
        
        service = DynamoDBService()
        result = service.store_record(sample_customer_record)
        
        assert result is True
        mock_table.put_item.assert_called_once()
        
        # Verify the item structure
        call_args = mock_table.put_item.call_args
        item = call_args[1]['Item']
        assert 'full_hash' in item
        assert 'block_key' in item
        assert item['firstname'] == sample_customer_record.firstname
        assert item['lastname'] == sample_customer_record.lastname
        assert item['email'] == sample_customer_record.email
    
    @patch('aws_services.boto3')
    def test_store_record_error(self, mock_boto3, sample_customer_record):
        """Test record storage with client error."""
        mock_resource = Mock()
        mock_table = Mock()
        mock_boto3.resource.return_value = mock_resource
        mock_resource.Table.return_value = mock_table
        
        # Mock client error
        client_error = ClientError(
            error_response={'Error': {'Code': 'ProvisionedThroughputExceededException'}},
            operation_name='put_item'
        )
        mock_table.put_item.side_effect = client_error
        
        service = DynamoDBService()
        result = service.store_record(sample_customer_record)
        
        assert result is False


class TestSQSService:
    """Comprehensive tests for SQSService."""
    
    @patch('aws_services.boto3')
    def test_sqs_service_initialization(self, mock_boto3):
        """Test SQS service initialization."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        
        service = SQSService()
        
        mock_boto3.client.assert_called_once_with('sqs', region_name=config.AWS_REGION)
        assert service.sqs == mock_client
    
    @patch('aws_services.boto3')
    def test_receive_message_success(self, mock_boto3):
        """Test successful message receiving."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        
        # Mock successful response
        mock_response = {
            'Messages': [
                {
                    'MessageId': 'test-id',
                    'Body': '{"test": "data"}',
                    'ReceiptHandle': 'test-handle'
                }
            ]
        }
        mock_client.receive_message.return_value = mock_response
        
        service = SQSService()
        result = service.receive_message()
        
        assert result == mock_response['Messages'][0]
        mock_client.receive_message.assert_called_once_with(
            QueueUrl=config.WORKFLOW_DEDUPLICATION_REQUEST_SQS_URL,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20
        )
    
    @patch('aws_services.boto3')
    def test_receive_message_no_messages(self, mock_boto3):
        """Test message receiving with no messages."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        
        # Mock response with no messages
        mock_response = {}
        mock_client.receive_message.return_value = mock_response
        
        service = SQSService()
        result = service.receive_message()
        
        assert result is None
    
    @patch('aws_services.boto3')
    def test_receive_message_error(self, mock_boto3):
        """Test message receiving with client error."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        
        # Mock client error
        client_error = ClientError(
            error_response={'Error': {'Code': 'QueueDoesNotExist'}},
            operation_name='receive_message'
        )
        mock_client.receive_message.side_effect = client_error
        
        service = SQSService()
        
        with pytest.raises(ClientError):
            service.receive_message()
    
    @patch('aws_services.boto3')
    def test_receive_messages_success(self, mock_boto3):
        """Test successful multiple message receiving."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        
        # Mock successful response
        mock_response = {
            'Messages': [
                {'MessageId': 'id1', 'Body': '{"test": "data1"}'},
                {'MessageId': 'id2', 'Body': '{"test": "data2"}'}
            ]
        }
        mock_client.receive_message.return_value = mock_response
        
        service = SQSService()
        result = service.receive_messages('test-queue-url', max_messages=5)
        
        assert result == mock_response['Messages']
        assert len(result) == 2
        mock_client.receive_message.assert_called_once_with(
            QueueUrl='test-queue-url',
            MaxNumberOfMessages=5,
            WaitTimeSeconds=20
        )
    
    @patch('aws_services.boto3')
    def test_receive_messages_max_limit(self, mock_boto3):
        """Test message receiving with max limit enforcement."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        
        mock_response = {'Messages': []}
        mock_client.receive_message.return_value = mock_response
        
        service = SQSService()
        service.receive_messages('test-queue-url', max_messages=15)  # Over limit
        
        # Should be capped at 10
        mock_client.receive_message.assert_called_once_with(
            QueueUrl='test-queue-url',
            MaxNumberOfMessages=10,
            WaitTimeSeconds=20
        )
    
    @patch('aws_services.boto3')
    def test_receive_messages_error(self, mock_boto3):
        """Test multiple message receiving with client error."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        
        # Mock client error
        client_error = ClientError(
            error_response={'Error': {'Code': 'QueueDoesNotExist'}},
            operation_name='receive_message'
        )
        mock_client.receive_message.side_effect = client_error
        
        service = SQSService()
        result = service.receive_messages('test-queue-url')
        
        assert result == []
    
    @patch('aws_services.boto3')
    def test_delete_message_success(self, mock_boto3):
        """Test successful message deletion."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        
        # Mock successful deletion
        mock_client.delete_message.return_value = {}
        
        service = SQSService()
        result = service.delete_message('test-receipt-handle')
        
        assert result is True
        mock_client.delete_message.assert_called_once_with(
            QueueUrl=config.WORKFLOW_DEDUPLICATION_REQUEST_SQS_URL,
            ReceiptHandle='test-receipt-handle'
        )
    
    @patch('aws_services.boto3')
    def test_delete_message_error(self, mock_boto3):
        """Test message deletion with client error."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        
        # Mock client error
        client_error = ClientError(
            error_response={'Error': {'Code': 'ReceiptHandleIsInvalid'}},
            operation_name='delete_message'
        )
        mock_client.delete_message.side_effect = client_error
        
        service = SQSService()
        result = service.delete_message('invalid-handle')
        
        assert result is False
    
    @patch('aws_services.boto3')
    def test_send_result_success(self, mock_boto3):
        """Test successful result sending."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        
        # Mock successful send
        mock_client.send_message.return_value = {'MessageId': 'test-id'}
        
        service = SQSService()
        test_result = {'status': 'success', 'duplicate_found': False}
        result = service.send_result(test_result)
        
        assert result is True
        mock_client.send_message.assert_called_once_with(
            QueueUrl=config.WORKFLOW_DEDUPLICATION_RESPONSE_SQS_URL,
            MessageBody=json.dumps(test_result)
        )
    
    @patch('aws_services.boto3')
    def test_send_result_error(self, mock_boto3):
        """Test result sending with client error."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        
        # Mock client error
        client_error = ClientError(
            error_response={'Error': {'Code': 'QueueDoesNotExist'}},
            operation_name='send_message'
        )
        mock_client.send_message.side_effect = client_error
        
        service = SQSService()
        test_result = {'status': 'error'}
        result = service.send_result(test_result)
        
        assert result is False