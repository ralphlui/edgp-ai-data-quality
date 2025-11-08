"""
Deduplication engine for the Customer Record Deduplication AI Agent.
"""

import json
import logging
from typing import List, Optional, Dict, Any
from rapidfuzz import fuzz
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage
from models import CustomerRecord, DuplicationResult, CandidateMatch, ProcessedRecord
from aws_services import DynamoDBService
from utils import normalize_text_for_comparison, create_gpt_prompt_best_match_with_score, compute_weighted_similarity
import config


logger = logging.getLogger(__name__)


class DeduplicationEngine:
    """
    Main deduplication engine that orchestrates all matching steps.
    """
    
    def __init__(self, dynamodb_service=None):
        """Initialize the deduplication engine."""
        self.dynamodb_service = dynamodb_service or DynamoDBService()
        
        # Ensure OpenAI configuration is initialized
        config.initialize_openai_config()
        
        self.llm = ChatOpenAI(
            model=config.OPENAI_MODEL,
            temperature=0,
            openai_api_key=config.OPENAI_API_KEY
        )
        
        # Ensure DynamoDB table exists
        self.dynamodb_service.create_table_if_not_exists()
    
    def exact_match(self, record: CustomerRecord) -> Optional[Dict[str, Any]]:
        """
        Step 1: Check for exact match using full hash.
        
        Args:
            record: Customer record to check
        
        Returns:
            Matching record if found, None otherwise
        """
        logger.info("🧠 THINK: Need to check if this exact customer record already exists in our database...")
        logger.debug(f"🎯 ACT: Computing full hash for {record.firstname} {record.lastname} to detect exact duplicates")
        
        exact_match_result = self.dynamodb_service.exact_match(record)
        
        if exact_match_result:
            logger.info("👁️ OBSERVE: Found exact match! This customer record is identical to an existing entry")
        else:
            logger.info("👁️ OBSERVE: No exact match found - proceeding to fuzzy similarity analysis")
            
        return exact_match_result
    
    def fetch_candidates(self, record: CustomerRecord) -> List[CustomerRecord]:
        """
        Step 2a: Fetch candidate records using block key.
        
        Args:
            record: Customer record to find candidates for
        
        Returns:
            List of candidate CustomerRecord objects
        """
        logger.info("🧠 THINK: Need to find similar customer records using intelligent block key matching...")
        logger.debug(f"🎯 ACT: Generating block key for {record.firstname} {record.lastname} to identify potential matches")
        
        candidate_items = self.dynamodb_service.fetch_candidates(record)
        
        logger.info(f"👁️ OBSERVE: Found {len(candidate_items)} potential candidate records from database")
        
        candidates = []
        for i, item in enumerate(candidate_items):
            try:
                candidate = CustomerRecord(
                    firstname=item['firstname'],
                    lastname=item['lastname'],
                    age=int(item['age']),
                    email=item['email'],
                    phone=item['phone'],
                    country=item['country'],
                    address=item['address'],
                    gender=item['gender'],
                    id=item['id'],
                    organization_id=item['organization_id']
                )
                candidates.append(candidate)
                logger.debug(f"🎯 ACT: Successfully loaded candidate #{i+1}: {candidate.firstname} {candidate.lastname}")
            except (KeyError, ValueError) as e:
                logger.warning(f"⚠️ WARNING: Skipping invalid candidate record #{i+1}: {e}")
                continue
        
        logger.info(f"👁️ OBSERVE: Successfully loaded {len(candidates)} valid candidate records for similarity analysis")
        return candidates
    
    def fuzzy_match_top_k(self, new_record: CustomerRecord, candidates: List[CustomerRecord]) -> List[CandidateMatch]:
        """
        Step 2b: Perform fuzzy matching and return top-k candidates.
        
        Args:
            new_record: New customer record
            candidates: List of candidate records
        
        Returns:
            List of top-k candidate matches sorted by similarity score
        """
        logger.info(f"🧠 THINK: Analyzing {len(candidates)} candidates using comprehensive fuzzy matching across 9 key fields...")
        
        if not candidates:
            logger.info("👁️ OBSERVE: No candidates available for fuzzy matching analysis")
            return []
        
        candidate_matches = []
        
        for i, candidate in enumerate(candidates):
            logger.debug(f"🎯 ACT: Evaluating candidate #{i+1} - {candidate.firstname} {candidate.lastname}")
            
            # Calculate individual field similarities
            similarities = {}
            
            # Firstname similarity (20% weight)
            similarities['firstname'] = fuzz.ratio(
                normalize_text_for_comparison(new_record.firstname),
                normalize_text_for_comparison(candidate.firstname)
            )
            
            # Lastname similarity (20% weight)
            similarities['lastname'] = fuzz.ratio(
                normalize_text_for_comparison(new_record.lastname),
                normalize_text_for_comparison(candidate.lastname)
            )
            
            # Email similarity (20% weight)
            similarities['email'] = fuzz.ratio(
                normalize_text_for_comparison(new_record.email),
                normalize_text_for_comparison(candidate.email)
            )
            
            # Phone similarity (15% weight)
            similarities['phone'] = fuzz.ratio(
                normalize_text_for_comparison(new_record.phone),
                normalize_text_for_comparison(candidate.phone)
            )
            
            # Address similarity (10% weight)
            similarities['address'] = fuzz.ratio(
                normalize_text_for_comparison(new_record.address),
                normalize_text_for_comparison(candidate.address)
            )
            
            # Organization ID similarity (10% weight)
            similarities['organization_id'] = 100.0 if str(new_record.organization_id) == str(candidate.organization_id) else 0.0
            
            # Country similarity (3% weight)
            similarities['country'] = fuzz.ratio(
                normalize_text_for_comparison(new_record.country),
                normalize_text_for_comparison(candidate.country)
            )
            
            # Gender similarity (2% weight)
            similarities['gender'] = 100.0 if new_record.gender.lower() == candidate.gender.lower() else 0.0
            
            # Age exact match bonus (included in overall calculation)
            age_bonus = 100.0 if new_record.age == candidate.age else max(0, 100 - abs(new_record.age - candidate.age) * 5)
            
            # Calculate weighted similarity score using config weights
            overall_similarity = 0.0
            field_details = []
            
            for field, weight in config.FIELD_WEIGHTS.items():
                if field in similarities:
                    score = similarities[field]
                    weighted_score = score * weight
                    overall_similarity += weighted_score
                    field_details.append(f"{field}={score:.1f}%")
            
            # Add age bonus as a separate component (not in config weights)
            age_weight = 0.02  # 2% for age
            overall_similarity += age_bonus * age_weight
            field_details.append(f"age={age_bonus:.1f}%")
            
            candidate_match = CandidateMatch(
                record_id=str(candidate.id),
                record=candidate,
                similarity_score=overall_similarity
            )
            candidate_matches.append(candidate_match)
            
            logger.debug(f"👁️ OBSERVE: Candidate #{i+1} overall similarity: {overall_similarity:.2f}% [{', '.join(field_details)}]")
        
        # Sort by similarity score (descending) and take top-3
        candidate_matches.sort(key=lambda x: x.similarity_score, reverse=True)
        top_k_matches = candidate_matches[:3]
        
        if top_k_matches:
            logger.info(f"🎯 ACT: Selected top-3 candidates for detailed analysis:")
            for i, match in enumerate(top_k_matches):
                logger.info(f"   #{i+1}: {match.record.firstname} {match.record.lastname} (similarity: {match.similarity_score:.2f}%)")
        else:
            logger.info("👁️ OBSERVE: No suitable candidates found during fuzzy matching")
        
        return top_k_matches
    
    def gpt_semantic_check_top_k(self, new_record: CustomerRecord, candidates: List[CandidateMatch]) -> Dict[str, Dict[str, float]]:
        """
        Step 3: Use GPT to perform semantic check on ambiguous candidates.
        
        Args:
            new_record: New customer record
            candidates: List of candidate matches to analyze
        
        Returns:
            Dictionary mapping candidate record_id to {duplicate: bool, confidence: float}
        """
        logger.info(f"� THINK: Fuzzy matching results are ambiguous - need AI semantic analysis for final decision...")
        logger.info(f"🎯 ACT: Performing advanced semantic analysis on {len(candidates)} candidate records for similarity assessment")
        
        if not candidates:
            logger.info("👁️ OBSERVE: No candidates provided for GPT analysis")
            return {}
        
        # Extract just the records for GPT analysis
        candidate_records = [match.record for match in candidates]
        
        logger.debug("🧠 THINK: Constructing detailed prompt for GPT semantic analysis...")
        # Create prompt for GPT
        prompt = create_gpt_prompt_best_match_with_score(new_record, candidate_records)
        
        try:
            logger.debug("🎯 ACT: Sending request for advanced semantic reasoning and duplicate detection...")
            # Call language model using the new invoke method (replaces deprecated __call__)
            message = HumanMessage(content=prompt)
            response = self.llm.invoke([message])
            
            # Parse JSON response
            response_text = response.content.strip()
            logger.debug(f"👁️ OBSERVE: Received GPT response: {response_text[:200]}..." if len(response_text) > 200 else f"👁️ OBSERVE: Received GPT response: {response_text}")
            logger.debug(f"👁️  OBSERVE: Received GPT response: {response_text}")
            
            # Extract JSON from response
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            elif "{" in response_text and "}" in response_text:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                json_text = response_text[json_start:json_end]
            else:
                logger.error("❌ ERROR: Could not extract JSON from GPT response")
                return {}
            
            parsed_response = json.loads(json_text)
            
            # Extract GPT response components (correct format: best_match_index and score)
            best_match_index = parsed_response.get('best_match_index')
            gpt_score = float(parsed_response.get('score', 0.0))
            gpt_reason = parsed_response.get('reason', '')
            
            # Convert GPT response to our expected format
            result = {}
            for i, candidate in enumerate(candidates):
                # Check if this candidate is the best match according to GPT
                if best_match_index is not None and i == best_match_index:
                    # This is the candidate GPT analyzed
                    if gpt_score >= config.GPT_CONFIDENCE_THRESHOLD:
                        # GPT found a duplicate match (score > threshold)
                        duplicate_flag = True
                        confidence_score = gpt_score
                        logger.debug(f"👁️ OBSERVE: Candidate {candidate.record_id}: duplicate={duplicate_flag}, GPT confidence={confidence_score:.2%}")
                    else:
                        # GPT analyzed but determined not a duplicate (score <= threshold)
                        duplicate_flag = False
                        confidence_score = gpt_score
                        logger.debug(f"👁️ OBSERVE: Candidate {candidate.record_id}: duplicate={duplicate_flag}")
                else:
                    # This candidate was not the best match selected by GPT
                    duplicate_flag = False
                    confidence_score = 0.0
                    logger.debug(f"👁️ OBSERVE: Candidate {candidate.record_id}: duplicate={duplicate_flag}")
                
                result[candidate.record_id] = {
                    "duplicate": duplicate_flag,
                    "confidence": confidence_score
                }
            
            duplicates_found = len([r for r in result.values() if r['duplicate']])
            logger.info(f"👁️ OBSERVE: GPT semantic analysis completed: {duplicates_found} duplicates detected")
            return result
            
        except Exception as e:
            logger.error(f"❌ ERROR: Failed in GPT semantic analysis: {e}")
            # Return conservative result (no duplicates) on error
            return {candidate.record_id: {"duplicate": False, "confidence": 0.0} for candidate in candidates}
    
    def is_duplicate(self, record: CustomerRecord) -> DuplicationResult:
        """
        Main function to determine if a record is a duplicate.
        Orchestrates all deduplication steps.
        
        Args:
            record: Customer record to check
        
        Returns:
            DuplicationResult with decision and reasoning
        """
        logger.info("🚀 AGENT MISSION: Initiating comprehensive 3-stage deduplication analysis...")
        logger.info(f"🧠 THINK: Target customer: {record.firstname} {record.lastname} ({record.email})")
        
        # Step 1: Exact Match
        logger.info("📋 STAGE 1: Exact Match Detection")
        exact_match_result = self.exact_match(record)
        if exact_match_result:
            logger.info("✅ MISSION COMPLETE: Duplicate confirmed via exact match - 100% confidence")
            # Handle case where exact_match_result might be a mock or actual data
            if isinstance(exact_match_result, dict) and 'full_hash' in exact_match_result:
                matched_id = exact_match_result['full_hash']
            else:
                # Fallback to record id if full_hash not available
                matched_id = str(record.id)
            
            return DuplicationResult(
                is_duplicate=True,
                reason="Exact Match",
                confidence_score=1.0,
                matched_record_id=matched_id
            )
        
        # Step 2: Candidate Retrieval + Fuzzy Match
        logger.info("📋 STAGE 2: Intelligent Fuzzy Similarity Analysis")
        candidates = self.fetch_candidates(record)
        if not candidates:
            # High confidence when no candidates are found using block key matching
            logger.info("✅ MISSION COMPLETE: No similar records found via block key matching - customer is unique (95% confidence)")
            return DuplicationResult(
                is_duplicate=False,
                reason="No Match",
                confidence_score=0.95  # High confidence but not 100% as block key might miss some edge cases
            )
        
        top_k_matches = self.fuzzy_match_top_k(record, candidates)
        
        # Check for high-confidence fuzzy matches
        logger.info(f"🧠 THINK: Evaluating fuzzy match results against high confidence threshold ({config.FUZZY_SIMILARITY_THRESHOLD_HIGH}%)...")
        high_confidence_matches = [
            match for match in top_k_matches 
            if match.similarity_score > config.FUZZY_SIMILARITY_THRESHOLD_HIGH
        ]
        
        if high_confidence_matches:
            best_match = high_confidence_matches[0]
            logger.info(f"✅ MISSION COMPLETE: Duplicate confirmed via fuzzy match (similarity: {best_match.similarity_score:.2f}%)")
            return DuplicationResult(
                is_duplicate=True,
                reason="Fuzzy Match",
                confidence_score=best_match.similarity_score / 100.0,
                matched_record_id=best_match.record_id
            )
        
        # Step 3: Semantic Check for ambiguous cases
        logger.info("📋 STAGE 3: AI Semantic Analysis for Ambiguous Cases")
        logger.info(f"🧠 THINK: Checking for ambiguous matches between {config.FUZZY_SIMILARITY_THRESHOLD_LOW}% and {config.FUZZY_SIMILARITY_THRESHOLD_HIGH}%...")
        ambiguous_matches = [
            match for match in top_k_matches 
            if config.FUZZY_SIMILARITY_THRESHOLD_LOW <= match.similarity_score <= config.FUZZY_SIMILARITY_THRESHOLD_HIGH
        ]
        
        if ambiguous_matches:
            logger.info(f"👁️ OBSERVE: Found {len(ambiguous_matches)} ambiguous matches requiring AI semantic analysis")
            gpt_results = self.gpt_semantic_check_top_k(record, ambiguous_matches)
            
            # Check if any candidate was marked as duplicate by GPT
            for candidate_id, gpt_result in gpt_results.items():
                if gpt_result["duplicate"]:
                    logger.info(f"✅ MISSION COMPLETE: Duplicate confirmed via AI semantic analysis (candidate: {candidate_id})")
                    # Find the matching candidate
                    matched_candidate = next(
                        (match for match in ambiguous_matches if match.record_id == candidate_id),
                        None
                    )
                    if matched_candidate:
                        # Use GPT confidence score alone
                        fuzzy_confidence = matched_candidate.similarity_score / 100.0
                        gpt_confidence = gpt_result["confidence"]  # Don't divide by 100 since it's already 0-1
                        # Use GPT confidence alone as requested
                        final_confidence = gpt_confidence
                        
                        logger.info(f"🤖 FINAL VERDICT: AI semantic analysis confirms duplicate")
                        logger.info(f"📊 CONFIDENCE BREAKDOWN: Fuzzy={fuzzy_confidence:.2%}, GPT={gpt_confidence:.2%}, Final={final_confidence:.2%}")
                        
                        return DuplicationResult(
                            is_duplicate=True,
                            reason="Semantic Check",
                            confidence_score=final_confidence,
                            matched_record_id=candidate_id
                        )
            
            logger.info("👁️ OBSERVE: AI semantic analysis confirms no duplicates among ambiguous candidates")
            
            # Calculate confidence based on actual GPT analysis results for no-match cases
            if gpt_results:
                # Use actual GPT confidence scores for no-match decision
                gpt_confidences = [result["confidence"] for result in gpt_results.values()]
                avg_gpt_confidence = sum(gpt_confidences) / len(gpt_confidences) if gpt_confidences else 0
                # Convert to percentage first (since confidence is in 0-1 range)
                avg_gpt_confidence_percent = avg_gpt_confidence * 100
                # For no-match, confidence is inverse of average GPT confidence (higher when GPT is less confident about duplicates)
                gpt_based_confidence = max(0.6, 1.0 - (avg_gpt_confidence_percent / 100.0))
                
                logger.info(f"👁️ OBSERVE: GPT analysis results - Average GPT confidence: {avg_gpt_confidence_percent:.1f}%, No-match confidence: {gpt_based_confidence:.2%}")
                return DuplicationResult(
                    is_duplicate=False,
                    reason="No Match (GPT Verified)",
                    confidence_score=gpt_based_confidence
                )
        else:
            logger.info("👁️ OBSERVE: No ambiguous matches found - skipping AI semantic analysis")
        
        # No duplicates found - use actual confidence based on fuzzy analysis results
        if top_k_matches:
            # Use actual fuzzy similarity scores to determine confidence
            highest_similarity = max([match.similarity_score for match in top_k_matches])
            similarity_scores = [match.similarity_score for match in top_k_matches]
            avg_similarity = sum(similarity_scores) / len(similarity_scores)
            
            # Confidence is higher when similarities are low (less chance of missing a duplicate)
            fuzzy_based_confidence = max(0.7, 1.0 - (avg_similarity / 100.0))
            
            logger.info(f"👁️ OBSERVE: Fuzzy analysis results - Highest: {highest_similarity:.1f}%, Average: {avg_similarity:.1f}%, No-match confidence: {fuzzy_based_confidence:.2%}")
            
            return DuplicationResult(
                is_duplicate=False,
                reason="No Match (Fuzzy Verified)",
                confidence_score=fuzzy_based_confidence
            )
        else:
            # No candidates found at all - high confidence
            logger.info(f"✅ MISSION COMPLETE: No similar candidates found - customer is unique (95% confidence)")
            return DuplicationResult(
                is_duplicate=False,
                reason="No Match (No Candidates)",
                confidence_score=0.95
            )
    
    def check_duplicate(self, record: CustomerRecord) -> DuplicationResult:
        """
        Alias for is_duplicate method for backward compatibility with tests.
        
        Args:
            record: Customer record to check
        
        Returns:
            DuplicationResult with decision and reasoning
        """
        return self.is_duplicate(record)
    
    def process_record(self, record: CustomerRecord) -> ProcessedRecord:
        """
        Process a customer record through the complete deduplication pipeline.
        
        Args:
            record: Customer record to process
        
        Returns:
            ProcessedRecord with deduplication results in required format
        """
        logger.info(f"🚀 PROCESSING PIPELINE: Starting comprehensive analysis for {record.firstname} {record.lastname}")
        logger.info(f"📊 CUSTOMER PROFILE: Email: {record.email}, Age: {record.age}, Country: {record.country}")
        
        # Perform deduplication check
        dup_result = self.is_duplicate(record)
        
        # If not a duplicate, store the record for future comparisons
        if not dup_result.is_duplicate:
            logger.info("🧠 THINK: Customer is unique - need to store in database for future deduplication checks...")
            logger.debug("🎯 ACT: Storing new customer record in DynamoDB database")
            stored = self.dynamodb_service.store_record(record)
            if stored:
                logger.info("👁️ OBSERVE: Successfully stored new customer record in database")
            else:
                logger.warning("⚠️ WARNING: Failed to store new record in DynamoDB - this may affect future deduplication accuracy")
        else:
            logger.info("🧠 THINK: Customer is a duplicate - skipping database storage to prevent redundancy")
        
        # Create human-readable error message with confidence score
        error_message = ""
        if dup_result.is_duplicate:
            confidence_percentage = round(dup_result.confidence_score * 100, 1)  # Use round instead of int to preserve decimals
            if dup_result.reason == "Exact Match":
                error_message = f"Exact match found with 100% confidence - identical record already exists"
                logger.info(f"🎯 FINAL RESULT: DUPLICATE DETECTED via {dup_result.reason} - 100% confidence")
            elif dup_result.reason == "Fuzzy Match":
                error_message = f"Fuzzy match found with {confidence_percentage}% confidence - similar record detected"
                logger.info(f"🎯 FINAL RESULT: DUPLICATE DETECTED via {dup_result.reason} - {confidence_percentage}% confidence")
            elif dup_result.reason == "Semantic Check":
                error_message = f"Semantic match found with {confidence_percentage}% confidence - AI detected duplicate meaning"
                logger.info(f"🎯 FINAL RESULT: DUPLICATE DETECTED via {dup_result.reason} - {confidence_percentage}% confidence")
            else:
                error_message = f"{dup_result.reason} with {confidence_percentage}% confidence"
                logger.info(f"🎯 FINAL RESULT: DUPLICATE DETECTED via {dup_result.reason} - {confidence_percentage}% confidence")
        else:
            logger.info("🎯 FINAL RESULT: UNIQUE CUSTOMER CONFIRMED - No duplicates found across all detection methods")
        
        # Create processed record in required format
        processed_record = ProcessedRecord(
            file_id="unknown",
            policy_id="unknown",
            data_type="tabular",
            status="fail" if dup_result.is_duplicate else "success",
            domain_name="customer",
            data={"id": str(record.id)},
            failed_validations=[
                {
                    "rule_name": "NoRecordDuplication",
                    "column_name": None,
                    "error_message": error_message,
                    "status": "fail"
                }
            ] if dup_result.is_duplicate else []
        )
        
        logger.info(f"📋 PROCESSING COMPLETE: Customer analysis finished with status='{processed_record.status}', reason='{dup_result.reason}'")
        logger.info("🏁 PIPELINE END: Deduplication analysis completed successfully")
        return processed_record
