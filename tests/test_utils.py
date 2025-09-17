"""
Test utilities and sample data for testing.
"""

from uuid import uuid4
from typing import Dict, Any, List


# Sample customer records for testing
SAMPLE_RECORDS = [
    {
        "firstname": "John",
        "lastname": "Smith", 
        "age": 30,
        "email": "john.smith@email.com",
        "phone": "+1-555-0123",
        "country": "USA",
        "address": "123 Main St",
        "gender": "Male",
        "status": "Active",
        "id": str(uuid4()),
        "organization_id": str(uuid4())
    },
    {
        "firstname": "Jane",
        "lastname": "Doe",
        "age": 25, 
        "email": "jane.doe@email.com",
        "phone": "+1-555-0456",
        "country": "USA",
        "address": "456 Oak Ave",
        "gender": "Female",
        "status": "Active",
        "id": str(uuid4()),
        "organization_id": str(uuid4())
    },
    {
        "firstname": "John",
        "lastname": "Smith", 
        "age": 30,
        "email": "john.smith@email.com",
        "phone": "+1-555-0123",
        "country": "USA",
        "address": "123 Main St",
        "gender": "Male",
        "status": "Active",
        "id": str(uuid4()),
        "organization_id": str(uuid4())
    }
]


def validate_customer_record(record_data: Dict[str, Any]) -> bool:
    """Validate a customer record dictionary."""
    required_fields = ["firstname", "lastname", "age", "email"]
    
    for field_name in required_fields:
        if field_name not in record_data or not record_data[field_name]:
            return False
    
    if not isinstance(record_data["age"], int) or record_data["age"] < 0:
        return False
        
    if "@" not in record_data["email"]:
        return False
    
    return True
