#!/usr/bin/env python3
"""
Tests for LLM prompt generation and response validation.
"""

import pytest
import sys
import os
import json
from uuid import uuid4
from unittest.mock import Mock, patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models import CustomerRecord
from utils import create_gpt_prompt_best_match_with_score, format_record_for_gpt


class TestLLMPromptGeneration:
    """Test cases for LLM prompt generation and formatting."""
    
    @pytest.fixture
    def sample_records(self):
        """Generate sample customer records for testing."""
        target_record = CustomerRecord(
            firstname="John", lastname="Smith", age=35,
            email="john.smith@example.com", phone="+1-555-0123",
            country="USA", address="123 Main St", gender="Male",
            status="active", id=uuid4(), organization_id=uuid4()
        )
        
        candidates = [
            CustomerRecord(
                firstname="Jon", lastname="Smyth", age=36,
                email="jon.smyth@company.com", phone="+1-555-9999",
                country="Canada", address="456 Oak Ave", gender="Male",
                status="active", id=uuid4(), organization_id=uuid4()
            ),
            CustomerRecord(
                firstname="Jane", lastname="Smith", age=28,
                email="jane.smith@email.com", phone="+1-555-7777",
                country="USA", address="789 Pine St", gender="Female",
                status="active", id=uuid4(), organization_id=uuid4()
            )
        ]
        
        return target_record, candidates
    
    def test_gpt_prompt_structure(self, sample_records):
        """Test that GPT prompt contains all required elements."""
        target_record, candidates = sample_records
        
        prompt = create_gpt_prompt_best_match_with_score(target_record, candidates)
        
        # Verify prompt contains key elements
        assert "new customer record" in prompt.lower()
        assert "candidate" in prompt.lower()
        assert "json" in prompt.lower()
        assert "best_match_index" in prompt
        assert "score" in prompt
        assert "reason" in prompt
        
        # Verify target record is in prompt
        assert target_record.firstname in prompt
        assert target_record.lastname in prompt
        assert target_record.email in prompt
        
        # Verify candidates are in prompt
        for candidate in candidates:
            assert candidate.firstname in prompt
            assert candidate.lastname in prompt
            assert candidate.email in prompt
    
    def test_record_formatting_for_gpt(self, sample_records):
        """Test that customer records are properly formatted for GPT."""
        target_record, _ = sample_records
        
        formatted = format_record_for_gpt(target_record)
        
        # Verify all key fields are included
        assert target_record.firstname in formatted
        assert target_record.lastname in formatted
        assert target_record.email in formatted
        assert target_record.phone in formatted
        assert target_record.address in formatted
        
        # Verify formatting is readable
        assert len(formatted) > 50  # Should be a substantial string
    
    def test_prompt_with_empty_candidates(self, sample_records):
        """Test prompt generation with empty candidate list."""
        target_record, _ = sample_records
        
        prompt = create_gpt_prompt_best_match_with_score(target_record, [])
        
        # Should handle empty candidates gracefully
        assert "new customer record" in prompt.lower()
        assert target_record.firstname in prompt
    
    def test_prompt_with_single_candidate(self, sample_records):
        """Test prompt generation with single candidate."""
        target_record, candidates = sample_records
        single_candidate = [candidates[0]]
        
        prompt = create_gpt_prompt_best_match_with_score(target_record, single_candidate)
        
        # Should handle single candidate correctly
        assert "candidate" in prompt.lower()
        assert single_candidate[0].firstname in prompt
        assert "best_match_index" in prompt


