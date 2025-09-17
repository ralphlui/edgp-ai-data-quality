#!/usr/bin/env python3
"""
Test script to validate the new customer record fields and functionality.
"""

import json
from datetime import datetime
from uuid import uuid4

from models import CustomerRecord
from utils import compute_full_hash, compute_block_key, format_record_for_gpt

def test_new_customer_model():
    """Test the new CustomerRecord model with all fields."""
    print("=" * 60)
    print("Testing New Customer Record Model")
    print("=" * 60)
    
    # Test data matching the new SQS format
    sample_data = {
        "status": "active",
        "id": "296807a2-c7ea-424c-9f91-24389a10fbd9",
        "organization_id": "296807a2-c7ea-424c-9f91-24389a10fbb0",
        "email": "eric@gmail.com",
        "firstname": "Eric",
        "lastname": "Wong",
        "age": 28,
        "gender": "Male",
        "phone": "+659900990",
        "country": "Malaysia",
        "address": "100 Pasir Ris Grove, #10-10, 440101 Singapore",
        "policy_id": "38ea186d-a3b3-4ecf-b1b0-ba0ae31ae861",
        "uploaded_by": "system",
        "uploaded_date": datetime.now().isoformat(),
        "domain_name": "customer",
        "file_id": "78fcf714-444f-4768-bdbd-61edfc6994a8"
    }
    
    try:
        # Create CustomerRecord instance
        record = CustomerRecord(**sample_data)
        print(f"✓ CustomerRecord created successfully:")
        print(f"  Name: {record.firstname} {record.lastname}")
        print(f"  Email: {record.email}")
        print(f"  Phone: {record.phone}")
        print(f"  Country: {record.country}")
        print(f"  Address: {record.address}")
        print(f"  Gender: {record.gender}")
        print(f"  Age: {record.age}")
        print(f"  Organization ID: {record.organization_id}")
        
        # Test hash functions
        print(f"\n✓ Testing hash functions:")
        full_hash = compute_full_hash(record)
        block_key = compute_block_key(record)
        print(f"  Full hash: {full_hash[:16]}...")
        print(f"  Block key: {block_key}")
        
        # Test GPT formatting
        print(f"\n✓ Testing GPT formatting:")
        gpt_format = format_record_for_gpt(record)
        print(f"  GPT format: {gpt_format}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error creating CustomerRecord: {e}")
        return False

def test_weighted_similarity_weights():
    """Test that our weighted similarity weights add up to 1.0."""
    print("\n" + "=" * 60)
    print("Testing Weighted Similarity Configuration")
    print("=" * 60)
    
    weights = {
        "firstname": 0.20,
        "lastname": 0.20,
        "email": 0.20,
        "phone": 0.15,
        "address": 0.10,
        "organization_id": 0.10,
        "country": 0.03,
        "gender": 0.02
    }
    
    total_weight = sum(weights.values())
    print(f"Individual weights:")
    for field, weight in weights.items():
        print(f"  {field}: {weight}")
    
    print(f"\nTotal weight: {total_weight}")
    
    if abs(total_weight - 1.0) < 0.001:
        print("✓ Weights sum to 1.0 - configuration is valid!")
        return True
    else:
        print(f"✗ Weights sum to {total_weight}, not 1.0!")
        return False

def test_sample_sqs_message():
    """Test processing the sample SQS message format."""
    print("\n" + "=" * 60)
    print("Testing Sample SQS Message Processing")
    print("=" * 60)
    
    # Sample SQS message matching the user's specification
    sample_sqs = {
        "data_entry": {
            "data_type": "tabular",
            "domain_name": "customer",
            "file_id": "78fcf714-444f-4768-bdbd-61edfc6994a8",
            "policy_id": "38ea186d-a3b3-4ecf-b1b0-ba0ae31ae861",
            "data": {
                "status": "active",
                "id": "296807a2-c7ea-424c-9f91-24389a10fbd9",
                "organization_id": "296807a2-c7ea-424c-9f91-24389a10fbb0",
                "email": "eric@gmail.com",
                "firstname": "Eric",
                "lastname": "Wong",
                "age": 28,
                "gender": "Male",
                "phone": "+659900990",
                "country": "Malaysia",
                "address": "100 Pasir Ris Grove, #10-10, 440101 Singapore"
            }
        }
    }
    
    print("SAMPLE SQS MESSAGE:")
    print(json.dumps(sample_sqs, indent=2))
    
    try:
        # Extract data like main.py would do
        data_entry = sample_sqs['data_entry']
        file_id = data_entry.get('file_id')
        policy_id = data_entry.get('policy_id')
        domain_name = data_entry.get('domain_name')
        customer_data = data_entry.get('data', {})
        
        # Create flattened record
        flattened_data = {
            'file_id': file_id,
            'policy_id': policy_id,
            'domain_name': domain_name,
            'uploaded_by': 'system',
            'uploaded_date': datetime.now().isoformat(),
            **customer_data
        }
        
        # Create CustomerRecord
        record = CustomerRecord(**flattened_data)
        print(f"\n✓ Successfully parsed SQS message into CustomerRecord:")
        print(f"  Customer: {record.firstname} {record.lastname}")
        print(f"  Email: {record.email}")
        print(f"  Phone: {record.phone}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error processing SQS message: {e}")
        return False

def main():
    """Run all tests."""
    print("Customer Record Deduplication AI Agent - New Fields Test")
    
    tests = [
        test_new_customer_model,
        test_weighted_similarity_weights,
        test_sample_sqs_message
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All tests passed! The new field structure is working correctly.")
        print("\nNext steps:")
        print("1. Make sure your SQS messages use the new field structure")
        print("2. Update any existing data to use firstname/lastname instead of name")
        print("3. Test the complete deduplication pipeline")
    else:
        print("✗ Some tests failed. Please check the errors above.")

if __name__ == "__main__":
    main()
