"""
Extract training data for severity classifier from DynamoDB.

This script scans the nexus-triage DynamoDB table to extract historical
triage records and create a training dataset for the severity classifier.

The training data consists of:
- Log text: Concatenated anomalous log sections from the triage record
- Label: The severity classification (INFO, WARNING, HIGH, CRITICAL)

Severity mapping in triage records:
- is_critical=False, needs_escalation=False → INFO
- is_critical=False, needs_escalation=True → WARNING
- is_critical=True, confidence < 0.8 → HIGH
- is_critical=True, confidence >= 0.8 → CRITICAL

Usage:
    python scripts/extract_training_data.py \
        --output_file ./data/severity_training.json \
        --table_name nexus-triage \
        --min_records 100

AWS Requirements:
    - DynamoDB table with triage records
    - IAM permissions: dynamodb:Scan, dynamodb:GetItem
"""

import json
import logging
import argparse
from typing import List, Tuple, Dict, Optional
from pathlib import Path
import sys

import boto3
from botocore.exceptions import ClientError, BotoCoreError

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TrainingDataExtractor:
    """Extract training data from DynamoDB triage records."""
    
    SEVERITY_LEVELS = ["INFO", "WARNING", "HIGH", "CRITICAL"]
    
    def __init__(
        self,
        table_name: str = "nexus-triage",
        region_name: str = "us-east-1"
    ):
        """
        Initialize extractor.
        
        Args:
            table_name: DynamoDB table name
            region_name: AWS region
        """
        self.table_name = table_name
        self.dynamodb = boto3.resource("dynamodb", region_name=region_name)
        self.table = self.dynamodb.Table(table_name)
    
    def infer_severity(
        self,
        is_critical: bool,
        needs_escalation: bool,
        confidence: Optional[float] = None
    ) -> str:
        """
        Infer severity label from triage attributes.
        
        Args:
            is_critical: Whether classified as critical
            needs_escalation: Whether escalation is needed
            confidence: Confidence score for critical classification
            
        Returns:
            Severity label (INFO, WARNING, HIGH, or CRITICAL)
        """
        if not is_critical and not needs_escalation:
            return "INFO"
        elif not is_critical and needs_escalation:
            return "WARNING"
        elif is_critical and (confidence is None or confidence < 0.8):
            return "HIGH"
        else:
            return "CRITICAL"
    
    def concatenate_logs(self, logs: List[Dict]) -> str:
        """
        Concatenate anomalous logs for training.
        
        Args:
            logs: List of log records
            
        Returns:
            Concatenated log text
        """
        messages = []
        
        for log in logs:
            # Extract text fields (order matters for context)
            if isinstance(log, dict):
                if "message" in log:
                    messages.append(log["message"])
                elif "text" in log:
                    messages.append(log["text"])
                elif "log" in log:
                    messages.append(log["log"])
            elif isinstance(log, str):
                messages.append(log)
        
        return " ".join(messages)
    
    def scan_triage_records(
        self,
        max_records: Optional[int] = None
    ) -> List[Dict]:
        """
        Scan DynamoDB table for triage records.
        
        Args:
            max_records: Maximum number of records to retrieve
            
        Returns:
            List of triage records
        """
        records = []
        scan_kwargs = {}
        
        try:
            done = False
            last_evaluated_key = None
            
            while not done:
                if last_evaluated_key:
                    scan_kwargs["ExclusiveStartKey"] = last_evaluated_key
                
                response = self.table.scan(**scan_kwargs)
                records.extend(response.get("Items", []))
                
                last_evaluated_key = response.get("LastEvaluatedKey")
                done = last_evaluated_key is None
                
                if max_records and len(records) >= max_records:
                    records = records[:max_records]
                    break
                
                logger.info(f"Scanned {len(records)} records so far...")
            
            logger.info(f"Total records retrieved: {len(records)}")
            return records
        
        except ClientError as e:
            logger.error(f"DynamoDB error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise
    
    def build_training_dataset(
        self,
        records: List[Dict]
    ) -> Tuple[List[str], List[str]]:
        """
        Build training dataset from triage records.
        
        Args:
            records: List of triage records from DynamoDB
            
        Returns:
            Tuple of (texts, labels) for training
        """
        texts = []
        labels = []
        
        for record in records:
            # Extract fields
            anomalous_logs = record.get("anomalous_logs", [])
            is_critical = record.get("is_critical", False)
            needs_escalation = record.get("needs_escalation", False)
            confidence = record.get("confidence")
            
            # Skip if no logs
            if not anomalous_logs:
                continue
            
            # Concatenate logs
            text = self.concatenate_logs(anomalous_logs)
            
            # Skip if text is empty or too short
            if not text or len(text) < 10:
                continue
            
            # Infer severity label
            label = self.infer_severity(
                is_critical=is_critical,
                needs_escalation=needs_escalation,
                confidence=confidence
            )
            
            texts.append(text)
            labels.append(label)
        
        return texts, labels
    
    def save_dataset(
        self,
        texts: List[str],
        labels: List[str],
        output_file: str
    ):
        """
        Save training dataset to JSON file.
        
        Args:
            texts: List of training texts
            labels: List of training labels
            output_file: Output file path
        """
        dataset = {
            "texts": texts,
            "labels": labels,
            "metadata": {
                "total_samples": len(texts),
                "label_distribution": {}
            }
        }
        
        # Compute label distribution
        for label in self.SEVERITY_LEVELS:
            count = labels.count(label)
            dataset["metadata"]["label_distribution"][label] = count
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w") as f:
            json.dump(dataset, f, indent=2)
        
        logger.info(f"Dataset saved to {output_path}")
        logger.info(f"Total samples: {len(texts)}")
        logger.info(f"Label distribution: {dataset['metadata']['label_distribution']}")


def create_mock_training_data() -> Tuple[List[str], List[str]]:
    """
    Create mock training data for testing.
    
    In production, this would come from DynamoDB.
    
    Returns:
        Tuple of (texts, labels)
    """
    data = [
        # INFO level logs (normal operation)
        ("Connection established successfully from 192.168.1.100", "INFO"),
        ("Cache invalidation completed. TTL updated to 3600 seconds.", "INFO"),
        ("Background job scheduler started. 5 tasks queued.", "INFO"),
        ("Database connection pool initialized with 10 connections.", "INFO"),
        ("API rate limiter configured: 1000 requests per minute", "INFO"),
        ("Log aggregation pipeline started successfully", "INFO"),
        
        # WARNING level logs (needs attention)
        ("High latency detected: API response time 2.5s exceed baseline 500ms", "WARNING"),
        ("Memory usage warning: Currently at 78% of available heap", "WARNING"),
        ("Database query execution time increased by 40% compared to baseline", "WARNING"),
        ("Thread pool exhaustion warning: 95% of threads in use", "WARNING"),
        ("Retry attempt 3 of 5 for payment service timeout", "WARNING"),
        ("Queue depth alert: Message queue contains 500 pending items", "WARNING"),
        
        # HIGH level logs (needs immediate attention)
        ("ALERT: Service error rate spike detected: 5% of requests failing", "HIGH"),
        ("Critical resource exhaustion: Disk space at 90% capacity", "HIGH"),
        ("Database connection timeout: Failed to acquire connection after 30 seconds", "HIGH"),
        ("Multiple downstream service failures cascading through system", "HIGH"),
        ("Kafka broker unavailable: Message processing halted", "HIGH"),
        ("Unhandled exception in payment processing service", "HIGH"),
        
        # CRITICAL level logs (emergency)
        ("FATAL: CPU usage at 99% - system becoming unresponsive", "CRITICAL"),
        ("EMERGENCY: Unrecoverable database corruption detected in production", "CRITICAL"),
        ("CRITICAL ALERT: Data loss incident - automatic failover activated", "CRITICAL"),
        ("SECURITY BREACH: Unauthorized access detected from foreign IP", "CRITICAL"),
        ("Out of memory exception: Service terminating abnormally", "CRITICAL"),
        ("Catastrophic failure: All nodes in cluster unreachable", "CRITICAL"),
    ]
    
    texts, labels = zip(*data)
    return list(texts), list(labels)


def main():
    """Main entry point for training data extraction."""
    parser = argparse.ArgumentParser(
        description="Extract training data from DynamoDB for severity classifier"
    )
    parser.add_argument(
        "--table_name",
        default="nexus-triage",
        help="DynamoDB table name"
    )
    parser.add_argument(
        "--output_file",
        default="./data/severity_training.json",
        help="Output JSON file path"
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region"
    )
    parser.add_argument(
        "--max_records",
        type=int,
        help="Maximum number of records to retrieve"
    )
    parser.add_argument(
        "--use_mock",
        action="store_true",
        help="Use mock data instead of DynamoDB"
    )
    
    args = parser.parse_args()
    
    if args.use_mock:
        logger.info("Using mock training data...")
        texts, labels = create_mock_training_data()
        
        # Save mock dataset
        output_path = Path(args.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        dataset = {
            "texts": texts,
            "labels": labels,
            "metadata": {
                "total_samples": len(texts),
                "label_distribution": {}
            }
        }
        
        for label in ["INFO", "WARNING", "HIGH", "CRITICAL"]:
            count = labels.count(label)
            dataset["metadata"]["label_distribution"][label] = count
        
        with open(output_path, "w") as f:
            json.dump(dataset, f, indent=2)
        
        logger.info(f"Mock dataset saved to {output_path}")
        logger.info(f"Total samples: {len(texts)}")
        logger.info(f"Label distribution: {dataset['metadata']['label_distribution']}")
    
    else:
        # Extract from DynamoDB
        try:
            logger.info(f"Connecting to DynamoDB table: {args.table_name}")
            extractor = TrainingDataExtractor(
                table_name=args.table_name,
                region_name=args.region
            )
            
            logger.info("Scanning triage records...")
            records = extractor.scan_triage_records(max_records=args.max_records)
            
            logger.info("Building training dataset...")
            texts, labels = extractor.build_training_dataset(records)
            
            if not texts:
                logger.warning("No training samples extracted!")
                sys.exit(1)
            
            # Save dataset
            extractor.save_dataset(texts, labels, args.output_file)
        
        except ClientError as e:
            logger.error(f"DynamoDB connection error: {e}")
            logger.info("Falling back to mock data...")
            texts, labels = create_mock_training_data()
        
        except Exception as e:
            logger.error(f"Error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
