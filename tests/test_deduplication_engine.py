#!/usr/bin/env python3
"""
Comprehensive tests for the DeduplicationEngine class.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch
from datetime import datetime
from uuid import uuid4

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models import CustomerRecord, DuplicationResult
from deduplication_engine import DeduplicationEngine


class TestDeduplicationEngine:
    """Test cases for DeduplicationEngine."""
    
    @pytest.fixture
    def mock_dynamodb_service(self):
        """Create a mock DynamoDB service."""
        mock_service = Mock()
        mock_service.get_candidates_by_block_key.return_value = []
        mock_service.store_record.return_value = None
        return mock_service
    
    @pytest.fixture
    def dedup_engine(self, mock_dynamodb_service):
        """Create a DeduplicationEngine instance with mocked dependencies."""
        with patch('deduplication_engine.ChatOpenAI'):
            return DeduplicationEngine(mock_dynamodb_service)
    
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
            address="123 Main St, Anytown",
            gender="Male",
            
            id=uuid4(),
            organization_id=uuid4(),
            policy_id=uuid4(),
            uploaded_by="test_user",
            uploaded_date=datetime.now(),
            domain_name="example.com",
            file_id=uuid4()
        )
    
    def test_exact_match_detection(self, dedup_engine, mock_dynamodb_service, sample_customer_record):
        """Test exact match detection."""
        # Mock exact match found
        mock_dynamodb_service.exact_match.return_value = sample_customer_record
        
        result = dedup_engine.check_duplicate(sample_customer_record)
        
        assert result.is_duplicate is True
        assert "Exact Match" in result.reason
        assert result.confidence_score == 1.0
    
    def test_no_duplicate_found(self, dedup_engine, mock_dynamodb_service, sample_customer_record):
        """Test when no duplicate is found."""
        # Mock no exact match and no fuzzy matches
        mock_dynamodb_service.exact_match.return_value = None
        mock_dynamodb_service.fetch_candidates.return_value = []
        
        result = dedup_engine.check_duplicate(sample_customer_record)
        
        assert result.is_duplicate is False
        assert "No Match" in result.reason
    
    def test_fuzzy_match_detection(self, dedup_engine, mock_dynamodb_service, sample_customer_record):
        """Test fuzzy match detection."""
        # Create a similar record
        similar_record = CustomerRecord(
            firstname="Jon",  # Slight variation
            lastname="Smith",
            age=35,
            email="john.smith@example.com",
            phone="+1-555-0123",
            country="USA",
            address="123 Main St, Anytown", 
            gender="Male",
            
            id=uuid4(),
            organization_id=sample_customer_record.organization_id,  # Same org
            policy_id=uuid4(),
            uploaded_by="test_user",
            uploaded_date=datetime.now(),
            domain_name="example.com",
            file_id=uuid4()
        )
        
        # Mock no exact match but fuzzy match candidates
        mock_dynamodb_service.exact_match.return_value = None
        # Return raw DynamoDB-style items, not CustomerRecord objects
        mock_dynamodb_service.fetch_candidates.return_value = [{
            'firstname': similar_record.firstname,
            'lastname': similar_record.lastname,
            'age': similar_record.age,
            'email': similar_record.email,
            'phone': similar_record.phone,
            'country': similar_record.country,
            'address': similar_record.address,
            'gender': similar_record.gender,
            'id': str(similar_record.id),
            'organization_id': str(similar_record.organization_id)
        }]
        
        result = dedup_engine.check_duplicate(sample_customer_record)
        
        # Should find fuzzy match
        assert result.is_duplicate is True
        assert "Fuzzy Match" in result.reason
        assert result.confidence_score >= 0.85
    
    @patch('deduplication_engine.ChatOpenAI')
    def test_gpt_semantic_analysis(self, mock_chat_openai, dedup_engine, mock_dynamodb_service, sample_customer_record):
        """Test GPT semantic analysis."""
        # Create a record that's similar but below fuzzy threshold
        different_record = CustomerRecord(
            firstname="Johnny",
            lastname="Smyth", 
            age=36,
            email="johnny.smyth@company.com",
            phone="+1-555-9999",
            country="Canada",
            address="456 Oak Ave, Different City",
            gender="Male",
            
            id=uuid4(),
            organization_id=uuid4(),
            policy_id=uuid4(),
            uploaded_by="test_user",
            uploaded_date=datetime.now(),
            domain_name="example.com",
            file_id=uuid4()
        )
        
        # Mock GPT response indicating a match
        mock_response = Mock()
        mock_response.content = '{"best_match_index": 0, "score": 0.85}'
        
        # Patch the actual LLM instance instead of the class
        dedup_engine.llm.invoke.return_value = mock_response
        
        # Mock no exact/fuzzy matches but GPT candidates  
        mock_dynamodb_service.exact_match.return_value = None
        # Return raw DynamoDB-style items, not CustomerRecord objects
        mock_dynamodb_service.fetch_candidates.return_value = [{
            'firstname': different_record.firstname,
            'lastname': different_record.lastname,
            'age': different_record.age,
            'email': different_record.email,
            'phone': different_record.phone,
            'country': different_record.country,
            'address': different_record.address,
            'gender': different_record.gender,
            'id': str(different_record.id),
            'organization_id': str(different_record.organization_id)
        }]
        
        # Patch compute_weighted_similarity to return low score
        with patch('deduplication_engine.compute_weighted_similarity', return_value=0.70):
            result = dedup_engine.check_duplicate(sample_customer_record)
        
        assert result.is_duplicate is True
        assert "Semantic Check" in result.reason
    
    def test_blocking_strategy(self, dedup_engine, sample_customer_record):
        """Test the blocking strategy generates correct keys."""
        from utils import compute_block_key
        
        block_key = compute_block_key(sample_customer_record)
        
        # Should be first char of normalized firstname|lastname|email
        expected_key = "j|s|j"  # john -> j, smith -> s, john.smith@example.com -> j
        assert block_key == expected_key
    
    def test_error_handling(self, dedup_engine, mock_dynamodb_service, sample_customer_record):
        """Test error handling in deduplication process."""
        # Mock DynamoDB error
        mock_dynamodb_service.exact_match.side_effect = Exception("DynamoDB error")
        
        # Should handle the error gracefully
        with pytest.raises(Exception):
            dedup_engine.check_duplicate(sample_customer_record)
    
    def test_fetch_candidates_empty_list(self, dedup_engine, sample_customer_record):
        """Test fetch_candidates with empty candidate list."""
        dedup_engine.dynamodb_service.fetch_candidates.return_value = []
        
        candidates = dedup_engine.fetch_candidates(sample_customer_record)
        
        assert candidates == []
        dedup_engine.dynamodb_service.fetch_candidates.assert_called_once_with(sample_customer_record)
    
    def test_fetch_candidates_with_invalid_data(self, dedup_engine, sample_customer_record):
        """Test fetch_candidates handling invalid candidate data."""
        # Mock candidates with missing/invalid data
        invalid_candidates = [
            {'firstname': 'Jane', 'lastname': 'Doe'},  # Missing required fields
            {'firstname': 'Bob', 'lastname': 'Smith', 'age': 'invalid', 'email': 'bob@test.com'},  # Invalid age
            {
                'firstname': 'Valid',
                'lastname': 'User',
                'age': 30,
                'email': 'valid@test.com',
                'phone': '+1-555-0199',
                'country': 'USA',
                'address': '456 Oak St',
                'gender': 'Female',
                'id': str(uuid4()),
                'organization_id': str(uuid4())
            }  # Valid candidate
        ]
        dedup_engine.dynamodb_service.fetch_candidates.return_value = invalid_candidates
        
        candidates = dedup_engine.fetch_candidates(sample_customer_record)
        
        # Should only return valid candidates (1 out of 3)
        assert len(candidates) == 1
        assert candidates[0].firstname == 'Valid'
    
    def test_fuzzy_match_top_k_empty_candidates(self, dedup_engine, sample_customer_record):
        """Test fuzzy matching with empty candidates list."""
        result = dedup_engine.fuzzy_match_top_k(sample_customer_record, [])
        
        assert result == []
    
    def test_fuzzy_match_top_k_high_similarity(self, dedup_engine, sample_customer_record):
        """Test fuzzy matching with high similarity candidates."""
        # Create similar candidate
        similar_candidate = CustomerRecord(
            firstname="Jon",  # Slightly different
            lastname="Smith",
            age=35,
            email="jon.smith@example.com",
            phone="+1-555-0123",
            country="USA",
            address="123 Main St, Anytown",
            gender="Male",
            
            id=uuid4(),
            organization_id=sample_customer_record.organization_id  # Same org
        )
        
        matches = dedup_engine.fuzzy_match_top_k(sample_customer_record, [similar_candidate])
        
        assert len(matches) == 1
        assert matches[0].similarity_score > 80  # Should be high similarity
    
    def test_fuzzy_match_top_k_low_similarity(self, dedup_engine, sample_customer_record):
        """Test fuzzy matching with low similarity candidates."""
        # Create dissimilar candidate
        different_candidate = CustomerRecord(
            firstname="Alice",
            lastname="Johnson",
            age=25,
            email="alice.johnson@different.com",
            phone="+1-555-9999",
            country="Canada",
            address="789 Different St",
            gender="Female",
            
            id=uuid4(),
            organization_id=uuid4()  # Different org
        )
        
        matches = dedup_engine.fuzzy_match_top_k(sample_customer_record, [different_candidate])
        
        assert len(matches) == 1
        assert matches[0].similarity_score < 50  # Should be low similarity
    
    def test_gpt_semantic_check_empty_candidates(self, dedup_engine, sample_customer_record):
        """Test GPT semantic check with empty candidates."""
        result = dedup_engine.gpt_semantic_check_top_k(sample_customer_record, [])
        
        assert result == {}
    
    def test_gpt_semantic_check_json_extraction_failure(self, dedup_engine, sample_customer_record):
        """Test GPT semantic check with invalid JSON response."""
        from models import CandidateMatch
        
        # Create mock candidate
        candidate = CustomerRecord(
            firstname="Jane",
            lastname="Doe",
            age=30,
            email="jane@test.com",
            phone="+1-555-0199",
            country="USA",
            address="456 Oak St",
            gender="Female",
            
            id=uuid4(),
            organization_id=uuid4()
        )
        
        candidate_match = CandidateMatch(
            record_id=str(candidate.id),
            record=candidate,
            similarity_score=75.0
        )
        
        # Mock LLM response with invalid JSON
        mock_response = Mock()
        mock_response.content = "This is not valid JSON response"
        dedup_engine.llm.invoke.return_value = mock_response
        
        result = dedup_engine.gpt_semantic_check_top_k(sample_customer_record, [candidate_match])
        
        # Should return empty result when JSON extraction fails
        assert len(result) == 0
        assert result == {}
    
    def test_gpt_semantic_check_exception_handling(self, dedup_engine, sample_customer_record):
        """Test GPT semantic check with exception during LLM call."""
        from models import CandidateMatch
        
        candidate = CustomerRecord(
            firstname="Jane",
            lastname="Doe",
            age=30,
            email="jane@test.com",
            phone="+1-555-0199",
            country="USA",
            address="456 Oak St",
            gender="Female",
            
            id=uuid4(),
            organization_id=uuid4()
        )
        
        candidate_match = CandidateMatch(
            record_id=str(candidate.id),
            record=candidate,
            similarity_score=75.0
        )
        
        # Mock LLM to raise exception
        dedup_engine.llm.invoke.side_effect = Exception("API Error")
        
        result = dedup_engine.gpt_semantic_check_top_k(sample_customer_record, [candidate_match])
        
        # Should return conservative result (no duplicates)
        assert len(result) == 1
        assert result[str(candidate.id)]["duplicate"] is False
        assert result[str(candidate.id)]["confidence"] == 0.0
    
    def test_is_duplicate_no_candidates_found(self, dedup_engine, sample_customer_record):
        """Test is_duplicate when no candidates are found."""
        # Mock no exact match and no candidates
        dedup_engine.dynamodb_service.exact_match.return_value = None
        dedup_engine.dynamodb_service.fetch_candidates.return_value = []
        
        result = dedup_engine.is_duplicate(sample_customer_record)
        
        assert result.is_duplicate is False
        assert result.reason == "No Match"
        assert result.confidence_score == 0.95
    
    def test_check_duplicate_alias(self, dedup_engine, sample_customer_record):
        """Test that check_duplicate is an alias for is_duplicate."""
        # Mock exact match
        dedup_engine.dynamodb_service.exact_match.return_value = {'full_hash': 'test_hash'}
        
        result1 = dedup_engine.is_duplicate(sample_customer_record)
        result2 = dedup_engine.check_duplicate(sample_customer_record)
        
        assert result1.is_duplicate == result2.is_duplicate
        assert result1.reason == result2.reason
        assert result1.confidence_score == result2.confidence_score
    
    def test_process_record_unique_customer(self, dedup_engine, sample_customer_record):
        """Test process_record for unique customer."""
        # Mock no duplicate found
        dedup_engine.dynamodb_service.exact_match.return_value = None
        dedup_engine.dynamodb_service.fetch_candidates.return_value = []
        dedup_engine.dynamodb_service.store_record.return_value = True
        
        result = dedup_engine.process_record(sample_customer_record)
        
        assert result.status == "success"
        assert len(result.failed_validations) == 0
        assert result.data["id"] == str(sample_customer_record.id)
        
        # Verify record was stored
        dedup_engine.dynamodb_service.store_record.assert_called_once()
    
    def test_process_record_duplicate_customer(self, dedup_engine, sample_customer_record):
        """Test process_record for duplicate customer."""
        # Mock duplicate found
        dedup_engine.dynamodb_service.exact_match.return_value = {'full_hash': 'test_hash'}
        
        result = dedup_engine.process_record(sample_customer_record)
        
        assert result.status == "fail"
        assert len(result.failed_validations) == 1
        assert result.failed_validations[0]["rule_name"] == "NoRecordDuplication"
        assert "100%" in result.failed_validations[0]["error_message"]
        
        # Verify record was NOT stored
        dedup_engine.dynamodb_service.store_record.assert_not_called()
    
    def test_process_record_storage_failure(self, dedup_engine, sample_customer_record):
        """Test process_record when storage fails."""
        # Mock no duplicate but storage fails
        dedup_engine.dynamodb_service.exact_match.return_value = None
        dedup_engine.dynamodb_service.fetch_candidates.return_value = []
        dedup_engine.dynamodb_service.store_record.return_value = False
        
        result = dedup_engine.process_record(sample_customer_record)
        
        # Should still succeed even if storage fails
        assert result.status == "success"
        assert len(result.failed_validations) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