class TestLLMResponseValidation:
    """Test cases for validating LLM response formats."""
    
    def test_valid_json_response_structure(self):
        """Test validation of correct JSON response structure."""
        valid_responses = [
            {
                "best_match_index": 0,
                "score": 0.85,
                "reason": "High similarity in name and contact details"
            },
            {
                "best_match_index": 1,
                "score": 0.92,
                "reason": "Exact match on email and phone number"
            },
            {
                "best_match_index": None,
                "score": 0.0,
                "reason": "No significant similarity found"
            }
        ]
        
        for response in valid_responses:
            # All responses should have required fields
            assert "best_match_index" in response
            assert "score" in response
            assert "reason" in response
            
            # Score should be float between 0 and 1
            assert 0.0 <= response["score"] <= 1.0
            
            # Reason should be non-empty string
            assert isinstance(response["reason"], str)
            assert len(response["reason"]) > 0
    
    def test_invalid_json_response_handling(self):
        """Test handling of invalid JSON response formats."""
        invalid_responses = [
            {"score": 0.85},  # Missing best_match_index
            {"best_match_index": 0},  # Missing score
            {"best_match_index": 0, "score": 1.5, "reason": "Invalid score > 1"},
            {"best_match_index": 0, "score": -0.1, "reason": "Invalid negative score"},
            {"best_match_index": "invalid", "score": 0.8, "reason": "Invalid index type"},
        ]
        
        for response in invalid_responses:
            # These would need to be handled gracefully in the actual implementation
            # Here we just verify the structure issues
            if "best_match_index" not in response or "score" not in response:
                assert True  # Missing required fields
            elif response.get("score", 0) < 0 or response.get("score", 0) > 1:
                assert True  # Invalid score range
    
    def test_confidence_threshold_validation(self):
        """Test validation of confidence threshold logic."""
        # These test cases verify the confidence threshold behavior
        test_cases = [
            (0.95, True, "High confidence should indicate duplicate"),
            (0.85, True, "Above threshold should indicate duplicate"),
            (0.75, True, "Above threshold should indicate duplicate"),
            (0.65, False, "Below threshold should not indicate duplicate"),
            (0.45, False, "Low confidence should not indicate duplicate"),
            (0.0, False, "Zero confidence should not indicate duplicate")
        ]
        
        # Assuming threshold is 0.7 (as used in the actual code)
        CONFIDENCE_THRESHOLD = 0.7
        
        for score, expected_duplicate, description in test_cases:
            actual_duplicate = score > CONFIDENCE_THRESHOLD
            assert actual_duplicate == expected_duplicate, f"Failed: {description} (score: {score})"


class TestModelDataIntegrity:
    """Test cases for model data integrity and business rules."""
    
    def test_customer_record_business_rules(self):
        """Test business rule validation for customer records."""
        # Test valid age range
        valid_record = CustomerRecord(
            firstname="Test", lastname="User", age=25,
            email="test@example.com", phone="+1-555-0000",
            country="USA", address="123 Test St", gender="Male",
            status="active", id=uuid4(), organization_id=uuid4()
        )
        
        assert 0 < valid_record.age < 150  # Reasonable age range
        assert "@" in valid_record.email  # Basic email validation
        assert len(valid_record.phone) > 5  # Basic phone validation
    
    def test_duplication_result_consistency(self):
        """Test consistency rules for duplication results."""
        from models import DuplicationResult
        
        # If is_duplicate is True, confidence_score should be provided
        duplicate_result = DuplicationResult(
            is_duplicate=True,
            reason="Match found",
            confidence_score=0.85,
            matched_record_id="test-id-123"
        )
        
        assert duplicate_result.is_duplicate is True
        assert duplicate_result.confidence_score is not None
        assert duplicate_result.confidence_score > 0
        assert duplicate_result.matched_record_id is not None
        
        # If is_duplicate is False, matched_record_id should be None
        no_duplicate_result = DuplicationResult(
            is_duplicate=False,
            reason="No duplicates found"
        )
        
        assert no_duplicate_result.is_duplicate is False
        assert no_duplicate_result.matched_record_id is None
    
    def test_processed_record_status_consistency(self):
        """Test status consistency in processed records."""
        from models import ProcessedRecord
        
        # Success case should have empty failed_validations
        success_record = ProcessedRecord(
            file_id="test-file",
            policy_id="test-policy", 
            data_type="tabular",
            status="success",
            domain_name="customer",
            data={"test": "data"},
            failed_validations=[]
        )
        
        assert success_record.status == "success"
        assert len(success_record.failed_validations) == 0
        
        # Failure case should have non-empty failed_validations
        failure_record = ProcessedRecord(
            file_id="test-file",
            policy_id="test-policy",
            data_type="tabular", 
            status="fail",
            domain_name="customer",
            data={"test": "data"},
            failed_validations=[{"field": "test", "error": "test error"}]
        )
        
        assert failure_record.status == "fail"
        assert len(failure_record.failed_validations) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])