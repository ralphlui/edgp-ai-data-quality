"""
Comprehensive tests for utility functions to improve code coverage.
"""

import pytest
import sys
import os
import logging
from uuid import uuid4
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models import CustomerRecord
from utils import (
    setup_logging,
    compute_full_hash,
    compute_block_key,
    normalize_text_for_comparison,
    format_record_for_gpt,
    create_gpt_prompt,
    create_gpt_prompt_best_match_with_score,
    compute_weighted_similarity
)


class TestUtilityFunctions:
    """Comprehensive tests for utility functions."""
    
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
            address="123 Main Street",
            gender="Male",
            
            id=uuid4(),
            organization_id=uuid4(),
            policy_id=uuid4(),
            uploaded_by="test_user",
            uploaded_date=datetime.now(),
            domain_name="customer",
            file_id=uuid4()
        )
    
    def test_setup_logging_default_level(self):
        """Test setup_logging with default level."""
        # Reset logging configuration first
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        
        logger = setup_logging()
        
        assert isinstance(logger, logging.Logger)
        # The root logger level should be set to INFO (20) after setup
        assert logging.getLogger().level == logging.INFO
    
    def test_compute_full_hash_identical_records(self, sample_customer_record):
        """Test that identical records produce the same hash."""
        # Create another record with same data
        identical_record = CustomerRecord(
            firstname=sample_customer_record.firstname,
            lastname=sample_customer_record.lastname,
            age=sample_customer_record.age,
            email=sample_customer_record.email,
            phone=sample_customer_record.phone,
            country=sample_customer_record.country,
            address=sample_customer_record.address,
            gender=sample_customer_record.gender,
            id=uuid4(),  # Different ID shouldn't affect hash
            organization_id=sample_customer_record.organization_id,
            policy_id=uuid4(),
            uploaded_by="different_user",
            uploaded_date=datetime.now(),
            domain_name="customer",
            file_id=uuid4()
        )
        
        hash1 = compute_full_hash(sample_customer_record)
        hash2 = compute_full_hash(identical_record)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 produces 64 character hex string
    
    def test_compute_block_key_normal_case(self, sample_customer_record):
        """Test block key computation for normal case."""
        block_key = compute_block_key(sample_customer_record)
        
        expected_key = "j|s|j"  # john -> j, smith -> s, john.smith@example.com -> j
        assert block_key == expected_key
    
    def test_compute_block_key_empty_fields(self):
        """Test block key computation with empty fields."""
        record = CustomerRecord(
            firstname="",
            lastname="",
            age=35,
            email="",
            phone="+1-555-0123",
            country="USA",
            address="123 Main Street",
            gender="Male",
            
            id=uuid4(),
            organization_id=uuid4(),
            policy_id=uuid4(),
            uploaded_by="test",
            uploaded_date=datetime.now(),
            domain_name="customer",
            file_id=uuid4()
        )
        
        block_key = compute_block_key(record)
        
        expected_key = "x|x|x"  # Default fallback for empty fields
        assert block_key == expected_key
    
    def test_normalize_text_for_comparison(self):
        """Test text normalization function."""
        test_cases = [
            ("  HELLO WORLD  ", "hello world"),
            ("Mixed Case Text", "mixed case text"),
            ("", ""),
            ("   ", ""),
            ("NoSpaces", "nospaces"),
            ("123 Numbers!", "123 numbers!")
        ]
        
        for input_text, expected in test_cases:
            result = normalize_text_for_comparison(input_text)
            assert result == expected
    
    def test_format_record_for_gpt(self, sample_customer_record):
        """Test GPT record formatting."""
        formatted = format_record_for_gpt(sample_customer_record)
        
        assert "FirstName: John" in formatted
        assert "LastName: Smith" in formatted
        assert "Age: 35" in formatted
        assert "Email: john.smith@example.com" in formatted
    
    def test_create_gpt_prompt_single_candidate(self, sample_customer_record):
        """Test GPT prompt creation with single candidate."""
        similar_record = CustomerRecord(
            firstname="Jon",
            lastname="Smith",
            age=35,
            email="j.smith@example.com",
            phone="+1-555-0123",
            country="USA",
            address="123 Main St",
            gender="Male",
            
            id=uuid4(),
            organization_id=uuid4(),
            policy_id=uuid4(),
            uploaded_by="test",
            uploaded_date=datetime.now(),
            domain_name="customer",
            file_id=uuid4()
        )
        
        candidates = [similar_record]
        prompt = create_gpt_prompt(sample_customer_record, candidates)
        
        assert "NEW CUSTOMER RECORD" in prompt
        assert "CANDIDATE RECORDS" in prompt
        assert "FirstName: John" in prompt
        assert "FirstName: Jon" in prompt
    
    def test_compute_weighted_similarity_identical_records(self, sample_customer_record):
        """Test weighted similarity for identical records."""
        # Create identical record
        identical_record = CustomerRecord(
            firstname=sample_customer_record.firstname,
            lastname=sample_customer_record.lastname,
            age=sample_customer_record.age,
            email=sample_customer_record.email,
            phone=sample_customer_record.phone,
            country=sample_customer_record.country,
            address=sample_customer_record.address,
            gender=sample_customer_record.gender,
            id=uuid4(),
            organization_id=uuid4(),
            policy_id=uuid4(),
            uploaded_by="test",
            uploaded_date=datetime.now(),
            domain_name="customer",
            file_id=uuid4()
        )
        
        similarity = compute_weighted_similarity(sample_customer_record, identical_record)
        
        assert similarity == 1.0


# Sample customer records for testing (kept for backward compatibility)
SAMPLE_RECORDS = [
    {
        "firstname": "John",
        "lastname": "Smith",
        "age": 30,
        "email": "john.smith@email.com",
        "phone": "+1-555-0123",
        "country": "USA",
        "address": "123 Main St, New York, NY 10001",
        "gender": "Male",
        
        "id": uuid4(),
        "organization_id": uuid4()
    },
    {
        "firstname": "Jane",
        "lastname": "Doe",
        "age": 25,
        "email": "jane.doe@email.com",
        "phone": "+1-555-0456",
        "country": "USA",
        "address": "456 Oak Ave, Los Angeles, CA 90001",
        "gender": "Female",
        
        "id": uuid4(),
        "organization_id": uuid4()
    }
]


def validate_customer_record(record_data):
    """Validate that a customer record has all required fields."""
    required_fields = ['firstname', 'lastname', 'email', 'age']
    for field in required_fields:
        if field not in record_data or not record_data[field]:
            return False
    return True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])