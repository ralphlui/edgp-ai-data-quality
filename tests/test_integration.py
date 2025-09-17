#!/usr/bin/env python3
"""
Integration tests for the complete EDGP AI Data Quality system.
"""

import pytest
import json
import sys
import os
from unittest.mock import Mock, patch
from datetime import datetime
from uuid import uuid4

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models import CustomerRecord, ProcessedRecord
from deduplication_engine import DeduplicationEngine
from aws_services import DynamoDBService, SQSService
from main import process_sqs_message
import config


class TestIntegration:
    """Integration tests for the complete system."""
    
    @pytest.fixture
    def sample_sqs_message(self):
        """Create a sample SQS message in the expected format."""
        return {
            "data_entry": {
                "data_type": "tabular",
                "domain_name": "customer",
                "file_id": str(uuid4()),
                "policy_id": str(uuid4()),
                "data": {
                    "firstname": "Jane",
                    "lastname": "Doe",
                    "age": 28,
                    "email": "jane.doe@example.com",
                    "phone": "+1-555-0199",
                    "country": "USA",
                    "address": "456 Oak Ave, Some City",
                    "gender": "Female",
                    "status": "active",
                    "id": str(uuid4()),
                    "organization_id": str(uuid4())
                }
            }
        }
    
    @pytest.fixture
    def mock_dedup_engine(self):
        """Create a mock deduplication engine."""
        mock_engine = Mock()
        mock_engine.check_duplicate.return_value = Mock(
            is_duplicate=False,
            reason="No match found - record is unique",
            confidence_score=0.0
        )
        
        # Mock the process_record method to return a ProcessedRecord
        mock_processed_record = ProcessedRecord(
            file_id="test-file-id",
            policy_id="test-policy-id",
            data_type="tabular",
            status="success",
            domain_name="customer",
            data={
                "firstname": "Jane",
                "lastname": "Doe",
                "age": 28,
                "email": "jane.doe@example.com"
            },
            failed_validations=[]
        )
        mock_engine.process_record.return_value = mock_processed_record
        
        return mock_engine
    
    def test_sqs_message_processing_success(self, sample_sqs_message, mock_dedup_engine):
        """Test successful processing of an SQS message."""
        message_body = json.dumps(sample_sqs_message)
        
        result = process_sqs_message(message_body, mock_dedup_engine)
        
        assert isinstance(result, ProcessedRecord)
        assert result.status == "success"
        assert result.data_type == "tabular"
        assert len(result.failed_validations) == 0
        assert result.data["firstname"] == "Jane"
        assert result.data["lastname"] == "Doe"
    
    def test_sqs_message_processing_duplicate_found(self, sample_sqs_message, mock_dedup_engine):
        """Test processing when a duplicate is found."""
        # Configure mock to return duplicate found
        mock_dedup_engine.check_duplicate.return_value = Mock(
            is_duplicate=True,
            reason="Fuzzy match found with 89% confidence",
            confidence_score=0.89
        )
        
        # Mock the process_record method to return a fail status
        mock_processed_record = ProcessedRecord(
            file_id="test-file-id",
            policy_id="test-policy-id",
            data_type="tabular",
            status="fail",
            domain_name="customer",
            data={},
            failed_validations=[{
                "rule_name": "NoRecordDuplication",
                "error_message": "Duplicate found - Fuzzy match found with 89% confidence"
            }]
        )
        mock_dedup_engine.process_record.return_value = mock_processed_record
        
        message_body = json.dumps(sample_sqs_message)
        result = process_sqs_message(message_body, mock_dedup_engine)
        
        assert result.status == "fail"
        assert len(result.failed_validations) == 1
        assert result.failed_validations[0]["rule_name"] == "NoRecordDuplication"
        assert "89% confidence" in result.failed_validations[0]["error_message"]
    
    def test_sqs_message_processing_invalid_format(self, mock_dedup_engine):
        """Test processing of malformed SQS message."""
        invalid_message = '{"invalid": "format"}'
        
        result = process_sqs_message(invalid_message, mock_dedup_engine)
        
        assert result.status == "fail"
        assert result.file_id == "unknown"
        assert len(result.failed_validations) == 1
        assert result.failed_validations[0]["rule_name"] == "ProcessingError"
    
    def test_customer_record_validation(self):
        """Test CustomerRecord validation with various inputs."""
        # Valid record
        valid_data = {
            "firstname": "Test",
            "lastname": "User",
            "age": 25,
            "email": "test@example.com",
            "phone": "+1-555-0123",
            "country": "USA",
            "address": "123 Test St",
            "gender": "Male",
            "status": "active",
            "id": uuid4(),
            "organization_id": uuid4(),
            "policy_id": uuid4(),
            "uploaded_by": "system",
            "uploaded_date": datetime.now(),
            "domain_name": "test.com",
            "file_id": uuid4()
        }
        
        record = CustomerRecord(**valid_data)
        assert record.firstname == "Test"
        assert record.email == "test@example.com"
        
        # Missing required field should raise validation error
        incomplete_data = valid_data.copy()
        del incomplete_data["firstname"]
        
        with pytest.raises(Exception):  # Pydantic validation error
            CustomerRecord(**incomplete_data)
    
    def test_field_weights_configuration(self):
        """Test that field weights are properly configured."""
        from config import FIELD_WEIGHTS
        
        # Check all expected fields are present
        expected_fields = [
            'firstname', 'lastname', 'email', 'phone', 
            'address', 'organization_id', 'country', 'gender'
        ]
        
        for field in expected_fields:
            assert field in FIELD_WEIGHTS
            assert 0 < FIELD_WEIGHTS[field] <= 1
        
        # Check total weights sum to 1.0 (within tolerance)
        total_weight = sum(FIELD_WEIGHTS.values())
        assert abs(total_weight - 1.0) < 0.01
    
    def test_environment_configuration(self):
        """Test environment configuration loading."""
        # Test that config module loads without errors
        import config
        
        # Test field weights are accessible
        assert hasattr(config, 'FIELD_WEIGHTS')
        assert isinstance(config.FIELD_WEIGHTS, dict)
        
        # Test thresholds are defined
        assert hasattr(config, 'SIMILARITY_THRESHOLD')
        assert hasattr(config, 'GPT_CONFIDENCE_THRESHOLD')
    
    @patch('aws_services.boto3')
    def test_aws_services_initialization(self, mock_boto3):
        """Test AWS services can be initialized."""
        # Mock boto3 clients
        mock_boto3.client.return_value = Mock()
        mock_boto3.resource.return_value = Mock()
        
        # Test DynamoDB service initialization
        dynamodb_service = DynamoDBService()
        assert dynamodb_service is not None
        
        # Test SQS service initialization
        sqs_service = SQSService()
        assert sqs_service is not None
    
    def test_utility_functions_integration(self):
        """Test that utility functions work together correctly."""
        from utils import compute_full_hash, compute_block_key, compute_weighted_similarity
        
        # Create two similar records
        record1 = CustomerRecord(
            firstname="John",
            lastname="Smith",
            age=30,
            email="john@example.com",
            phone="+1-555-0123",
            country="USA",
            address="123 Main St",
            gender="Male",
            status="active",
            id=uuid4(),
            organization_id=uuid4(),
            policy_id=uuid4(),
            uploaded_by="system",
            uploaded_date=datetime.now(),
            domain_name="test.com",
            file_id=uuid4()
        )
        
        record2 = CustomerRecord(
            firstname="Jon",  # Slight variation
            lastname="Smith",
            age=30,
            email="john@example.com",
            phone="+1-555-0123",
            country="USA",
            address="123 Main St",
            gender="Male",
            status="active",
            id=uuid4(),
            organization_id=record1.organization_id,  # Same org
            policy_id=uuid4(),
            uploaded_by="system",
            uploaded_date=datetime.now(),
            domain_name="test.com",
            file_id=uuid4()
        )
        
        # Test hash functions
        hash1 = compute_full_hash(record1)
        hash2 = compute_full_hash(record2)
        assert hash1 != hash2  # Different records should have different hashes
        
        # Test blocking keys
        block1 = compute_block_key(record1)
        block2 = compute_block_key(record2)
        assert block1 == block2  # Similar names should have same block key
        
        # Test similarity calculation
        similarity = compute_weighted_similarity(record1, record2)
        assert 0.85 <= similarity <= 1.0  # Should be high similarity
    
    def test_end_to_end_workflow(self, sample_sqs_message):
        """Test complete end-to-end workflow simulation."""
        with patch('aws_services.boto3'):
            # Mock the complete workflow
            mock_dynamodb = Mock()
            mock_dynamodb.get_record_by_hash.return_value = None
            mock_dynamodb.get_candidates_by_block_key.return_value = []
            mock_dynamodb.store_record.return_value = None
            
            # Create engine
            with patch('deduplication_engine.ChatOpenAI'):
                engine = DeduplicationEngine(mock_dynamodb)
            
            # Process message
            message_body = json.dumps(sample_sqs_message)
            result = process_sqs_message(message_body, engine)
            
            # Verify results
            assert isinstance(result, ProcessedRecord)
            assert result.status in ["success", "fail"]
            assert result.data_type == "tabular"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
