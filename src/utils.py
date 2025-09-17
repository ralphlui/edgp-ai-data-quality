"""
Utility functions for the Customer Record Deduplication AI Agent.
"""

import hashlib
import logging
from typing import List, Dict
from models import CustomerRecord


def setup_logging(log_level: str = 'INFO') -> logging.Logger:
    """
    Set up logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    
    Returns:
        Logger instance
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    logger.debug(f"🎯 ACT: Logging system initialized at {log_level.upper()} level")
    return logger


def compute_full_hash(record: CustomerRecord) -> str:
    """
    Compute full hash for exact matching.
    Uses all customer fields for comprehensive matching.
    
    Args:
        record: Customer record
    
    Returns:
        SHA256 hash string
    """
    # Normalize data for consistent hashing
    firstname_normalized = record.firstname.strip().lower()
    lastname_normalized = record.lastname.strip().lower()
    email_normalized = record.email.strip().lower()
    phone_normalized = record.phone.strip().lower()
    country_normalized = record.country.strip().lower()
    address_normalized = record.address.strip().lower()
    gender_normalized = record.gender.strip().lower()
    age_str = str(record.age)
    organization_id_str = str(record.organization_id)
    
    # Create hash input with all fields
    hash_input = (f"{firstname_normalized}|{lastname_normalized}|{email_normalized}|"
                 f"{phone_normalized}|{country_normalized}|{address_normalized}|"
                 f"{gender_normalized}|{age_str}|{organization_id_str}")
    
    # Generate SHA256 hash
    return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()


def compute_block_key(record: CustomerRecord) -> str:
    """
    Compute block key for candidate retrieval.
    Uses first character of normalized firstname, lastname, and email separated by pipes.
    
    Args:
        record: Customer record
    
    Returns:
        Block key string in format: firstname_char|lastname_char|email_char
    """
    # Extract first character of firstname, lastname, and email
    firstname_char = record.firstname.strip().lower()[:1] if record.firstname.strip() else 'x'
    lastname_char = record.lastname.strip().lower()[:1] if record.lastname.strip() else 'x'
    email_char = record.email.strip().lower()[:1] if record.email.strip() else 'x'
    
    return f"{firstname_char}|{lastname_char}|{email_char}"


def normalize_text_for_comparison(text: str) -> str:
    """
    Normalize text for fuzzy matching comparison.
    
    Args:
        text: Input text
    
    Returns:
        Normalized text
    """
    return text.strip().lower()


def format_record_for_gpt(record: CustomerRecord) -> str:
    """
    Format a customer record for GPT analysis.

    Args:
        record: Customer record

    Returns:
        Formatted string representation
    """
    return (f"FirstName: {record.firstname}, "
            f"LastName: {record.lastname}, "
            f"Age: {record.age}, "
            f"Email: {record.email}, "
            f"Phone: {record.phone}, "
            f"Country: {record.country}, "
            f"Address: {record.address}, "
            f"Gender: {record.gender}, "
            f"Status: {record.status}, "
            f"Organization ID: {record.organization_id}")
def create_gpt_prompt(new_record: CustomerRecord, candidates: List[CustomerRecord]) -> str:
    """
    Create a prompt for GPT to analyze potential duplicates.
    
    Args:
        new_record: The new customer record to check
        candidates: List of candidate records for comparison
    
    Returns:
        Formatted prompt string
    """
    prompt = f"""You are an AI expert specializing in customer record deduplication and data matching. Your role is to identify potential duplicate customer records by analyzing all available customer information including personal details, contact information, and organizational data.

NEW CUSTOMER RECORD to analyze:
{format_record_for_gpt(new_record)}

CANDIDATE RECORDS to compare against:
"""
    
    for i, candidate in enumerate(candidates):
        prompt += f"{i}: {format_record_for_gpt(candidate)}\n"
    
    prompt += """
INSTRUCTIONS:
Perform a comprehensive semantic analysis to determine if the new customer record matches any of the candidate records. Consider all fields when making your determination:

