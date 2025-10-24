"""
AWS service integrations for the            if response['Table']['TableStatus'] == 'ACTIVE':
                logger.info(f"👁️ OBSERVE: Table {config.DYNAMODB_TABLE_NAME} already exists and is active")
            else:
                logger.info(f"🧠 THINK: Table exists but not active, creating new table...")
                logger.info(f"🎯 ACT: Creating table {config.DYNAMODB_TABLE_NAME}")ustomer Record Deduplication AI Agent.
"""

import json
import logging
from typing import List, Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError
from models import CustomerRecord, CandidateMatch
from utils import compute_full_hash, compute_block_key
import config


logger = logging.getLogger(__name__)


class DynamoDBService:
    """
    Service for DynamoDB operations.
    """
    
    def __init__(self):
        """Initialize DynamoDB service."""
        self.dynamodb = boto3.resource('dynamodb', region_name=config.AWS_REGION)
        self.table = self.dynamodb.Table(config.DYNAMODB_TABLE_NAME)
    
    def create_table_if_not_exists(self):
        """
        Create DynamoDB table if it doesn't exist.
        """
        try:
            # Check if table exists
            self.table.load()
            logger.info(f"Table {config.DYNAMODB_TABLE_NAME} already exists")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                logger.info(f"Creating table {config.DYNAMODB_TABLE_NAME}")
                
                # Create table
                table = self.dynamodb.create_table(
                    TableName=config.DYNAMODB_TABLE_NAME,
                    KeySchema=[
                        {
                            'AttributeName': 'full_hash',
                            'KeyType': 'HASH'
                        }
                    ],
                    AttributeDefinitions=[
                        {
                            'AttributeName': 'full_hash',
                            'AttributeType': 'S'
                        },
                        {
                            'AttributeName': 'block_key',
                            'AttributeType': 'S'
                        }
                    ],
                    GlobalSecondaryIndexes=[
                        {
                            'IndexName': config.BLOCK_KEY_GSI_NAME,
                            'KeySchema': [
                                {
                                    'AttributeName': 'block_key',
                                    'KeyType': 'HASH'
                                }
                            ],
                            'Projection': {
                                'ProjectionType': 'ALL'
                            }
                        }
                    ],
                    BillingMode='PAY_PER_REQUEST'
                )
                
                # Wait for table to be created
                table.wait_until_exists()
                logger.info(f"Table {config.DYNAMODB_TABLE_NAME} created successfully")
            else:
                raise e
    
    def exact_match(self, record: CustomerRecord) -> Optional[Dict[str, Any]]:
        """
        Check for exact match using full hash.
        
        Args:
            record: Customer record to check
        
        Returns:
            Matching record if found, None otherwise
        """
        full_hash = compute_full_hash(record)
        
        try:
            response = self.table.get_item(
                Key={'full_hash': full_hash}
            )
            
            if 'Item' in response:
                logger.info(f"Exact match found for hash: {full_hash}")
                return response['Item']
            
            return None
            
        except ClientError as e:
            logger.error(f"Error checking exact match: {e}")
            raise e
    
    def fetch_candidates(self, record: CustomerRecord) -> List[Dict[str, Any]]:
        """
        Fetch candidate records using block key.
        
        Args:
            record: Customer record to find candidates for
        
        Returns:
            List of candidate records
        """
        block_key = compute_block_key(record)
        
        try:
            response = self.table.query(
                IndexName=config.BLOCK_KEY_GSI_NAME,
                KeyConditionExpression='block_key = :block_key',
                ExpressionAttributeValues={
                    ':block_key': block_key
                }
            )
            
            candidates = response.get('Items', [])
            logger.info(f"Found {len(candidates)} candidates for block key: {block_key}")
            
            return candidates
            
        except ClientError as e:
            logger.error(f"Error fetching candidates: {e}")
            raise e
    
    def store_record(self, record: CustomerRecord) -> bool:
        """
        Store a new customer record in DynamoDB.
        
        Args:
            record: Customer record to store
        
        Returns:
            True if successful, False otherwise
        """
        full_hash = compute_full_hash(record)
        block_key = compute_block_key(record)
        
        item = {
            'full_hash': full_hash,
            'block_key': block_key,
            'firstname': record.firstname,
            'lastname': record.lastname,
            'phone': record.phone,
            'address': record.address,
            'country': record.country,
            'age': record.age,
            'email': record.email,
        }
        
        # Add additional fields that are available in the CustomerRecord model
        item['id'] = str(record.id)
        item['organization_id'] = str(record.organization_id)
        item['gender'] = record.gender
        
        try:
            self.table.put_item(Item=item)
            logger.info(f"Stored record with hash: {full_hash}")
            return True
            
        except ClientError as e:
            logger.error(f"Error storing record: {e}")
            return False


class SQSService:
    """
    Service for SQS operations.
    """
    
    def __init__(self):
        """Initialize SQS service."""
        self.sqs = boto3.client('sqs', region_name=config.AWS_REGION)
    
    def receive_message(self) -> Optional[Dict[str, Any]]:
        """
        Receive a message from the input queue.
        
        Returns:
            Message dict if available, None otherwise
        """
        try:
            response = self.sqs.receive_message(
                QueueUrl=config.WORKFLOW_DEDUPLICATION_REQUEST_SQS_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20  # Long polling
            )
            
            messages = response.get('Messages', [])
            if messages:
                return messages[0]
            
            return None
            
        except ClientError as e:
            logger.error(f"❌ ERROR: Failed to receive message from SQS: {e}")
            raise e

    def receive_messages(self, queue_url: str, max_messages: int = 10) -> List[Dict[str, Any]]:
        """
        Receive multiple messages from the specified queue.
        
        Args:
            queue_url: SQS queue URL
            max_messages: Maximum number of messages to receive (1-10)
        
        Returns:
            List of message dictionaries
        """
        try:
            response = self.sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=min(max_messages, 10),  # SQS limit is 10
                WaitTimeSeconds=20  # Long polling
            )
            
            messages = response.get('Messages', [])
            logger.debug(f"👁️ OBSERVE: Received {len(messages)} messages from queue")
            return messages
            
        except ClientError as e:
            logger.error(f"❌ ERROR: Failed to receive messages from SQS: {e}")
            return []
    
    def delete_message(self, receipt_handle: str) -> bool:
        """
        Delete a processed message from the input queue.
        
        Args:
            receipt_handle: Message receipt handle
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.sqs.delete_message(
                QueueUrl=config.WORKFLOW_DEDUPLICATION_REQUEST_SQS_URL,
                ReceiptHandle=receipt_handle
            )
            logger.debug(f"🎯 ACT: Successfully deleted message from queue")
            return True
            
        except ClientError as e:
            logger.error(f"❌ ERROR: Failed to delete message from SQS: {e}")
            return False
    
    def send_result(self, result: Dict[str, Any]) -> bool:
        """
        Send processing result to output queue.
        
        Args:
            result: Processing result to send
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.sqs.send_message(
                QueueUrl=config.WORKFLOW_DEDUPLICATION_RESPONSE_SQS_URL,
                MessageBody=json.dumps(result)
            )
            logger.info("🎯 ACT: Result successfully sent to output queue")
            return True
            
        except ClientError as e:
            logger.error(f"❌ ERROR: Failed to send result to SQS: {e}")
            return False
