"""
Training script for time-series forecasting models.

This script fits Prophet models on historical CloudWatch metrics and
prepares them for deployment in Lambda for proactive forecasting.

Historical metrics are fetched from CloudWatch using boto3.

Usage:
    python scripts/train_prophet_model.py \
        --metric cpu_utilization \
        --days 30 \
        --output_dir ./models/forecasts

AWS Requirements:
    - CloudWatch Metrics data
    - IAM permissions: cloudwatch:GetMetricStatistics
"""

import logging
import argparse
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
from pathlib import Path
import json

import boto3
from botocore.exceptions import ClientError
import numpy as np
import pandas as pd

from nexus.models.forecaster import TimeSeriesForecast, ForecastingEngine

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CloudWatchMetricsCollector:
    """Fetch historical metrics from AWS CloudWatch."""
    
    def __init__(self, region_name: str = "us-east-1"):
        """Initialize CloudWatch client."""
        self.cloudwatch = boto3.client("cloudwatch", region_name=region_name)
    
    def get_metric_statistics(
        self,
        namespace: str,
        metric_name: str,
        dimensions: List[Dict],
        start_time: datetime,
        end_time: datetime,
        period: int = 300,
        statistic: str = "Average"
    ) -> List[Tuple[datetime, float]]:
        """
        Fetch metric statistics from CloudWatch.
        
        Args:
            namespace: CloudWatch namespace (e.g., "AWS/Lambda")
            metric_name: Metric name 
            dimensions: List of dimension dicts
            start_time: Start of time range
            end_time: End of time range
            period: Period in seconds (default: 5 minutes)
            statistic: Statistic type (Average, Maximum, Minimum, Sum)
            
        Returns:
            List of (timestamp, value) tuples
        """
        try:
            response = self.cloudwatch.get_metric_statistics(
                Namespace=namespace,
                MetricName=metric_name,
                Dimensions=dimensions,
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=[statistic]
            )
            
            # Convert to list of tuples, sorted by timestamp
            datapoints = response["Datapoints"]
            datapoints.sort(key=lambda x: x["Timestamp"])
            
            return [
                (point["Timestamp"], point[statistic])
                for point in datapoints
            ]
        
        except ClientError as e:
            logger.error(f"CloudWatch error: {e}")
            return []
    
    def create_dummy_metrics(
        self,
        metric_name: str,
        days: int = 30
    ) -> Tuple[List[datetime], List[float]]:
        """
        Create realistic dummy metrics for testing.
        
        Simulates patterns like:
        - Daily cyclical pattern (peak in business hours)
        - Weekly pattern (lower on weekends)
        - Random noise
        - Occasional spikes
        
        Args:
            metric_name: Name of metric to simulate
            days: Number of days of history
            
        Returns:
            Tuple of (timestamps, values)
        """
        timestamps = []
        values = []
        
        # Generate 5-minute data points
        now = datetime.now()
        periods = days * 24 * 12  # 5-min intervals
        
        for i in range(periods):
            ts = now - timedelta(minutes=periods * 5) + timedelta(minutes=i * 5)
            timestamps.append(ts)
            
            # Create realistic pattern
            hour_of_day = ts.hour
            day_of_week = ts.weekday()
            
            # Base value (varies by metric)
            if metric_name == "cpu_utilization":
                base = 40.0
                peak_hour = 14  # 2 PM
            elif metric_name == "memory_usage":
                base = 45.0
                peak_hour = 12
            elif metric_name == "error_rate":
                base = 0.5
                peak_hour = 10
            elif metric_name == "latency_p99":
                base = 200.0
                peak_hour = 15
            else:
                base = 50.0
                peak_hour = 12
            
            # Daily cycle (higher during peak hours)
            daily_factor = 1.0 + 0.3 * np.sin(2 * np.pi * (hour_of_day - peak_hour) / 24)
            
            # Weekly cycle (lower on weekends)
            weekly_factor = 1.0 if day_of_week < 5 else 0.7
            
            # Random noise
            noise = np.random.normal(0, base * 0.05)
            
            # Occasional spike
            spike = 1.5 if np.random.random() < 0.02 else 1.0
            
            value = base * daily_factor * weekly_factor * spike + noise
            value = max(0, value)  # Non-negative
            
            values.append(value)
        
        return timestamps, values


def train_single_metric(
    metric_name: str,
    timestamps: List[datetime],
    values: List[float],
    output_dir: str,
    threshold: Optional[float] = None
) -> TimeSeriesForecast:
    """Train forecaster for a single metric."""
    logger.info(f"Training forecaster for {metric_name}...")
    
    forecaster = TimeSeriesForecast(metric_name, threshold=threshold)
    forecaster.fit(timestamps, values)
    
    # Generate sample forecast
    forecast_points = forecaster.forecast()
    logger.info(f"Generated {len(forecast_points)} forecast points")
    
    # Calculate statistics
    forecast_values = [p.value for p in forecast_points]
    logger.info(
        f"{metric_name} forecast range: {min(forecast_values):.2f} - {max(forecast_values):.2f}"
    )
    
    # Save model
    save_path = Path(output_dir) / metric_name
    forecaster.save(str(save_path))
    
    return forecaster


def main():
    """Main training entry point."""
    parser = argparse.ArgumentParser(
        description="Train Prophet forecasting models"
    )
    parser.add_argument(
        "--metric",
        choices=TimeSeriesForecast.SUPPORTED_METRICS,
        help="Specific metric to train (trains all if omitted)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Historical data span in days"
    )
    parser.add_argument(
        "--output_dir",
        default="./models/forecasts",
        help="Output directory for models"
    )
    parser.add_argument(
        "--live_cloudwatch",
        action="store_true",
        help="Fetch real data from CloudWatch (requires AWS credentials)"
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region"
    )
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    metrics_to_train = [args.metric] if args.metric else TimeSeriesForecast.SUPPORTED_METRICS
    
    if args.live_cloudwatch:
        logger.info("Collecting metrics from CloudWatch...")
        collector = CloudWatchMetricsCollector(region_name=args.region)
        
        # TODO: Implement CloudWatch data fetching
        # For now, create dummy data
        logger.warning("CloudWatch data collection not fully implemented. Using dummy data.")
    
    # Train models
    for metric in metrics_to_train:
        logger.info(f"\nTraining {metric}...")
        
        # Collect data (using dummy data for now)
        collector = CloudWatchMetricsCollector()
        timestamps, values = collector.create_dummy_metrics(metric, days=args.days)
        
        logger.info(f"Collected {len(timestamps)} data points for {metric}")
        
        # Train forecaster
        forecaster = train_single_metric(
            metric,
            timestamps,
            values,
            str(output_dir),
            threshold=None  # Use default threshold
        )
    
    # Generate summary report
    summary = {
        "timestamp": datetime.now().isoformat(),
        "metrics_trained": metrics_to_train,
        "data_span_days": args.days,
        "output_directory": str(output_dir)
    }
    
    summary_path = output_dir / "training_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"\nTraining complete. Summary saved to {summary_path}")


if __name__ == "__main__":
    main()