- Personal Identity: FirstName, LastName, Age, Gender
- Contact Information: Email, Phone, Address, Country
- Organizational Data: Organization ID, Status
- Unique Identifiers: ID

Look for:
1. Exact matches across multiple fields
2. Similar names with same contact details
3. Same person with slight variations in spelling or formatting
4. Different representations of the same individual

Return your response in JSON format only:
{
  "matches": {
    "0": {"duplicate": false, "score": 0.2},
    "1": {"duplicate": true, "score": 0.9},
    "2": {"duplicate": false, "score": 0.1}
  }
}

Where each candidate index maps to:
- "duplicate": true if it's a duplicate of the new record, false otherwise
- "score": confidence score between 0.0 (definitely not a match) and 1.0 (definitely a match)
"""
    
    return prompt


def create_gpt_prompt_best_match_with_score(new_record: CustomerRecord, candidates: List[CustomerRecord]) -> str:
    """
    Enhanced prompt for GPT to return the single best duplicate match with confidence score and reasoning.

    Args:
        new_record: The new customer record to check
        candidates: List of candidate records for comparison

    Returns:
        Formatted prompt string
    """
    prompt = f"""You are an AI expert specializing in customer record deduplication. 
Your role is to identify the single best duplicate match from a set of candidate records 
by analyzing all available customer data.

NEW CUSTOMER RECORD to analyze:
{format_record_for_gpt(new_record)}

CANDIDATE RECORDS:
"""
    
    for i, candidate in enumerate(candidates):
        prompt += f"{i}: {format_record_for_gpt(candidate)}\n"
    
    prompt += """
INSTRUCTIONS:
Analyze all fields comprehensively:
- Personal Identity: FirstName, LastName, Age, Gender
- Contact Information: Email, Phone, Address, Country  
- Organizational Data: Organization ID, Status

Find the ONE candidate that is most likely to be the same person as the new record. Consider:
1. Multiple field matches indicating same identity
2. Similar names with matching contact details
3. Same organizational context
4. Accounting for data entry variations and typos

Return JSON only:
{
  "best_match_index": 0,   // index of the candidate that is the best duplicate, or null if no good match
  "score": 0.85,           // confidence as a float between 0.0 (no match) and 1.0 (definitely same person)
  "reason": "Exact email and phone match with similar name spelling" // short explanation of why
}
"""
    return prompt


def compute_weighted_similarity(record1: CustomerRecord, record2: CustomerRecord, weights: Dict[str, float] = None) -> float:
    """
    Compute weighted similarity between two customer records.
    
    Args:
        record1: First customer record
        record2: Second customer record
        weights: Field weights for similarity calculation
    
    Returns:
        Similarity score between 0.0 and 1.0
    """
    from rapidfuzz import fuzz
    
    if weights is None:
        weights = {
            'firstname': 0.15,
            'lastname': 0.15,
            'email': 0.25,
            'phone': 0.20,
            'address': 0.15,
            'age': 0.05,
            'gender': 0.03,
            'country': 0.02
        }
    
    total_score = 0.0
    total_weight = 0.0
    
    # Compare text fields using fuzzy matching
    text_fields = ['firstname', 'lastname', 'email', 'phone', 'address', 'gender', 'country']
    for field in text_fields:
        if field in weights:
            val1 = str(getattr(record1, field, '')).lower().strip()
            val2 = str(getattr(record2, field, '')).lower().strip()
            
            if val1 and val2:
                similarity = fuzz.ratio(val1, val2) / 100.0
                total_score += similarity * weights[field]
                total_weight += weights[field]
    
    # Compare age with special handling
    if 'age' in weights and hasattr(record1, 'age') and hasattr(record2, 'age'):
        age_diff = abs(record1.age - record2.age)
        if age_diff == 0:
            age_similarity = 1.0
        elif age_diff <= 2:
            age_similarity = 0.8
        elif age_diff <= 5:
            age_similarity = 0.5
        else:
            age_similarity = 0.0
        
        total_score += age_similarity * weights['age']
        total_weight += weights['age']
    
    return total_score / total_weight if total_weight > 0 else 0.0
