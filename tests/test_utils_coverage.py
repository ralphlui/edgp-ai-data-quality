"""
Simple coverage tests for utility functions.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch
import uuid

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.utils import compute_weighted_similarity
from src.models import CustomerRecord


class TestUtilsCoverage:
    """Simple tests to improve coverage for utils module."""

    def test_compute_weighted_similarity_age_exact_match(self):
        """Test compute_weighted_similarity with exact age match."""
        record1 = CustomerRecord(
            id=str(uuid.uuid4()),
            firstname="John",
            lastname="Doe",
            email="john@test.com",
            phone="123-456-7890",
            address="123 Main St",
            country="USA",
            gender="Male",
            age=30,
            organization_id=str(uuid.uuid4())
        )
        
        record2 = CustomerRecord(
            id=str(uuid.uuid4()),
            firstname="John",
            lastname="Doe", 
            email="john@test.com",
            phone="123-456-7890",
            address="123 Main St",
            country="USA",
            gender="Male",
            age=30,  # Same age
            organization_id=str(uuid.uuid4())
        )
        
        # Use default weights that include age
        weights = {
            'firstname': 0.2,
            'lastname': 0.2,
            'email': 0.3,
            'phone': 0.2,
            'age': 0.1
        }
        
        similarity = compute_weighted_similarity(record1, record2, weights)
        assert similarity > 0.9  # Should be very high since all fields match

    def test_compute_weighted_similarity_age_close_match(self):
        """Test compute_weighted_similarity with close age match."""
        record1 = CustomerRecord(
            id=str(uuid.uuid4()),
            firstname="John",
            lastname="Doe",
            email="john@test.com",
            phone="123-456-7890",
            address="123 Main St",
            country="USA",
            gender="Male",
            age=30,
            organization_id=str(uuid.uuid4())
        )
        
        record2 = CustomerRecord(
            id=str(uuid.uuid4()),
            firstname="John",
            lastname="Doe",
            email="john@test.com", 
            phone="123-456-7890",
            address="123 Main St",
            country="USA",
            gender="Male",
            age=32,  # 2 years difference
            organization_id=str(uuid.uuid4())
        )
        
        weights = {
            'firstname': 0.2,
            'lastname': 0.2,
            'email': 0.3,
            'phone': 0.2,
            'age': 0.1
        }
        
        similarity = compute_weighted_similarity(record1, record2, weights)
        # Should be high but not perfect due to age difference
        assert 0.95 < similarity < 1.0

    def test_compute_weighted_similarity_age_medium_difference(self):
        """Test compute_weighted_similarity with medium age difference."""
        record1 = CustomerRecord(
            id=str(uuid.uuid4()),
            firstname="John",
            lastname="Doe",
            email="john@test.com",
            phone="123-456-7890",
            address="123 Main St",
            country="USA",
            gender="Male",
            age=30,
            organization_id=str(uuid.uuid4())
        )
        
        record2 = CustomerRecord(
            id=str(uuid.uuid4()),
            firstname="John",
            lastname="Doe",
            email="john@test.com",
            phone="123-456-7890",
            address="123 Main St",
            country="USA", 
            gender="Male",
            age=34,  # 4 years difference (within 5 year range)
            organization_id=str(uuid.uuid4())
        )
        
        weights = {
            'firstname': 0.2,
            'lastname': 0.2,
            'email': 0.3,
            'phone': 0.2,
            'age': 0.1
        }
        
        similarity = compute_weighted_similarity(record1, record2, weights)
        # Should be good but lower due to age difference
        assert 0.9 < similarity < 1.0

    def test_compute_weighted_similarity_age_large_difference(self):
        """Test compute_weighted_similarity with large age difference."""
        record1 = CustomerRecord(
            id=str(uuid.uuid4()),
            firstname="John",
            lastname="Doe",
            email="john@test.com",
            phone="123-456-7890",
            address="123 Main St",
            country="USA",
            gender="Male",
            age=30,
            organization_id=str(uuid.uuid4())
        )
        
        record2 = CustomerRecord(
            id=str(uuid.uuid4()),
            firstname="John",
            lastname="Doe",
            email="john@test.com",
            phone="123-456-7890",
            address="123 Main St",
            country="USA",
            gender="Male",
            age=50,  # 20 years difference (>5 years)
            organization_id=str(uuid.uuid4())
        )
        
        weights = {
            'firstname': 0.2,
            'lastname': 0.2,
            'email': 0.3,
            'phone': 0.2,
            'age': 0.1
        }
        
        similarity = compute_weighted_similarity(record1, record2, weights)
        # Should be lower due to large age difference
        assert 0.85 < similarity < 0.95