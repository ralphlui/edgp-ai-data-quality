"""
Data models for the Customer Record Deduplication AI Agent.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


class CustomerRecord(BaseModel):
    """
    Customer record data model.
    """
    firstname: str = Field(..., description="Customer first name")
    lastname: str = Field(..., description="Customer last name")
    age: int = Field(..., description="Customer age")
    email: str = Field(..., description="Customer email address")
    phone: str = Field(..., description="Customer phone number")
    country: str = Field(..., description="Customer country")
    address: str = Field(..., description="Customer address")
    gender: str = Field(..., description="Customer gender")
    status: str = Field(..., description="Customer status")
    id: UUID = Field(..., description="Customer unique identifier (UUID)")
    organization_id: UUID = Field(..., description="Organization unique identifier (UUID)")


class ProcessedRecord(BaseModel):
    """
    Processed customer record with deduplication results in required format.
    """
    file_id: str
    policy_id: str
    data_type: str = "tabular"
    status: str  # "success" or "fail"
    domain_name: str
    data: dict
    failed_validations: List[dict]


class DuplicationResult(BaseModel):
    """
    Result of the deduplication process.
    """
    is_duplicate: bool
    reason: str
    confidence_score: Optional[float] = None
    matched_record_id: Optional[str] = None


class CandidateMatch(BaseModel):
    """
    A candidate match from the fuzzy matching process.
    """
    record_id: str
    record: CustomerRecord
    similarity_score: float
