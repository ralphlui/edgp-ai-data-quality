"""
Debug test to investigate the GPT logic issue.
"""

import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import Mock, patch
from uuid import uuid4

from src.models import CustomerRecord, CandidateMatch
from src.deduplication_engine import DeduplicationEngine


class TestGPTLogicDebug:
    """Test class to debug the GPT decision logic."""
    
    @pytest.fixture
    def dedup_engine(self):
        """Create a deduplication engine with mocked dependencies."""
        with patch('src.deduplication_engine.DynamoDBService'), \
             patch('src.deduplication_engine.ChatOpenAI'):
            engine = DeduplicationEngine()
            # Mock the LLM
            engine.llm = Mock()
            return engine
    
    @pytest.fixture
    def sample_record(self):
        """Create a sample customer record."""
        return CustomerRecord(
            firstname="John",
            lastname="Smith",
            age=30,
            email="john.smith@example.com",
            phone="+1-555-0123",
            country="USA",
            address="123 Main St",
            gender="Male",
            status="active",
            id=uuid4(),
            organization_id=uuid4()
        )
    
    def test_gpt_logic_with_multiple_candidates(self, dedup_engine, sample_record):
        """Test GPT logic with multiple candidates to reproduce the issue."""
        
        # Create multiple candidates
        candidate1 = CustomerRecord(
            firstname="John",
            lastname="Smith", 
            age=30,
            email="john.smith@example.com",  # Exact match
            phone="+1-555-0123",
            country="USA",
            address="123 Main St",
            gender="Male",
            status="active",
            id=uuid4(),
            organization_id=uuid4()
        )
        
        candidate2 = CustomerRecord(
            firstname="Jon",
            lastname="Smyth",
            age=29,
            email="jon.smyth@email.com",  # Different email
            phone="+1-555-0199",
            country="USA", 
            address="456 Oak St",
            gender="Male",
            status="active",
            id=uuid4(),
            organization_id=uuid4()
        )
        
        candidate_matches = [
            CandidateMatch(
                record_id=str(candidate1.id),
                record=candidate1,
                similarity_score=95.0  # High similarity
            ),
            CandidateMatch(
                record_id=str(candidate2.id),
                record=candidate2,
                similarity_score=75.0  # Lower similarity
            )
        ]
        
        # Mock GPT response - selects first candidate (index 0) with high confidence
        mock_response = Mock()
        mock_response.content = '''
        {
          "best_match_index": 0,
          "score": 0.85,
          "reason": "Exact email and phone match with similar name spelling"
        }
        '''
        dedup_engine.llm.invoke.return_value = mock_response
        
        # Call the GPT semantic check
        result = dedup_engine.gpt_semantic_check_top_k(sample_record, candidate_matches)
        
        print(f"\n=== GPT Results Debug ===")
        for candidate_id, gpt_result in result.items():
            print(f"Candidate {candidate_id}: duplicate={gpt_result['duplicate']}, confidence={gpt_result['confidence']}")
        
        # Verify results
        assert len(result) == 2, "Should have results for both candidates"
        
        # First candidate should be marked as duplicate
        candidate1_result = result[str(candidate1.id)]
        assert candidate1_result["duplicate"] is True, "First candidate should be marked as duplicate"
        assert candidate1_result["confidence"] == 0.85, "First candidate should have GPT confidence"
        
        # Second candidate should NOT be marked as duplicate  
        candidate2_result = result[str(candidate2.id)]
        assert candidate2_result["duplicate"] is False, "Second candidate should NOT be duplicate"
        assert candidate2_result["confidence"] == 0.0, "Second candidate should have 0 confidence"
        
        print("✅ GPT logic working correctly - issue must be elsewhere")
    
    def test_gpt_logic_edge_case_threshold(self, dedup_engine, sample_record):
        """Test GPT logic at the confidence threshold boundary."""
        
        candidate = CustomerRecord(
            firstname="John",
            lastname="Smith",
            age=30,
            email="john.smith@different.com",
            phone="+1-555-0123", 
            country="USA",
            address="123 Main St",
            gender="Male",
            status="active",
            id=uuid4(),
            organization_id=uuid4()
        )
        
        candidate_match = CandidateMatch(
            record_id=str(candidate.id),
            record=candidate,
            similarity_score=75.0
        )
        
        # Test exactly at threshold (0.70)
        mock_response = Mock()
        mock_response.content = '''
        {
          "best_match_index": 0,
          "score": 0.70,
          "reason": "At threshold boundary"
        }
        '''
        dedup_engine.llm.invoke.return_value = mock_response
        
        result = dedup_engine.gpt_semantic_check_top_k(sample_record, [candidate_match])
        
        # At threshold, should NOT be duplicate (score must be > threshold)
        candidate_result = result[str(candidate.id)]
        assert candidate_result["duplicate"] is False, "At threshold should NOT be duplicate"
        assert candidate_result["confidence"] == 0.70, "Should have GPT confidence value"
        
        print("✅ Threshold logic working correctly")