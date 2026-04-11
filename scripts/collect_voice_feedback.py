"""
Voice Feedback Collection and Processing Pipeline

This module handles collecting feedback from engineers after voice calls
and processing it for RL model training. Stores feedback in DynamoDB
with incident/suggestion pairs for later RLHF training.

Feedback includes:
- Overall satisfaction (0-10 scale)
- Suggestion quality rating (0-10 scale)
- Was the suggestion relevant? (boolean)
- Did it help resolve the incident? (boolean)
- What suggestions would have been better? (text comments)
- Metadata: call duration, incident severity, etc.

Usage:
    from nexus.rlhf import VoiceFeedbackCollector
    
    collector = VoiceFeedbackCollector()
    feedback = {
        "incident_id": "inc-12345",
        "suggestion": "Check CPU metrics",
        "satisfaction": 8,
        "was_helpful": True,
        "engineer_id": "eng-789"
    }
    collector.store_feedback(feedback)
"""

import json
import logging
from datetime import datetime
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import uuid

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


@dataclass
class VoiceFeedback:
    """Voice call feedback record."""
    feedback_id: str
    incident_id: str
    suggestion: str
    suggestion_quality: int  # 0-10
    relevance_score: float  # 0-1
    was_helpful: bool
    engineer_comments: Optional[str] = None
    overall_satisfaction: int = 5  # 0-10
    timestamp: Optional[str] = None
    call_duration_seconds: Optional[int] = None
    incident_severity: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


class VoiceFeedbackCollector:
    """Collects and stores voice feedback from engineers."""
    
    def __init__(
        self,
        table_name: str = "nexus-voice-feedback",
        region: str = "us-east-1"
    ):
        """
        Initialize feedback collector.
        
        Args:
            table_name: DynamoDB table for storing feedback
            region: AWS region
        """
        self.dynamodb = boto3.resource("dynamodb", region_name=region)
        self.table = self.dynamodb.Table(table_name)
        self.table_name = table_name
    
    def collect_feedback(self, incident_id: str, suggestion: str) -> VoiceFeedback:
        """
        Create new feedback record.
        
        Args:
            incident_id: ID of the incident
            suggestion: The Nova suggestion that was given
            
        Returns:
            VoiceFeedback object with auto-generated ID and timestamp
        """
        feedback_id = f"fb-{uuid.uuid4().hex[:12]}"
        timestamp = datetime.now().isoformat()
        
        feedback = VoiceFeedback(
            feedback_id=feedback_id,
            incident_id=incident_id,
            suggestion=suggestion,
            suggestion_quality=5,  # Default middle value, engineer will update
            relevance_score=0.5,
            was_helpful=False,
            timestamp=timestamp
        )
        
        return feedback
    
    def store_feedback(
        self,
        feedback: VoiceFeedback
    ) -> bool:
        """
        Store feedback record in DynamoDB.
        
        Args:
            feedback: VoiceFeedback object
            
        Returns:
            True if successful
        """
        try:
            feedback_dict = feedback.to_dict()
            
            # Set TTL: 90 days
            feedback_dict["ttl"] = int(datetime.now().timestamp()) + (90 * 24 * 3600)
            
            self.table.put_item(Item=feedback_dict)
            
            logger.info(f"Stored feedback {feedback.feedback_id} for incident {feedback.incident_id}")
            return True
        
        except ClientError as e:
            logger.error(f"DynamoDB error storing feedback: {e}")
            return False
    
    def get_feedback_for_training(
        self,
        min_records: int = 100,
        quality_threshold: int = 6
    ) -> List[VoiceFeedback]:
        """
        Retrieve feedback suitable for training.
        
        Filters for:
        - Suggestion quality >= threshold
        - Include both helpful and unhelpful for contrast
        
        Args:
            min_records: Minimum records to attempt retrieval
            quality_threshold: Min suggestion quality (0-10)
            
        Returns:
            List of VoiceFeedback records
        """
        try:
            # Scan table for high-quality feedback
            response = self.table.scan(
                FilterExpression="suggestion_quality >= :sq",
                ExpressionAttributeValues={":sq": quality_threshold},
                Limit=min_records * 2
            )
            
            items = response.get("Items", [])
            logger.info(f"Retrieved {len(items)} feedback records for training")
            
            return [self._dict_to_feedback(item) for item in items]
        
        except ClientError as e:
            logger.error(f"Error retrieving feedback: {e}")
            return []
    
    def _dict_to_feedback(self, item: Dict) -> VoiceFeedback:
        """Convert DynamoDB item to VoiceFeedback."""
        return VoiceFeedback(
            feedback_id=item.get("feedback_id", ""),
            incident_id=item.get("incident_id", ""),
            suggestion=item.get("suggestion", ""),
            suggestion_quality=item.get("suggestion_quality", 5),
            relevance_score=item.get("relevance_score", 0.5),
            was_helpful=item.get("was_helpful", False),
            engineer_comments=item.get("engineer_comments"),
            overall_satisfaction=item.get("overall_satisfaction", 5),
            timestamp=item.get("timestamp"),
            call_duration_seconds=item.get("call_duration_seconds"),
            incident_severity=item.get("incident_severity")
        )
    
    def get_feedback_statistics(self) -> Dict[str, Any]:
        """Get overall feedback statistics."""
        try:
            # Scan all feedback (in production, use aggregation table)
            response = self.table.scan(Select="ALL_ATTRIBUTES", Limit=10000)
            items = response.get("Items", [])
            
            if not items:
                return {"total_feedback": 0}
            
            qualities = [item.get("suggestion_quality", 5) for item in items]
            satisfactions = [item.get("overall_satisfaction", 5) for item in items]
            helpful_count = sum(1 for item in items if item.get("was_helpful", False))
            
            return {
                "total_feedback": len(items),
                "avg_suggestion_quality": sum(qualities) / len(qualities),
                "avg_satisfaction": sum(satisfactions) / len(satisfactions),
                "helpful_count": helpful_count,
                "helpful_rate": helpful_count / len(items),
            }
        
        except ClientError as e:
            logger.error(f"Error getting statistics: {e}")
            return {}


