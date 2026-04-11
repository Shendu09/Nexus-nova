"""
Inference script for proactive metric prediction.

This Lambda-friendly script loads trained forecasters and generates
predictions for all metrics. Designed to run on EventBridge schedule
(e.g., every 5 minutes) to continuously monitor breach probability.

Usage (from Lambda):
    event = {}  # EventBridge event
    response = lambda_handler(event, context)

Output:
    Publishes forecast results to SNS for downstream consumption
    Stores breach alerts in DynamoDB for dashboard visualization
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
import os

import boto3
from botocore.exceptions import ClientError

try:
    from nexus.models.forecaster import TimeSeriesForecast, ForecastingEngine
    _forecaster_available = True
except ImportError:
    _forecaster_available = False

# AWS clients
s3 = boto3.client("s3")
sns = boto3.client("sns")
dynamodb = boto3.resource("dynamodb")
cloudwatch = boto3.client("cloudwatch")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ForecastInferenceEngine:
    """Load and run inference on pre-trained forecasters."""
    
    MODELS_BUCKET = os.getenv("MODELS_BUCKET", "nexus-ml-models")
    MODELS_PREFIX = "forecasts/"
    
    def __init__(self):
        """Initialize engine."""
        self.forecasters: Dict[str, TimeSeriesForecast] = {}
        self.load_models()
    
    def load_models(self):
        """Load pre-trained models from S3."""
        try:
            logger.info("Loading forecast models from S3...")
            
            # List all metric folders
            response = s3.list_objects_v2(
                Bucket=self.MODELS_BUCKET,
                Prefix=self.MODELS_PREFIX,
                Delimiter="/"
            )
            
            if "CommonPrefixes" not in response:
                logger.warning("No forecasters found in S3")
                return
            
            for prefix_obj in response["CommonPrefixes"]:
                metric_name = prefix_obj["Prefix"].rstrip("/").split("/")[-1]
                
                try:
                    # Download model from S3
                    local_path = f"/tmp/{metric_name}"
                    self._download_model(metric_name, local_path)
                    
                    # Load forecaster
                    forecaster = TimeSeriesForecast.load(local_path)
                    self.forecasters[metric_name] = forecaster
                    
                    logger.info(f"Loaded forecaster for {metric_name}")
                
                except Exception as e:
                    logger.error(f"Failed to load {metric_name}: {e}")
            
            logger.info(f"Loaded {len(self.forecasters)} forecasters")
        
        except ClientError as e:
            logger.error(f"S3 error: {e}")
    
    def _download_model(self, metric_name: str, local_path: str):
        """Download model folder from S3."""
        try:
            response = s3.list_objects_v2(
                Bucket=self.MODELS_BUCKET,
                Prefix=f"{self.MODELS_PREFIX}{metric_name}/"
            )
            
            if "Contents" not in response:
                raise ValueError(f"No objects found for {metric_name}")
            
            os.makedirs(local_path, exist_ok=True)
            
            for obj in response["Contents"]:
                key = obj["Key"]
                filename = os.path.basename(key)
                
                s3.download_file(
                    self.MODELS_BUCKET,
                    key,
                    f"{local_path}/{filename}"
                )
        
        except ClientError as e:
            logger.error(f"Download error: {e}")
            raise
    
    def run_inference(self) -> Dict:
        """
        Run inference on all forecasters.
        
        Returns:
            Dictionary with forecast results for each metric
        """
        results = {}
        
        for metric_name, forecaster in self.forecasters.items():
            try:
                forecast_points = forecaster.forecast()
                
                # Aggregate breach probability
                breach_probs = [p.likelihood_breach for p in forecast_points]
                aggregate_breach_prob = 1.0 - np.prod([1 - p for p in breach_probs])
                
                # Find first breach time
                first_breach = None
                for point in forecast_points:
                    if point.likelihood_breach > 0.5:
                        first_breach = point.timestamp
                        break
                
                results[metric_name] = {
                    "metric": metric_name,
                    "threshold": forecaster.threshold,
                    "forecast_points": len(forecast_points),
                    "breach_probability": float(aggregate_breach_prob),
                    "first_breach_time": first_breach,
                    "sample_points": [
                        {
                            "timestamp": p.timestamp,
                            "value": float(p.value),
                            "lower": float(p.yhat_lower),
                            "upper": float(p.yhat_upper),
                            "breach_likelihood": float(p.likelihood_breach)
                        }
                        for p in forecast_points[:3]  # First 3 points
                    ]
                }
            
            except Exception as e:
                logger.error(f"Inference error for {metric_name}: {e}")
                results[metric_name] = {
                    "metric": metric_name,
                    "error": str(e)
                }
        
        return results
    
    def publish_results(self, results: Dict, topic_arn: str):
        """Publish results to SNS."""
        try:
            sns.publish(
                TopicArn=topic_arn,
                Subject="Nexus Forecast Update",
                Message=json.dumps(results, indent=2)
            )
            logger.info("Published results to SNS")
        
        except ClientError as e:
            logger.error(f"SNS publish error: {e}")
    
    def store_alert_metrics(self, results: Dict):
        """Store breach alerts in DynamoDB."""
        table = dynamodb.Table("nexus-forecast-alerts")
        now = datetime.now().isoformat()
        
        for metric_name, result in results.items():
            if "breach_probability" in result:
                try:
                    breach_prob = result["breach_probability"]
                    
                    # Only store if breach probability > threshold
                    if breach_prob > 0.3:
                        table.put_item(
                            Item={
                                "metric": metric_name,
                                "timestamp": now,
                                "breach_probability": breach_prob,
                                "first_breach_time": result.get("first_breach_time"),
                                "threshold": result.get("threshold"),
                                "ttl": int(datetime.now().timestamp()) + (24 * 3600)  # 24h TTL
                            }
                        )
                except ClientError as e:
                    logger.error(f"DynamoDB error: {e}")
    
    def emit_metrics(self, results: Dict):
        """Emit CloudWatch metrics."""
        try:
            metric_data = []
            
            for metric_name, result in results.items():
                if "breach_probability" not in result:
                    continue
                
                metric_data.append({
                    "MetricName": f"Forecast-{metric_name}-BreachProbability",
                    "Value": result["breach_probability"],
                    "Unit": "Percent",
                    "Timestamp": datetime.now()
                })
            
            if metric_data:
                for i in range(0, len(metric_data), 20):  # Batch limit
                    cloudwatch.put_metric_data(
                        Namespace="Nexus/Forecasts",
                        MetricData=metric_data[i:i+20]
                    )
                logger.info(f"Emitted {len(metric_data)} CloudWatch metrics")
        
        except ClientError as e:
            logger.error(f"CloudWatch error: {e}")


def lambda_handler(event, context):
    """
    Lambda handler for periodic forecasting.
    
    Triggered by EventBridge schedule rule every 5 minutes.
    """
    logger.info("Starting forecast inference...")
    
    try:
        # Initialize engine
        engine = ForecastInferenceEngine()
        
        # Run inference
        results = engine.run_inference()
        
        # Store and publish results
        sns_topic = os.getenv("SNS_TOPIC_ARN")
        if sns_topic:
            engine.publish_results(results, sns_topic)
        
        engine.store_alert_metrics(results)
        engine.emit_metrics(results)
        
        # Return results
        return {
            "statusCode": 200,
            "body": json.dumps(results)
        }
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }


def invocation_example():
    """Example of running inference locally."""
    import numpy as np
    
    if not _forecaster_available:
        print("Forecaster module not available")
        return
    
    engine = ForecastInferenceEngine()
    results = engine.run_inference()
    
    print("Forecast Results:")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    import numpy as np
    invocation_example()
