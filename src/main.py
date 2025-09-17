#!/usr/bin/env python3
"""
Main entry point for the Customer Record Deduplication AI Agent.
"""

import json
import time
import logging
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError

from models import CustomerRecord, ProcessedRecord
from deduplication_engine import DeduplicationEngine
from aws_services import SQSService, DynamoDBService
import config
from utils import setup_logging


def process_sqs_message(message_body: str, dedup_engine: DeduplicationEngine) -> ProcessedRecord:
    """
    Process a single SQS message.
    
    Args:
        message_body: JSON string from SQS message
        dedup_engine: Deduplication engine instance
    
    Returns:
        ProcessedRecord with results
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.debug("🧠 THINK: Parsing incoming customer record data...")
        # Parse the SQS message
        data = json.loads(message_body)
        data_entry = data.get('data_entry', {})
        
        # Extract metadata fields for response
        file_id = data_entry.get('file_id', 'unknown')
        policy_id = data_entry.get('policy_id', 'unknown')
        domain_name = data_entry.get('domain_name', 'customer')
        data_type = data_entry.get('data_type', 'tabular')
        
        # Extract customer data
        customer_data = data_entry.get('data', {})
        
        logger.debug("🎯 ACT: Creating customer record model...")
        # Create CustomerRecord directly from customer data
        customer_record = CustomerRecord(**customer_data)
        logger.debug(f"👁️ OBSERVE: Customer record created for {customer_record.firstname} {customer_record.lastname}")
        
        logger.info("🧠 THINK: Executing 3-stage deduplication analysis (exact, fuzzy, AI semantic)...")
        # Process through deduplication engine
        response = dedup_engine.process_record(customer_record)
        
        logger.debug("🎯 ACT: Deduplication analysis completed successfully")
        
        # Update response with metadata from original message
        response.file_id = file_id
        response.policy_id = policy_id
        response.domain_name = domain_name
        response.data_type = data_type
        
        # Log results
        if response.status == "fail":
            if response.failed_validations:
                error_msg = response.failed_validations[0].get("error_message", "Duplicate detected")
                logger.info(f"👁️ OBSERVE: Duplicate detected! Reason: {error_msg}")
        else:
            logger.info("👁️ OBSERVE: No duplicates found - customer record is unique!")
        
        return response
        
    except Exception as e:
        logger.error(f"❌ OBSERVE: Error processing customer record: {str(e)}")
        # Return error response with metadata if available
        try:
            data = json.loads(message_body)
            data_entry = data.get('data_entry', {})
            file_id = data_entry.get('file_id', 'unknown')
            policy_id = data_entry.get('policy_id', 'unknown')
            domain_name = data_entry.get('domain_name', 'unknown')
            data_type = data_entry.get('data_type', 'tabular')
        except:
            file_id = "unknown"
            policy_id = "unknown"
            domain_name = "unknown"
            data_type = "tabular"
            
        return ProcessedRecord(
            file_id=file_id,
            policy_id=policy_id,
            data_type=data_type,
            status="fail",
            domain_name=domain_name,
            data={},
            failed_validations=[
                {
                    "rule_name": "ProcessingError",
                    "column_name": None,
                    "error_message": f"Processing error: {str(e)}",
                    "status": "fail"
                }
            ]
        )


def main():
    """Main application loop."""
    # Setup logging
    logger = setup_logging(config.LOG_LEVEL)
    logger.info("🤖 AGENT STARTUP: Initializing Customer Record Deduplication AI Agent")
    
    # Validate configuration
    logger.info("🧠 THINK: Need to validate configuration and environment variables...")
    try:
        config.validate_config()
        logger.info("🎯 ACT: Configuration validation completed successfully")
        logger.info("👁️ OBSERVE: All required environment variables are present")
    except ValueError as e:
        logger.error(f"❌ OBSERVE: Configuration error: {e}")
        return
    
    # Initialize services
    logger.info("🧠 THINK: Need to establish connections to AWS SQS, DynamoDB, and OpenAI services")
    try:
        sqs_service = SQSService()
        dynamodb_service = DynamoDBService()
        dedup_engine = DeduplicationEngine()
        
        logger.info("🎯 ACT: Successfully initialized all services")
        logger.info("👁️ OBSERVE: Ready to process customer deduplication requests")
        
    except Exception as e:
        logger.error(f"❌ OBSERVE: Failed to initialize services: {e}")
        return
    
    # Main processing loop
    logger.info("🚀 AGENT READY: Starting message processing loop...")
    
    while True:
        try:
            # Receive messages from input queue
            logger.debug("🧠 THINK: Checking for new customer records to deduplicate...")
            messages = sqs_service.receive_messages(config.WORKFLOW_DEDUPLICATION_REQUEST_SQS_URL, max_messages=10)
            
            if not messages:
                logger.debug("👁️ OBSERVE: No messages in queue, waiting for new records...")
                time.sleep(5)
                continue
            
            logger.info(f"🎯 ACT: Found {len(messages)} customer records to process")
            
            for message in messages:
                try:
                    logger.info("🧠 THINK: Analyzing customer record for potential duplicates...")
                    # Process the message
                    result = process_sqs_message(message['Body'], dedup_engine)
                    
                    logger.info("🎯 ACT: Sending deduplication results to output queue...")
                    # Send result to output queue
                    sqs_service.send_result(result.dict())
                    
                    logger.info("🎯 ACT: Cleaning up processed message from input queue...")
                    # Delete the processed message
                    sqs_service.delete_message(message['ReceiptHandle'])
                    
                    logger.info(f"👁️ OBSERVE: Message processed successfully with status: {result.status}")
                    
                except Exception as e:
                    logger.error(f"❌ OBSERVE: Error processing message: {e}")
                    # Optionally send to dead letter queue or handle error
                    
        except KeyboardInterrupt:
            logger.info("🛑 OBSERVE: Received shutdown signal, gracefully stopping agent...")
            break
            
        except Exception as e:
            logger.error(f"❌ OBSERVE: Unexpected error in main loop: {e}")
            logger.info("🧠 THINK: Error occurred, waiting before retrying...")
            time.sleep(10)  # Wait before retrying
    
    logger.info("🤖 AGENT SHUTDOWN: Customer Record Deduplication AI Agent stopped gracefully")


if __name__ == "__main__":
    main()
