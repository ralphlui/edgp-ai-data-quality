#!/usr/bin/env python3
"""
Simple test script to verify the deduplication engine setup.
This script tests the core functionality without requiring AWS services.
"""

import sys
import os
from typing import List

# Add the project root to the Python path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

from models import CustomerRecord
from utils import compute_full_hash, compute_block_key, normalize_text_for_comparison
from test_utils import SAMPLE_RECORDS, validate_customer_record


def test_models():
    """Test the Pydantic models."""
    print("Testing Pydantic models...")
    
    for i, record_data in enumerate(SAMPLE_RECORDS[:2]):  # Test first 2 records
        try:
            record = CustomerRecord(**record_data)
            print(f"✓ Record {i+1} created successfully: {record.firstname} {record.lastname}")
        except Exception as e:
            print(f"✗ Record {i+1} failed: {e}")
            return False
    
    return True


def test_hash_functions():
    """Test the hash computation functions."""
    print("\nTesting hash functions...")
    
    record = CustomerRecord(**SAMPLE_RECORDS[0])
    
    # Test full hash
    full_hash = compute_full_hash(record)
    print(f"✓ Full hash computed: {full_hash[:16]}...")
    
    # Test block key
    block_key = compute_block_key(record)
    print(f"✓ Block key computed: {block_key}")
    
    # Test duplicate hash consistency
    record2 = CustomerRecord(**SAMPLE_RECORDS[2])  # Should be identical to record 0
    full_hash2 = compute_full_hash(record2)
    
    if full_hash == full_hash2:
        print("✓ Identical records produce identical hashes")
    else:
        print("✗ Hash consistency test failed")
        return False
    
    return True


def test_text_normalization():
    """Test text normalization."""
    print("\nTesting text normalization...")
    
    test_cases = [
        ("John Smith", "john smith"),
        ("  JANE DOE  ", "jane doe"),
        ("Bob O'Connor", "bob o'connor")
    ]
    
    for input_text, expected in test_cases:
        result = normalize_text_for_comparison(input_text)
        if result == expected:
            print(f"✓ '{input_text}' → '{result}'")
        else:
            print(f"✗ '{input_text}' → '{result}' (expected '{expected}')")
            return False
    
    return True


def test_validation():
    """Test record validation."""
    print("\nTesting record validation...")
    
    # Valid record
    valid_record = SAMPLE_RECORDS[0]
    if validate_customer_record(valid_record):
        print("✓ Valid record passed validation")
    else:
        print("✗ Valid record failed validation")
        return False
    
    # Invalid record (missing required field)
    invalid_record = {k: v for k, v in valid_record.items() if k != 'firstname'}
    if not validate_customer_record(invalid_record):
        print("✓ Invalid record correctly rejected")
    else:
        print("✗ Invalid record incorrectly accepted")
        return False
    
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Customer Record Deduplication AI Agent - Setup Test")
    print("=" * 60)
    
    tests = [
        test_models,
        test_hash_functions,
        test_text_normalization,
        test_validation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        else:
            print("Test failed!")
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All tests passed! The setup is working correctly.")
        print("\nNext steps:")
        print("1. Copy .env.template to .env and fill in your AWS credentials")
        print("2. Set up your AWS SQS queues and DynamoDB table")
        print("3. Run 'python main.py' to start the AI agent")
    else:
        print("✗ Some tests failed. Please check the error messages above.")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
