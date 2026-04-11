"""
Threshold Calibration for Autoencoder Anomaly Detection

This script calibrates the anomaly detection threshold based on a baseline
of "normal" log embeddings. The threshold is computed as:
    threshold = mean_error + (std_multiplier * std_error)

The calibrated threshold is stored in AWS SSM Parameter Store for easy access
by the Lambda function.

Usage:
    python scripts/calibrate_threshold.py \
        --model-path s3://bucket/autoencoder.pt \
        --baseline-log-group /aws/lambda/my-app \
        --baseline-days 7 \
        --std-multiplier 3.0 \
        --parameter-name /nexus/autoencoder/threshold
"""

import argparse
import logging
import torch
import numpy as np
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from nexus.models.autoencoder import LogAutoencoder, AutoencoderScorer

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def create_dummy_baseline_embeddings(n_samples: int = 5000) -> np.ndarray:
    """
    Create dummy baseline embeddings (from healthy logs).
    
    In production, these would come from CloudWatch logs marked as "normal"
    (e.g., no active alarms during the baseline period).
    
    Args:
        n_samples: Number of baseline embeddings
        
    Returns:
        Array of shape (n_samples, 768)
    """
    # Simulate embeddings from logs without anomalies
    # Tighter distribution than full data to represent "normal" state
    embeddings = np.random.normal(0, 0.05, (n_samples, 768)).astype(np.float32)
    return embeddings


def calibrate_threshold(
    model_path: str,
    baseline_embeddings: Optional[np.ndarray] = None,
    n_baseline_samples: int = 5000,
    std_multiplier: float = 3.0,
    device: Optional[torch.device] = None
) -> dict:
    """
    Calibrate anomaly detection threshold.
    
    Args:
        model_path: Path to saved autoencoder model
        baseline_embeddings: Pre-computed baseline embeddings (if None, generates dummy)
        n_baseline_samples: Number of baseline samples if generating dummy data
        std_multiplier: Multiplier for standard deviation
        device: torch.device
        
    Returns:
        Dict with calibration results
    """
    device = device or torch.device("cpu")
    
    logger.info("="*60)
    logger.info("Autoencoder Threshold Calibration")
    logger.info("="*60)
    
    # Load model
    logger.info(f"Loading model from {model_path}")
    model = LogAutoencoder(device=device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()
    logger.info("Model loaded successfully")
    
    # Create or use provided baseline embeddings
    if baseline_embeddings is None:
        logger.info(f"Generating {n_baseline_samples} dummy baseline embeddings...")
        baseline_embeddings = create_dummy_baseline_embeddings(n_baseline_samples)
    
    baseline_tensor = torch.from_numpy(baseline_embeddings).float()
    
    # Create scorer and calibrate
    scorer = AutoencoderScorer(model)
    logger.info(f"Calibrating threshold (std_multiplier={std_multiplier})...")
    threshold = scorer.calibrate_threshold(baseline_tensor, std_multiplier=std_multiplier)
    
    # Log calibration results
    logger.info("="*60)
    logger.info("Calibration Results:")
    logger.info(f"  Baseline Mean Error: {scorer.baseline_mean:.6f}")
    logger.info(f"  Baseline Std Error:  {scorer.baseline_std:.6f}")
    logger.info(f"  Computed Threshold:  {threshold:.6f}")
    logger.info("="*60)
    
    # Test on baseline data (should have low anomaly rate)
    result = scorer.score_logs(baseline_tensor)
    anomaly_rate = result["n_anomalies"] / len(baseline_embeddings)
    
    logger.info(f"Baseline Anomaly Rate: {anomaly_rate:.2%}")
    logger.info(f"  (Expected: ~0.13% for 3-sigma threshold)")
    
    return {
        "threshold": float(threshold),
        "baseline_mean": float(scorer.baseline_mean),
        "baseline_std": float(scorer.baseline_std),
        "std_multiplier": std_multiplier,
        "baseline_anomaly_rate": float(anomaly_rate),
        "n_baseline_samples": len(baseline_embeddings)
    }


def save_threshold_to_ssm(
    threshold: float,
    parameter_name: str = "/nexus/autoencoder/anomaly_threshold"
):
    """
    Save threshold to AWS SSM Parameter Store.
    
    Args:
        threshold: Threshold value to store
        parameter_name: SSM parameter name
    """
    import boto3
    
    logger.info(f"Saving threshold to SSM: {parameter_name}")
    
    ssm = boto3.client("ssm")
    ssm.put_parameter(
        Name=parameter_name,
        Value=str(threshold),
        Type="String",
        Overwrite=True,
        Tags=[
            {"Key": "Component", "Value": "Nexus"},
            {"Key": "Module", "Value": "Autoencoder"}
        ]
    )
    
    logger.info(f"✓ Threshold saved to SSM Parameter Store")


def save_threshold_to_dynamodb(
    threshold_data: dict,
    table_name: str = "nexus-ml-config"
):
    """
    Save full calibration data to DynamoDB for reference.
    
    Args:
        threshold_data: Calibration results dict
        table_name: DynamoDB table name
    """
    import boto3
    from datetime import datetime
    
    logger.info(f"Saving calibration data to DynamoDB: {table_name}")
    
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)
    
    item = {
        "model_id": "autoencoder-v1",
        "timestamp": datetime.utcnow().isoformat(),
        **threshold_data
    }
    
    table.put_item(Item=item)
    logger.info(f"✓ Calibration data saved to DynamoDB")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Calibrate autoencoder anomaly detection threshold"
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default="/tmp/autoencoder.pt",
        help="Path to trained autoencoder model"
    )
    parser.add_argument(
        "--baseline-samples",
        type=int,
        default=5000,
        help="Number of baseline samples for calibration"
    )
    parser.add_argument(
        "--std-multiplier",
        type=float,
        default=3.0,
        help="Multiplier for standard deviation"
    )
    parser.add_argument(
        "--parameter-name",
        type=str,
        default="/nexus/autoencoder/anomaly_threshold",
        help="SSM Parameter Store name"
    )
    parser.add_argument(
        "--save-to-ssm",
        action="store_true",
        help="Save threshold to SSM Parameter Store"
    )
    parser.add_argument(
        "--save-to-dynamodb",
        action="store_true",
        help="Save calibration data to DynamoDB"
    )
    
    args = parser.parse_args()
    
    # Calibrate
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    calibration_result = calibrate_threshold(
        model_path=args.model_path,
        n_baseline_samples=args.baseline_samples,
        std_multiplier=args.std_multiplier,
        device=device
    )
    
    # Save if requested
    if args.save_to_ssm:
        save_threshold_to_ssm(
            calibration_result["threshold"],
            args.parameter_name
        )
    
    if args.save_to_dynamodb:
        save_threshold_to_dynamodb(calibration_result)
    
    logger.info("Calibration complete!")