class FeedbackAnalyzer:
    """Analyzes feedback for insights."""
    
    def __init__(self, collector: VoiceFeedbackCollector):
        """Initialize analyzer."""
        self.collector = collector
    
    def get_trending_suggestions(self, top_k: int = 10) -> List[Dict[str, Any]]:
        """Get most frequently given suggestions."""
        feedback = self.collector.get_feedback_for_training(min_records=1000)
        
        suggestion_stats = {}
        for fb in feedback:
            sugg = fb.suggestion
            if sugg not in suggestion_stats:
                suggestion_stats[sugg] = {
                    "count": 0,
                    "avg_quality": 0,
                    "helpful_rate": 0,
                    "qualities": [],
                    "helpful": 0
                }
            
            suggestion_stats[sugg]["count"] += 1
            suggestion_stats[sugg]["qualities"].append(fb.suggestion_quality)
            if fb.was_helpful:
                suggestion_stats[sugg]["helpful"] += 1
        
        # Compute averages
        for sugg, stats in suggestion_stats.items():
            stats["avg_quality"] = sum(stats["qualities"]) / len(stats["qualities"])
            stats["helpful_rate"] = stats["helpful"] / stats["count"]
            del stats["qualities"]
        
        # Sort by frequency
        trending = sorted(
            suggestion_stats.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )[:top_k]
        
        return [
            {
                "suggestion": sugg,
                **stats
            }
            for sugg, stats in trending
        ]
    
    def identify_problematic_suggestions(self, quality_threshold: int = 4) -> List[Dict]:
        """Identify suggestions with poor feedback."""
        feedback = self.collector.get_feedback_for_training(min_records=500)
        
        bad_suggestions = []
        for fb in feedback:
            if fb.suggestion_quality <= quality_threshold:
                bad_suggestions.append({
                    "suggestion": fb.suggestion,
                    "quality": fb.suggestion_quality,
                    "was_helpful": fb.was_helpful,
                    "comments": fb.engineer_comments,
                    "incident_severity": fb.incident_severity
                })
        
        return bad_suggestions


class LocalFeedbackStore:
    """Local file-based feedback store for testing/demo."""
    
    def __init__(self, store_path: str = "./data/feedback"):
        """Initialize local store."""
        self.store_path = Path(store_path)
        self.store_path.mkdir(parents=True, exist_ok=True)
        self.feedback_file = self.store_path / "feedback.jsonl"
    
    def store_feedback(self, feedback: VoiceFeedback) -> bool:
        """Store feedback to local file."""
        try:
            with open(self.feedback_file, "a") as f:
                json.dump(feedback.to_dict(), f)
                f.write("\n")
            return True
        except Exception as e:
            logger.error(f"Error storing locally: {e}")
            return False
    
    def get_feedback_for_training(
        self,
        min_records: int = 100
    ) -> List[VoiceFeedback]:
        """Load feedback from local file."""
        feedback_list = []
        
        try:
            if not self.feedback_file.exists():
                logger.warning(f"Feedback file not found: {self.feedback_file}")
                return []
            
            with open(self.feedback_file, "r") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        fb = VoiceFeedback(
                            feedback_id=data.get("feedback_id", ""),
                            incident_id=data.get("incident_id", ""),
                            suggestion=data.get("suggestion", ""),
                            suggestion_quality=data.get("suggestion_quality", 5),
                            relevance_score=data.get("relevance_score", 0.5),
                            was_helpful=data.get("was_helpful", False),
                            engineer_comments=data.get("engineer_comments"),
                            overall_satisfaction=data.get("overall_satisfaction", 5),
                            timestamp=data.get("timestamp"),
                            call_duration_seconds=data.get("call_duration_seconds"),
                            incident_severity=data.get("incident_severity")
                        )
                        feedback_list.append(fb)
                    except json.JSONDecodeError:
                        continue
        
        except Exception as e:
            logger.error(f"Error loading feedback: {e}")
        
        return feedback_list
