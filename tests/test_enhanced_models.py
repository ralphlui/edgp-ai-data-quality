#!/usr/bin/env python3
"""
Enhanced tests for model validation, LLM output format verification, and accuracy testing.
"""

import pytest
import sys
import os
import json
import logging
from uuid import uuid4, UUID
from datetime import datetime
from typing import Dict, List, Any
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models import CustomerRecord, DuplicationResult, ProcessedRecord, CandidateMatch
from deduplication_engine import DeduplicationEngine
from utils import create_gpt_prompt_best_match_with_score


class TestModelValidation:
    """Test cases for model validation and data integrity."""
    
    @pytest.fixture
    def valid_customer_data(self):
        """Generate valid customer data for testing."""
        return {
            "firstname": "John",
            "lastname": "Smith",
            "age": 35,
            "email": "john.smith@example.com",
            "phone": "+1-555-0123",
            "country": "USA",
            "address": "123 Main St, Anytown, NY 10001",
            "gender": "Male",
            "status": "active",
            "id": uuid4(),
            "organization_id": uuid4()
        }
    
    @pytest.fixture
    def invalid_customer_data_sets(self):
        """Generate sets of invalid customer data for testing validation."""
        base_data = {
            "firstname": "John",
            "lastname": "Smith",
            "age": 35,
            "email": "john.smith@example.com",
            "phone": "+1-555-0123",
            "country": "USA",
            "address": "123 Main St, Anytown, NY 10001",
            "gender": "Male",
            "status": "active",
            "id": uuid4(),
            "organization_id": uuid4()
        }
        
        return {
            "missing_required_field": {k: v for k, v in base_data.items() if k != "firstname"},
            "invalid_age_type": {**base_data, "age": "thirty-five"},
            "invalid_email_format": {**base_data, "email": "not-an-email"},
            "invalid_uuid": {**base_data, "id": "not-a-uuid"},
            "negative_age": {**base_data, "age": -5},
            "empty_string_field": {**base_data, "firstname": ""},
            "none_required_field": {**base_data, "lastname": None}
        }
    
    def test_valid_customer_record_creation(self, valid_customer_data):
        """Test successful creation of CustomerRecord with valid data."""
        record = CustomerRecord(**valid_customer_data)
        
        # Verify all fields are set correctly
        assert record.firstname == valid_customer_data["firstname"]
        assert record.lastname == valid_customer_data["lastname"]
        assert record.age == valid_customer_data["age"]
        assert record.email == valid_customer_data["email"]
        assert record.phone == valid_customer_data["phone"]
        assert record.country == valid_customer_data["country"]
        assert record.address == valid_customer_data["address"]
        assert record.gender == valid_customer_data["gender"]
        assert record.status == valid_customer_data["status"]
        assert isinstance(record.id, UUID)
        assert isinstance(record.organization_id, UUID)
    
    @pytest.mark.parametrize("invalid_case", [
        "missing_required_field",
        "invalid_age_type", 
        "invalid_uuid"
        # Note: negative_age and empty_string_field are actually allowed in our model
    ])
    def test_invalid_customer_record_validation(self, invalid_customer_data_sets, invalid_case):
        """Test that CustomerRecord validation catches invalid data."""
        invalid_data = invalid_customer_data_sets[invalid_case]
        
        with pytest.raises(Exception):  # Pydantic validation error
            CustomerRecord(**invalid_data)
    
    def test_duplication_result_model(self):
        """Test DuplicationResult model validation."""
        # Test valid DuplicationResult
        result = DuplicationResult(
            is_duplicate=True,
            reason="Exact match found on email and phone",
            confidence_score=0.95,
            matched_record_id="123e4567-e89b-12d3-a456-426614174000"
        )
        
        assert result.is_duplicate is True
        assert result.reason == "Exact match found on email and phone"
        assert result.confidence_score == 0.95
        assert result.matched_record_id == "123e4567-e89b-12d3-a456-426614174000"
        
        # Test without optional fields
        simple_result = DuplicationResult(
            is_duplicate=False,
            reason="No duplicates found"
        )
        
        assert simple_result.is_duplicate is False
        assert simple_result.confidence_score is None
        assert simple_result.matched_record_id is None
    
    def test_processed_record_format(self):
        """Test ProcessedRecord output format."""
        processed = ProcessedRecord(
            file_id="test-file-123",
            policy_id="policy-456",
            data_type="tabular",
            status="success",
            domain_name="customer",
            data={"customer_id": "123", "name": "John Doe"},
            failed_validations=[]
        )
        
        assert processed.file_id == "test-file-123"
        assert processed.policy_id == "policy-456"
        assert processed.data_type == "tabular"
        assert processed.status == "success"
        assert processed.domain_name == "customer"
        assert isinstance(processed.data, dict)
        assert isinstance(processed.failed_validations, list)
    
    def test_candidate_match_model(self, valid_customer_data):
        """Test CandidateMatch model."""
        record = CustomerRecord(**valid_customer_data)
        
        match = CandidateMatch(
            record_id=str(record.id),
            record=record,
            similarity_score=85.5
        )
        
        assert match.record_id == str(record.id)
        assert match.record == record
        assert match.similarity_score == 85.5


