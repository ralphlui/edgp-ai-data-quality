#!/usr/bin/env python3
"""
Simple tests for deduplication_engine.py to improve code coverage.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch
from uuid import uuid4

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from deduplication_engine import DeduplicationEngine
from models import CustomerRecord


class TestDeduplicationEngineCoverage:
    """Simple tests to improve deduplication_engine.py coverage."""
    
    @pytest.fixture
    def sample_customer_record(self):
        """Create a sample customer record for testing."""
        return CustomerRecord(
            id=str(uuid4()),
            organization_id=str(uuid4()),
            policy_id=str(uuid4()),
            firstname="John",
            lastname="Smith", 
            age=30,
            email="john.smith@example.com",
            phone="+1-555-0123",
            country="USA",
            address="123 Main St",
            gender="Male",
            uploaded_by="test_user",
            uploaded_date="2023-01-01T00:00:00Z",
            domain_name="customer",
            file_id=str(uuid4())
        )
    
    def test_fetch_candidates_empty_result(self, sample_customer_record):
        """Test fetch_candidates when no candidates are found."""
        # Mock services
        mock_dynamodb = Mock()
        mock_dynamodb.fetch_candidates.return_value = []
        
        # Create engine
        engine = DeduplicationEngine(mock_dynamodb)
        
        # Test fetch_candidates
        candidates = engine.fetch_candidates(sample_customer_record)
        
        assert candidates == []
        mock_dynamodb.fetch_candidates.assert_called_once()
    
    def test_fetch_candidates_with_results(self, sample_customer_record):
        """Test fetch_candidates when candidates are found."""
        # Mock services
        mock_dynamodb = Mock()
        candidate_data = {
            'id': str(uuid4()),
            'organization_id': str(uuid4()),
            'policy_id': str(uuid4()),
            'firstname': 'Jane',
            'lastname': 'Smith',
            'age': 28,
            'email': 'jane.smith@example.com',
            'phone': '+1-555-9876',
            'country': 'USA',
            'address': '456 Oak Ave',
            'gender': 'Female',
            'uploaded_by': 'test_user',
            'uploaded_date': '2023-01-01T00:00:00Z',
            'domain_name': 'customer',
            'file_id': str(uuid4())
        }
        mock_dynamodb.fetch_candidates.return_value = [candidate_data]
        
        # Create engine
        engine = DeduplicationEngine(mock_dynamodb)
        
        # Test fetch_candidates
        candidates = engine.fetch_candidates(sample_customer_record)
        
        assert len(candidates) == 1
        assert isinstance(candidates[0], CustomerRecord)
        assert candidates[0].firstname == 'Jane'
        assert candidates[0].lastname == 'Smith'
    
    def test_fetch_candidates_invalid_data(self, sample_customer_record):
        """Test fetch_candidates with invalid candidate data."""
        # Mock services
        mock_dynamodb = Mock()
        # Return invalid data missing required fields
        invalid_data = {
            'id': str(uuid4()),
            'firstname': 'Invalid'
            # Missing many required fields
        }
        mock_dynamodb.fetch_candidates.return_value = [invalid_data]
        
        # Create engine
        engine = DeduplicationEngine(mock_dynamodb)
        
        # Test fetch_candidates - should handle invalid data gracefully
        candidates = engine.fetch_candidates(sample_customer_record)
        
        # The function should still return the candidates list
        # (it doesn't validate the structure, just converts to CustomerRecord objects)
        assert isinstance(candidates, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])