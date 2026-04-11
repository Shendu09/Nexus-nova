"""
SimCSE Embedding Fine-tuning Training Script

Fine-tunes sentence-transformers embeddings on log data for better
semantic representations. Output embeddings are optimized for:
- Anomaly detection (used by autoencoder)
- Log clustering
- Incident similarity

Usage:
    python scripts/train_embeddings.py \
        --output_dir ./models/embeddings_finetuned \
        --num_epochs 3 \
        --batch_size 32

Data Source:
    - Can use historical logs from CloudWatch
    - Or dummy data with realistic log patterns
    - Requires log messages and incident grouping
"""

import logging
import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple
import numpy as np
import random

try:
    from nexus.models.embeddings import SimCSETrainer, SimCSEEmbedder
    _embeddings_available = True
except ImportError:
    _embeddings_available = False

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LogDataGenerator:
    """Generate realistic log data for training."""
    
    LOG_TEMPLATES = {
        "CPU": [
            "CPU utilization at {cpu}% on {service}",
            "High CPU alert: {service} consuming {cpu}% of resources",
            "CPU threshold exceeded for {service}: {cpu}%",
            "[{service}] CPU spike detected: {cpu}%"
        ],
        "Memory": [
            "Memory usage: {memory}% for {service}",
            "OOM risk: {service} at {memory}% memory",
            "Memory threshold warning: {service} {memory}%",
            "[WARNING] High memory on {service}: {memory}%"
        ],
        "Error": [
            "Error rate spike: {service} {error_rate}% of requests",
            "[ERROR] {service} failing at {error_rate}%",
            "Service {service} error threshold: {error_rate}%",
            "High error rate {error_rate}% from {service}"
        ],
        "Latency": [
            "Latency alert: {service} P99={latency}ms",
            "Slow response: {service} latency {latency}ms",
            "[LATENCY] {service} is slow: {latency}ms P99",
            "P99 latency spike for {service}: {latency}ms"
        ],
        "Dependency": [
            "Dependency {dep} down, affecting {service}",
            "[ALERT] {dep} unavailable for {service}",
            "Service {service} blocked by {dep} failure",
            "Circuit breaker open for {dep}: {service} impacted"
        ]
    }
    
    SERVICES = [
        "api-gateway", "user-service", "order-service",
        "payment-service", "inventory-service", "notification-service"
    ]
    
    DEPENDENCIES = [
        "database", "redis-cache", "elasticsearch", "kafka",
        "auth-service", "shipping-service"
    ]
    
    def __init__(self, seed: int = 42):
        """Initialize generator."""
        random.seed(seed)
        np.random.seed(seed)
    
    def generate_incident_logs(
        self,
        num_incidents: int = 100,
        logs_per_incident: int = 10
    ) -> Tuple[List[str], List[str]]:
        """
        Generate logs grouped by incident.
        
        Args:
            num_incidents: Number of incidents to generate
            logs_per_incident: Logs per incident
            
        Returns:
            Tuple of (logs, incident_ids)
        """
        logs = []
        incident_ids = []
        
        for inc_id in range(num_incidents):
            incident_id = f"inc-{inc_id:05d}"
            
            # Choose incident type
            incident_type = random.choice(list(self.LOG_TEMPLATES.keys()))
            templates = self.LOG_TEMPLATES[incident_type]
            
            for log_idx in range(logs_per_incident):
                template = random.choice(templates)
                
                # Fill template
                if incident_type == "CPU":
                    log = template.format(
                        cpu=random.randint(70, 99),
                        service=random.choice(self.SERVICES)
                    )
                elif incident_type == "Memory":
                    log = template.format(
                        memory=random.randint(75, 98),
                        service=random.choice(self.SERVICES)
                    )
                elif incident_type == "Error":
                    log = template.format(
                        service=random.choice(self.SERVICES),
                        error_rate=random.randint(5, 50)
                    )
                elif incident_type == "Latency":
                    log = template.format(
                        service=random.choice(self.SERVICES),
                        latency=random.randint(500, 5000)
                    )
                else:  # Dependency
                    log = template.format(
                        dep=random.choice(self.DEPENDENCIES),
                        service=random.choice(self.SERVICES)
                    )
                
                logs.append(log)
                incident_ids.append(incident_id)
        
        return logs, incident_ids