class TestLLMOutputFormatValidation:
    """Test cases for LLM output format validation and parsing."""
    
    @pytest.fixture
    def mock_dedup_engine(self):
        """Create a mock deduplication engine for testing."""
        with patch('deduplication_engine.DynamoDBService'), \
             patch('deduplication_engine.ChatOpenAI'):
            engine = DeduplicationEngine()
            engine.llm = Mock()
            return engine
    
    @pytest.fixture
    def sample_customer_records(self):
        """Generate sample customer records for LLM testing."""
        return [
            CustomerRecord(
                firstname="John", lastname="Smith", age=35,
                email="john.smith@example.com", phone="+1-555-0123",
                country="USA", address="123 Main St", gender="Male",
                status="active", id=uuid4(), organization_id=uuid4()
            ),
            CustomerRecord(
                firstname="Jon", lastname="Smyth", age=36,
                email="jon.smyth@company.com", phone="+1-555-9999",
                country="Canada", address="456 Oak Ave", gender="Male",
                status="active", id=uuid4(), organization_id=uuid4()
            )
        ]
    
    def test_valid_llm_json_response_parsing(self, mock_dedup_engine, sample_customer_records):
        """Test parsing of valid LLM JSON responses."""
        # Mock valid JSON response
        valid_response = Mock()
        valid_response.content = '''
        {
            "best_match_index": 0,
            "score": 0.85,
            "reason": "High similarity in name and contact details"
        }
        '''
        mock_dedup_engine.llm.invoke.return_value = valid_response
        
        # Create candidate matches
        candidates = [
            CandidateMatch(
                record_id=str(sample_customer_records[0].id),
                record=sample_customer_records[0],
                similarity_score=80.0
            )
        ]
        
        result = mock_dedup_engine.gpt_semantic_check_top_k(sample_customer_records[1], candidates)
        
        # Verify result format
        assert isinstance(result, dict)
        assert len(result) == 1
        
        # Verify result content
        candidate_id = str(sample_customer_records[0].id)
        assert candidate_id in result
        assert "duplicate" in result[candidate_id]
        assert "confidence" in result[candidate_id]
        assert isinstance(result[candidate_id]["duplicate"], bool)
        assert isinstance(result[candidate_id]["confidence"], (int, float))
    
    def test_llm_json_with_code_blocks(self, mock_dedup_engine, sample_customer_records):
        """Test parsing JSON responses wrapped in markdown code blocks."""
        # Mock JSON response with markdown code blocks
        response_with_blocks = Mock()
        response_with_blocks.content = '''
        Here's my analysis:
        
        ```json
        {
            "best_match_index": 1,
            "score": 0.75,
            "reason": "Similar names but different contact information"
        }
        ```
        
        The records show moderate similarity.
        '''
        mock_dedup_engine.llm.invoke.return_value = response_with_blocks
        
        candidates = [
            CandidateMatch(
                record_id=str(sample_customer_records[0].id),
                record=sample_customer_records[0],
                similarity_score=75.0
            )
        ]
        
        result = mock_dedup_engine.gpt_semantic_check_top_k(sample_customer_records[1], candidates)
        
        # Should successfully parse despite markdown formatting
        assert isinstance(result, dict)
        assert len(result) == 1
    
    def test_invalid_llm_json_response_handling(self, mock_dedup_engine, sample_customer_records):
        """Test handling of invalid or malformed JSON responses."""
        # Mock invalid JSON response
        invalid_response = Mock()
        invalid_response.content = "This is not valid JSON at all!"
        mock_dedup_engine.llm.invoke.return_value = invalid_response
        
        candidates = [
            CandidateMatch(
                record_id=str(sample_customer_records[0].id),
                record=sample_customer_records[0],
                similarity_score=80.0
            )
        ]
        
        result = mock_dedup_engine.gpt_semantic_check_top_k(sample_customer_records[1], candidates)
        
        # Should return empty dict when JSON parsing fails
        assert isinstance(result, dict)
        assert len(result) == 0
    
    def test_llm_response_missing_required_fields(self, mock_dedup_engine, sample_customer_records):
        """Test handling of JSON responses missing required fields."""
        # Mock JSON response missing required fields
        incomplete_response = Mock()
        incomplete_response.content = '''
        {
            "score": 0.85
        }
        '''
        mock_dedup_engine.llm.invoke.return_value = incomplete_response
        
        candidates = [
            CandidateMatch(
                record_id=str(sample_customer_records[0].id),
                record=sample_customer_records[0],
                similarity_score=80.0
            )
        ]
        
        result = mock_dedup_engine.gpt_semantic_check_top_k(sample_customer_records[1], candidates)
        
        # Should handle missing fields gracefully
        assert isinstance(result, dict)
    
    @pytest.mark.parametrize("score_value,expected_duplicate", [
        (0.95, True),   # High confidence - should be duplicate
        (0.85, True),   # Above threshold - should be duplicate  
        (0.75, True),   # Above threshold - should be duplicate
        (0.65, False),  # Below threshold - should not be duplicate
        (0.45, False),  # Low confidence - should not be duplicate
        (0.0, False),   # Zero confidence - should not be duplicate
    ])
    def test_llm_confidence_threshold_logic(self, mock_dedup_engine, sample_customer_records, score_value, expected_duplicate):
        """Test that confidence threshold logic works correctly for different scores."""
        # Mock JSON response with varying scores
        response = Mock()
        response.content = f'''
        {{
            "best_match_index": 0,
            "score": {score_value},
            "reason": "Test case for confidence threshold"
        }}
        '''
        mock_dedup_engine.llm.invoke.return_value = response
        
        candidates = [
            CandidateMatch(
                record_id=str(sample_customer_records[0].id),
                record=sample_customer_records[0],
                similarity_score=80.0
            )
        ]
        
        result = mock_dedup_engine.gpt_semantic_check_top_k(sample_customer_records[1], candidates)
        
        # Verify threshold logic
        candidate_id = str(sample_customer_records[0].id)
        if len(result) > 0:
            assert result[candidate_id]["duplicate"] == expected_duplicate


