"""
Threshold calibration script for LSTM-based log anomaly detector (Module 1).

Performs:
1. Load trained LSTM model (or train new one)
2. Score log sequences from a baseline "normal" period
3. Compute threshold at specified percentile
4. Save threshold to AWS SSM Parameter Store and DynamoDB
5. Generate calibration report

The calibration is critical for tuning false positive/negative rates.

Usage:
    python scripts/calibrate_lstm_threshold.py \\
        --model-path /tmp/lstm_model.pt \\
        --percentile 95 \\
        --save-to-ssm \\
        --parameter-name /nexus/lstm/anomaly_threshold
"""

import argparse
import json
import logging
import numpy as np
import torch
from pathlib import Path
from typing import Dict, Optional, Tuple
import os
from datetime import datetime

from nexus.models.lstm import (
    LogAnomalyLSTM,
    LogAnomalyLSTMConfig,
    LogAnomalyLSTMScorer,
    LogSequenceDataset
)

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def create_dummy_baseline_embeddings(
    num_samples: int = 5000,
    embedding_dim: int = 768,
    seed: int = 42
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Create synthetic baseline embeddings from a "normal" period.
    
    In production, these would be:
    - Retrieved from CloudWatch Logs
    - Filtered to a known-healthy baseline period (e.g., last Sunday, no alarms)
    - Embedded using Nova Embeddings API
    
    For testing, we create synthetic normal logs with minimal anomalies.
    
    Args:
        num_samples: Number of embeddings to generate
        embedding_dim: Dimensionality of embeddings
        seed: Random seed for reproducibility
    
    Returns:
        Tuple of (embeddings, labels) for baseline period
    """
    np.random.seed(seed)
    
    # Normal logs: Gaussian distribution
    embeddings = np.random.normal(
        loc=0.0,
        scale=0.5,
        size=(num_samples, embedding_dim)
    )
    
    # Baseline is mostly normal (assume 95% normal, 5% undetected anomalies)
    labels = np.zeros(num_samples)
    anomaly_indices = np.random.choice(num_samples, size=int(num_samples * 0.05), replace=False)
    labels[anomaly_indices] = 1
    
    logger.info(f"Created baseline with {num_samples} embeddings ({np.sum(labels)} anomalies)")
    
    return embeddings, labels


def calibrate_lstm_threshold(
    model_path: str,
    num_baseline_samples: int = 5000,
    percentile: float = 95.0,
    device: str = "cpu"
) -> Dict[str, any]:
    """
    Calibrate LSTM anomaly threshold from baseline data.
    
    Args:
        model_path: Path to saved LSTM model weights
        num_baseline_samples: Number of baseline logs to score
        percentile: Percentile for threshold computation
        device: "cpu" or "cuda"
    
    Returns:
        Dictionary with calibration results
    """
    logger.info("=== LSTM Threshold Calibration ===")
    
    # 1. Load model
    logger.info(f"Loading model from {model_path}")
    config = LogAnomalyLSTMConfig(device=device)
    model = LogAnomalyLSTM(config)
    
    try:
        model.load_state_dict(torch.load(model_path, map_location=device))
        logger.info("Model loaded successfully")
    except FileNotFoundError:
        logger.warning(f"Model not found at {model_path}. Using untrained model.")
    
    # 2. Create scorer
    scorer = LogAnomalyLSTMScorer(model, config=config)
    
    # 3. Create baseline data
    baseline_embeddings, baseline_labels = create_dummy_baseline_embeddings(
        num_samples=num_baseline_samples
    )
    
    # 4. Calibrate threshold
    threshold = scorer.calibrate_threshold(
        baseline_embeddings=baseline_embeddings,
        baseline_labels=baseline_labels,
        percentile=percentile
    )
    
    logger.info(f"Calibrated threshold: {threshold:.4f}")
    
    # 5. Generate statistics
    # Score all baseline
    scores = scorer.score_sequences_batch(baseline_embeddings)
    
    # Separate normal and anomaly scores
    normal_mask = baseline_labels == 0
    anomaly_mask = baseline_labels == 1
    
    normal_scores = scores[normal_mask] if np.any(normal_mask) else np.array([])
    anomaly_scores = scores[anomaly_mask] if np.any(anomaly_mask) else np.array([])
    
    calibration_stats = {
        'threshold': float(threshold),
        'percentile': percentile,
        'baseline_samples': num_baseline_samples,
        'normal_samples': np.sum(normal_mask),
        'anomaly_samples': np.sum(anomaly_mask),
        'normal_scores': {
            'mean': float(np.mean(normal_scores)) if len(normal_scores) > 0 else 0.0,
            'std': float(np.std(normal_scores)) if len(normal_scores) > 0 else 0.0,
            'min': float(np.min(normal_scores)) if len(normal_scores) > 0 else 0.0,
            'max': float(np.max(normal_scores)) if len(normal_scores) > 0 else 0.0,
            'percentile_95': float(np.percentile(normal_scores, 95)) if len(normal_scores) > 0 else 0.0,
        },
        'anomaly_scores': {
            'mean': float(np.mean(anomaly_scores)) if len(anomaly_scores) > 0 else 0.0,
            'std': float(np.std(anomaly_scores)) if len(anomaly_scores) > 0 else 0.0,
            'min': float(np.min(anomaly_scores)) if len(anomaly_scores) > 0 else 0.0,
            'max': float(np.max(anomaly_scores)) if len(anomaly_scores) > 0 else 0.0,
        },
        'threshold_coverage': {
            'false_positive_rate': float(np.mean(normal_scores >= threshold)) if len(normal_scores) > 0 else 0.0,
            'true_positive_rate': float(np.mean(anomaly_scores >= threshold)) if len(anomaly_scores) > 0 else 0.0,
        },
        'timestamp': datetime.utcnow().isoformat(),
    }
    
    logger.info("\nCalibration Statistics:")
    logger.info(f"  Normal samples: {calibration_stats['normal_samples']}")
    logger.info(f"  Anomaly samples: {calibration_stats['anomaly_samples']}")
    logger.info(f"  Normal score range: [{calibration_stats['normal_scores']['min']:.3f}, {calibration_stats['normal_scores']['max']:.3f}]")
    logger.info(f"  Anomaly score range: [{calibration_stats['anomaly_scores']['min']:.3f}, {calibration_stats['anomaly_scores']['max']:.3f}]")
    logger.info(f"  False positive rate: {calibration_stats['threshold_coverage']['false_positive_rate']*100:.1f}%")
    logger.info(f"  True positive rate: {calibration_stats['threshold_coverage']['true_positive_rate']*100:.1f}%")
    
    return calibration_stats


def save_threshold_to_ssm(
    parameter_name: str,
    threshold: float,
    overwrite: bool = True
) -> str:
    """
    Save threshold to AWS Systems Manager Parameter Store.
    
    Makes threshold accessible to Lambda functions at runtime.
    
    Args:
        parameter_name: SSM parameter name (e.g., /nexus/lstm/anomaly_threshold)
        threshold: Threshold value
        overwrite: Whether to overwrite existing parameter
    
    Returns:
        Parameter ARN
    """
    try:
        import boto3
        ssm = boto3.client("ssm", region_name="us-east-1")
        
        response = ssm.put_parameter(
            Name=parameter_name,
            Value=str(threshold),
            Type="String",
            Description="LSTM anomaly detection threshold",
            Overwrite=overwrite
        )
        
        logger.info(f"Saved threshold to SSM: {parameter_name} = {threshold}")
        return response['Version']
    
    except ImportError:
        logger.warning("boto3 not available; skipping SSM save")
        return ""
    except Exception as e:
        logger.error(f"Failed to save to SSM: {e}")
        return ""


def save_threshold_to_dynamodb(
    table_name: str,
    calibration_stats: Dict[str, any],
    item_id: str = "lstm_latest"
) -> bool:
    """
    Save full calibration statistics to DynamoDB.
    
    Enables historical tracking and audit trail of threshold changes.
    
    Args:
        table_name: DynamoDB table name
        calibration_stats: Full calibration results dictionary
        item_id: Partition key value
    
    Returns:
        True if successful, False otherwise
    """
    try:
        import boto3
        from boto3.dynamodb.conditions import Key
        
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.Table(table_name)
        
        item = {
            'id': item_id,
            'module': 'lstm',
            'calibration_stats': json.dumps(calibration_stats),
            'timestamp': datetime.utcnow().isoformat(),
        }
        
        table.put_item(Item=item)
        
        logger.info(f"Saved calibration to DynamoDB table {table_name}")
        return True
    
    except ImportError:
        logger.warning("boto3 not available; skipping DynamoDB save")
        return False
    except Exception as e:
        logger.error(f"Failed to save to DynamoDB: {e}")
        return False


def main(
    model_path: str = "/tmp/lstm_model.pt",
    num_baseline_samples: int = 5000,
    percentile: float = 95.0,
    save_to_ssm: bool = False,
    parameter_name: str = "/nexus/lstm/anomaly_threshold",
    save_to_dynamodb: bool = False,
    dynamodb_table: str = "LSTMCalibration",
    output_path: Optional[str] = None,
    device: str = "cpu"
) -> Dict[str, any]:
    """
    Main calibration function.
    
    Args:
        model_path: Path to trained model
        num_baseline_samples: Size of baseline dataset
        percentile: Percentile for threshold
        save_to_ssm: Whether to save to AWS SSM
        parameter_name: SSM parameter name
        save_to_dynamodb: Whether to save to DynamoDB
        dynamodb_table: DynamoDB table name
        output_path: Optional local JSON file to save results
        device: "cpu" or "cuda"
    
    Returns:
        Calibration results dictionary
    """
    # Calibrate
    calibration_stats = calibrate_lstm_threshold(
        model_path=model_path,
        num_baseline_samples=num_baseline_samples,
        percentile=percentile,
        device=device
    )
    
    # Save to SSM
    if save_to_ssm:
        save_threshold_to_ssm(parameter_name, calibration_stats['threshold'])
    
    # Save to DynamoDB
    if save_to_dynamodb:
        save_threshold_to_dynamodb(dynamodb_table, calibration_stats)
    
    # Save to local file
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(calibration_stats, f, indent=2)
        logger.info(f"Saved calibration to {output_path}")
    
    return calibration_stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Calibrate LSTM anomaly detection threshold"
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default="/tmp/lstm_model.pt",
        help="Path to trained LSTM model"
    )
    parser.add_argument(
        "--num-baseline-samples",
        type=int,
        default=5000,
        help="Number of baseline (normal) logs to score"
    )
    parser.add_argument(
        "--percentile",
        type=float,
        default=95.0,
        help="Percentile for threshold (e.g., 95 for 5% FPR on normal)"
    )
    parser.add_argument(
        "--save-to-ssm",
        action="store_true",
        help="Save threshold to AWS SSM Parameter Store"
    )
    parser.add_argument(
        "--parameter-name",
        type=str,
        default="/nexus/lstm/anomaly_threshold",
        help="SSM parameter name"
    )
    parser.add_argument(
        "--save-to-dynamodb",
        action="store_true",
        help="Save calibration stats to DynamoDB"
    )
    parser.add_argument(
        "--dynamodb-table",
        type=str,
        default="LSTMCalibration",
        help="DynamoDB table name"
    )
    parser.add_argument(
        "--output-path",
        type=str,
        default=None,
        help="Optional path to save results as JSON"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        choices=["cpu", "cuda"],
        help="Device for inference"
    )
    
    args = parser.parse_args()
    
    results = main(
        model_path=args.model_path,
        num_baseline_samples=args.num_baseline_samples,
        percentile=args.percentile,
        save_to_ssm=args.save_to_ssm,
        parameter_name=args.parameter_name,
        save_to_dynamodb=args.save_to_dynamodb,
        dynamodb_table=args.dynamodb_table,
        output_path=args.output_path,
        device=args.device
    )
    
    logger.info("\nCalibration complete!")
    logger.info(json.dumps({k: v for k, v in results.items() if k != 'calibration_stats'}, indent=2))