def train_embeddings(
    output_dir: str,
    num_incidents: int = 100,
    logs_per_incident: int = 10,
    num_epochs: int = 3,
    batch_size: int = 32
):
    """Train embeddings."""
    logger.info(f"Generating training data: {num_incidents} incidents...")
    
    generator = LogDataGenerator()
    logs, incident_ids = generator.generate_incident_logs(
        num_incidents=num_incidents,
        logs_per_incident=logs_per_incident
    )
    
    logger.info(f"Generated {len(logs)} logs from {num_incidents} incidents")
    
    # Create trainer
    logger.info("Initializing SimCSE trainer...")
    try:
        trainer = SimCSETrainer()
    except Exception as e:
        logger.error(f"Failed to initialize trainer: {e}")
        return
    
    # Train
    logger.info("Starting fine-tuning...")
    try:
        metrics = trainer.train(
            logs=logs,
            incident_ids=incident_ids,
            num_epochs=num_epochs,
            batch_size=batch_size,
            warmup_steps=100
        )
        
        logger.info(f"Training complete. Metrics: {metrics}")
    except Exception as e:
        logger.error(f"Training failed: {e}")
        logger.info("Continuing with base model...")
    
    # Save embedder
    logger.info(f"Saving fine-tuned model to {output_dir}...")
    try:
        trainer.save(output_dir)
    except Exception as e:
        logger.error(f"Failed to save model: {e}")
    
    # Test embedder
    logger.info("Testing embedder...")
    try:
        embedder = SimCSEEmbedder()
        
        test_logs = [
            "CPU utilization at 95% on api-gateway",
            "Memory usage: 88% for user-service",
            "Database connection timeout"
        ]
        
        embeddings = embedder.encode(test_logs)
        logger.info(f"Generated embeddings shape: {embeddings.shape}")
        
        # Test similarity
        similarities = embedder.get_similarity(embeddings, embeddings)
        logger.info(f"Similarity matrix shape: {similarities.shape}")
        logger.info(f"Diagonal (self-similarity): {np.diag(similarities)}")
    
    except Exception as e:
        logger.error(f"Testing failed: {e}")
    
    # Save summary
    summary = {
        "timestamp": datetime.now().isoformat(),
        "output_directory": output_dir,
        "training_data": {
            "num_incidents": num_incidents,
            "logs_per_incident": logs_per_incident,
            "total_logs": len(logs)
        },
        "training_params": {
            "num_epochs": num_epochs,
            "batch_size": batch_size
        }
    }
    
    summary_path = Path(output_dir) / "training_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"Summary saved to {summary_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fine-tune embeddings with SimCSE"
    )
    parser.add_argument(
        "--output_dir",
        default="./models/embeddings_finetuned",
        help="Output directory"
    )
    parser.add_argument(
        "--num_incidents",
        type=int,
        default=100,
        help="Number of incidents"
    )
    parser.add_argument(
        "--logs_per_incident",
        type=int,
        default=10,
        help="Logs per incident"
    )
    parser.add_argument(
        "--num_epochs",
        type=int,
        default=3,
        help="Training epochs"
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=32,
        help="Batch size"
    )
    
    args = parser.parse_args()
    
    train_embeddings(
        output_dir=args.output_dir,
        num_incidents=args.num_incidents,
        logs_per_incident=args.logs_per_incident,
        num_epochs=args.num_epochs,
        batch_size=args.batch_size
    )


if __name__ == "__main__":
    main()