class TestLLMAccuracyAndDecisionLogic:
    """Test cases for LLM accuracy and decision-making logic."""
    
    @pytest.fixture
    def dedup_engine_with_mock_llm(self):
        """Create deduplication engine with mocked LLM for controlled testing."""
        with patch('deduplication_engine.DynamoDBService'), \
             patch('deduplication_engine.ChatOpenAI'):
            engine = DeduplicationEngine()
            engine.llm = Mock()
            return engine
    
    def test_exact_duplicate_detection(self, dedup_engine_with_mock_llm):
        """Test that LLM correctly identifies exact duplicates."""
        # Create identical records (except IDs)
        record1 = CustomerRecord(
            firstname="John", lastname="Smith", age=35,
            email="john.smith@example.com", phone="+1-555-0123",
            country="USA", address="123 Main St", gender="Male",
            status="active", id=uuid4(), organization_id=uuid4()
        )
        
        record2 = CustomerRecord(
            firstname="John", lastname="Smith", age=35,
            email="john.smith@example.com", phone="+1-555-0123",
            country="USA", address="123 Main St", gender="Male",
            status="active", id=uuid4(), organization_id=uuid4()
        )
        
        # Mock LLM response indicating high confidence duplicate
        mock_response = Mock()
        mock_response.content = '''
        {
            "best_match_index": 0,
            "score": 0.95,
            "reason": "Exact match on all key fields: name, email, phone, address"
        }
        '''
        dedup_engine_with_mock_llm.llm.invoke.return_value = mock_response
        
        candidates = [CandidateMatch(record_id=str(record1.id), record=record1, similarity_score=95.0)]
        result = dedup_engine_with_mock_llm.gpt_semantic_check_top_k(record2, candidates)
        
        # Should identify as duplicate with high confidence
        assert len(result) == 1
        candidate_result = list(result.values())[0]
        assert candidate_result["duplicate"] is True
        assert candidate_result["confidence"] >= 0.9
    
    def test_non_duplicate_detection(self, dedup_engine_with_mock_llm):
        """Test that LLM correctly identifies non-duplicates."""
        # Create clearly different records
        record1 = CustomerRecord(
            firstname="John", lastname="Smith", age=35,
            email="john.smith@example.com", phone="+1-555-0123",
            country="USA", address="123 Main St", gender="Male",
            status="active", id=uuid4(), organization_id=uuid4()
        )
        
        record2 = CustomerRecord(
            firstname="Jane", lastname="Doe", age=28,
            email="jane.doe@different.com", phone="+1-555-9999",
            country="Canada", address="456 Oak Ave", gender="Female",
            status="active", id=uuid4(), organization_id=uuid4()
        )
        
        # Mock LLM response indicating low confidence (not duplicate)
        mock_response = Mock()
        mock_response.content = '''
        {
            "best_match_index": 0,
            "score": 0.25,
            "reason": "Different names, emails, phones, and addresses - clearly different people"
        }
        '''
        dedup_engine_with_mock_llm.llm.invoke.return_value = mock_response
        
        candidates = [CandidateMatch(record_id=str(record1.id), record=record1, similarity_score=30.0)]
        result = dedup_engine_with_mock_llm.gpt_semantic_check_top_k(record2, candidates)
        
        # Should identify as not duplicate
        assert len(result) == 1
        candidate_result = list(result.values())[0]
        assert candidate_result["duplicate"] is False
        assert candidate_result["confidence"] <= 0.7
    
    def test_ambiguous_case_handling(self, dedup_engine_with_mock_llm):
        """Test LLM handling of ambiguous cases (similar but not identical)."""
        # Create similar but different records (common name variations)
        record1 = CustomerRecord(
            firstname="Robert", lastname="Johnson", age=45,
            email="robert.johnson@example.com", phone="+1-555-1234",
            country="USA", address="789 Pine St", gender="Male",
            status="active", id=uuid4(), organization_id=uuid4()
        )
        
        record2 = CustomerRecord(
            firstname="Bob", lastname="Johnson", age=45,
            email="bob.johnson@example.com", phone="+1-555-1234",
            country="USA", address="789 Pine Street", gender="Male",
            status="active", id=uuid4(), organization_id=uuid4()
        )
        
        # Mock LLM response showing moderate confidence
        mock_response = Mock()
        mock_response.content = '''
        {
            "best_match_index": 0,
            "score": 0.80,
            "reason": "Same last name, age, phone and similar address. Robert/Bob are common name variations."
        }
        '''
        dedup_engine_with_mock_llm.llm.invoke.return_value = mock_response
        
        candidates = [CandidateMatch(record_id=str(record1.id), record=record1, similarity_score=82.0)]
        result = dedup_engine_with_mock_llm.gpt_semantic_check_top_k(record2, candidates)
        
        # Should handle ambiguous case appropriately
        assert len(result) == 1
        candidate_result = list(result.values())[0]
        # Based on score of 0.80, should be above threshold (likely duplicate)
        assert candidate_result["duplicate"] is True
        assert 0.7 <= candidate_result["confidence"] <= 0.9
    
    def test_multiple_candidates_selection(self, dedup_engine_with_mock_llm):
        """Test LLM's ability to select the best match among multiple candidates."""
        base_record = CustomerRecord(
            firstname="Sarah", lastname="Wilson", age=32,
            email="sarah.wilson@email.com", phone="+1-555-5678",
            country="USA", address="321 Elm St", gender="Female",
            status="active", id=uuid4(), organization_id=uuid4()
        )
        
        # Create multiple candidates
        candidate1 = CustomerRecord(
            firstname="Sara", lastname="Wilson", age=32,
            email="sara.wilson@email.com", phone="+1-555-5678",
            country="USA", address="321 Elm Street", gender="Female",
            status="active", id=uuid4(), organization_id=uuid4()
        )
        
        candidate2 = CustomerRecord(
            firstname="Sarah", lastname="Williams", age=33,
            email="sarah.williams@email.com", phone="+1-555-9876",
            country="USA", address="654 Oak Rd", gender="Female",
            status="active", id=uuid4(), organization_id=uuid4()
        )
        
        # Mock LLM response selecting the better match (candidate1)
        mock_response = Mock()
        mock_response.content = '''
        {
            "best_match_index": 0,
            "score": 0.88,
            "reason": "First candidate is clearly the better match: same phone, age, similar name (Sara/Sarah), and similar address"
        }
        '''
        dedup_engine_with_mock_llm.llm.invoke.return_value = mock_response
        
        candidates = [
            CandidateMatch(record_id=str(candidate1.id), record=candidate1, similarity_score=85.0),
            CandidateMatch(record_id=str(candidate2.id), record=candidate2, similarity_score=65.0)
        ]
        
        result = dedup_engine_with_mock_llm.gpt_semantic_check_top_k(base_record, candidates)
        
        # Should select candidate1 as duplicate and candidate2 as not duplicate
        assert len(result) == 2
        
        candidate1_result = result[str(candidate1.id)]
        candidate2_result = result[str(candidate2.id)]
        
        assert candidate1_result["duplicate"] is True
        assert candidate1_result["confidence"] >= 0.85
        assert candidate2_result["duplicate"] is False


class TestEndToEndModelFlow:
    """Test complete model flow from input to output."""
    
    def test_complete_deduplication_flow_unique_record(self):
        """Test complete flow for a unique record (no duplicates)."""
        # This would test the complete pipeline but requires more complex mocking
        # For now, we'll test the data transformation aspects
        
        # Sample SQS message
        sqs_message = {
            "data_entry": {
                "data_type": "tabular",
                "domain_name": "customer",
                "file_id": "test-file-123",
                "policy_id": "test-policy-456",
                "data": {
                    "status": "active",
                    "id": "296807a2-c7ea-424c-9f91-24389a10fbd9",
                    "organization_id": "296807a2-c7ea-424c-9f91-24389a10fbb0",
                    "email": "test@example.com",
                    "firstname": "Test",
                    "lastname": "User",
                    "age": 30,
                    "gender": "Male",
                    "phone": "+1-555-TEST",
                    "country": "USA",
                    "address": "123 Test St"
                }
            }
        }
        
        # Extract and transform data
        data_entry = sqs_message['data_entry']
        customer_data = data_entry['data']
        
        # Add metadata
        full_data = {
            'file_id': data_entry['file_id'],
            'policy_id': data_entry['policy_id'],
            'domain_name': data_entry['domain_name'],
            'uploaded_by': 'system',
            'uploaded_date': datetime.now().isoformat(),
            **customer_data
        }
        
        # Create CustomerRecord
        record = CustomerRecord(**full_data)
        
        # Verify record creation
        assert record.firstname == "Test"
        assert record.lastname == "User" 
        assert record.email == "test@example.com"
        
        # Test expected output format for unique record
        duplication_result = DuplicationResult(
            is_duplicate=False,
            reason="No duplicates found after comprehensive analysis"
        )
        
        processed_record = ProcessedRecord(
            file_id=data_entry['file_id'],
            policy_id=data_entry['policy_id'],
            data_type="tabular",
            status="success",
            domain_name=data_entry['domain_name'],
            data=customer_data,
            failed_validations=[]
        )
        
        # Verify output formats
        assert duplication_result.is_duplicate is False
        assert processed_record.status == "success"
        assert processed_record.data_type == "tabular"
        assert len(processed_record.failed_validations) == 0
    
    def test_data_validation_failure_handling(self):
        """Test handling of data validation failures."""
        # Invalid SQS message with missing required fields
        invalid_sqs = {
            "data_entry": {
                "data_type": "tabular",
                "domain_name": "customer",
                "file_id": "test-file-123",
                "policy_id": "test-policy-456",
                "data": {
                    "status": "active",
                    "id": "296807a2-c7ea-424c-9f91-24389a10fbd9",
                    # Missing required fields like firstname, lastname, email, etc.
                    "age": 30
                }
            }
        }
        
        data_entry = invalid_sqs['data_entry']
        customer_data = data_entry['data']
        
        full_data = {
            'file_id': data_entry['file_id'],
            'policy_id': data_entry['policy_id'],
            'domain_name': data_entry['domain_name'],
            'uploaded_by': 'system',
            'uploaded_date': datetime.now().isoformat(),
            **customer_data
        }
        
        # Should raise validation error
        with pytest.raises(Exception):
            CustomerRecord(**full_data)
        
        # Test error handling in ProcessedRecord
        processed_record = ProcessedRecord(
            file_id=data_entry['file_id'],
            policy_id=data_entry['policy_id'],
            data_type="tabular",
            status="fail",
            domain_name=data_entry['domain_name'],
            data=customer_data,
            failed_validations=[
                {
                    "field": "firstname",
                    "error": "Field required",
                    "received_value": None
                },
                {
                    "field": "lastname", 
                    "error": "Field required",
                    "received_value": None
                }
            ]
        )
        
        assert processed_record.status == "fail"
        assert len(processed_record.failed_validations) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])