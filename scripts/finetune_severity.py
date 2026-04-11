"""
Training script for BERT-based severity classifier.

This script fine-tunes a pre-trained BERT model on log severity labels.
Training data can be extracted from DynamoDB historical triage reports.

Usage:
    python scripts/finetune_severity.py \
        --output_dir ./models/severity_classifier \
        --num_epochs 5 \
        --batch_size 16 \
        --learning_rate 2e-5

AWS Requirements:
    - DynamoDB table: nexus-triage (with historical records)
    - IAM permissions: dynamodb:Scan, dynamodb:GetItem
"""

import torch
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader, random_split
from transformers import AutoTokenizer, AutoModelForSequenceClassification, AdamW
from typing import List, Tuple, Dict, Optional
import numpy as np
import json
import logging
import argparse
from pathlib import Path
import sys

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SeverityDataset(Dataset):
    """PyTorch dataset for severity classification."""
    
    LABELS = ["INFO", "WARNING", "HIGH", "CRITICAL"]
    LABEL_TO_ID = {label: idx for idx, label in enumerate(LABELS)}
    
    def __init__(
        self,
        texts: List[str],
        labels: List[str],
        tokenizer,
        max_length: int = 512
    ):
        """Initialize dataset."""
        self.texts = texts
        self.label_ids = [self.LABEL_TO_ID[label] for label in labels]
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self) -> int:
        return len(self.texts)
    
    def __getitem__(self, idx: int) -> Dict:
        """Return tokenized text and label ID."""
        text = self.texts[idx]
        label_id = self.label_ids[idx]
        
        encoding = self.tokenizer(
            text,
            max_length=self.max_length,
            truncation=True,
            padding="max_length",
            return_tensors="pt"
        )
        
        return {
            "input_ids": encoding["input_ids"][0],
            "attention_mask": encoding["attention_mask"][0],
            "label": torch.tensor(label_id, dtype=torch.long)
        }


class SeverityClassifierTrainerTask:
    """Trainer for severity classifier."""
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        num_labels: int = 4,
        learning_rate: float = 2e-5,
        batch_size: int = 16,
        num_epochs: int = 5,
        device: Optional[torch.device] = None
    ):
        """Initialize trainer."""
        self.device = device or torch.device("cpu")
        self.model_name = model_name
        self.num_labels = num_labels
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.num_epochs = num_epochs
        
        # Load model and tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_name,
            num_labels=num_labels
        ).to(self.device)
    
    def train_epoch(
        self,
        train_loader: DataLoader,
        criterion
    ) -> float:
        """Train for one epoch."""
        self.model.train()
        total_loss = 0.0
        num_batches = 0
        
        for batch in train_loader:
            # Move to device
            input_ids = batch["input_ids"].to(self.device)
            attention_mask = batch["attention_mask"].to(self.device)
            labels = batch["label"].to(self.device)
            
            # Forward pass
            outputs = self.model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels
            )
            loss = outputs.loss
            
            # Backward pass
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
            
            total_loss += loss.item()
            num_batches += 1
        
        return total_loss / num_batches
    
    def evaluate(self, val_loader: DataLoader) -> Tuple[float, float]:
        """Evaluate on validation set."""
        self.model.eval()
        total_loss = 0.0
        correct = 0
        total = 0
        
        with torch.no_grad():
            for batch in val_loader:
                input_ids = batch["input_ids"].to(self.device)
                attention_mask = batch["attention_mask"].to(self.device)
                labels = batch["label"].to(self.device)
                
                outputs = self.model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels
                )
                
                loss = outputs.loss
                logits = outputs.logits
                
                total_loss += loss.item()
                predictions = torch.argmax(logits, dim=1)
                correct += (predictions == labels).sum().item()
                total += labels.size(0)
        
        avg_loss = total_loss / len(val_loader)
        accuracy = correct / total
        
        return avg_loss, accuracy
    
    def train(
        self,
        train_texts: List[str],
        train_labels: List[str],
        val_texts: Optional[List[str]] = None,
        val_labels: Optional[List[str]] = None,
    ) -> Dict[str, List[float]]:
        """
        Train severity classifier.
        
        Args:
            train_texts: List of training texts
            train_labels: List of training labels
            val_texts: Optional validation texts (if None, split from training)
            val_labels: Optional validation labels
            
        Returns:
            Dict with training history
        """
        # Create datasets
        full_dataset = SeverityDataset(
            train_texts,
            train_labels,
            self.tokenizer
        )
        
        if val_texts is None:
            # Split training data
            val_size = int(len(full_dataset) * 0.2)
            train_size = len(full_dataset) - val_size
            train_dataset, val_dataset = random_split(
                full_dataset,
                [train_size, val_size]
            )
        else:
            train_dataset = full_dataset
            val_dataset = SeverityDataset(
                val_texts,
                val_labels,
                self.tokenizer
            )
        
        # Create dataloaders
        train_loader = DataLoader(
            train_dataset,
            batch_size=self.batch_size,
            shuffle=True
        )
        val_loader = DataLoader(
            val_dataset,
            batch_size=self.batch_size,
            shuffle=False
        )
        
        # Setup optimizer
        self.optimizer = AdamW(
            self.model.parameters(),
            lr=self.learning_rate
        )
        
        # Training loop
        history = {
            "train_loss": [],
            "val_loss": [],
            "val_accuracy": []
        }
        
        for epoch in range(self.num_epochs):
            train_loss = self.train_epoch(train_loader, None)
            val_loss, val_accuracy = self.evaluate(val_loader)
            
            history["train_loss"].append(train_loss)
            history["val_loss"].append(val_loss)
            history["val_accuracy"].append(val_accuracy)
            
            logger.info(
                f"Epoch {epoch + 1}/{self.num_epochs} - "
                f"Train Loss: {train_loss:.4f}, "
                f"Val Loss: {val_loss:.4f}, "
                f"Val Accuracy: {val_accuracy:.4f}"
            )
        
        return history
    
    def save(self, save_path: str):
        """Save model and tokenizer."""
        Path(save_path).mkdir(parents=True, exist_ok=True)
        self.model.save_pretrained(save_path)
        self.tokenizer.save_pretrained(save_path)
        logger.info(f"Model saved to {save_path}")


def create_dummy_training_data() -> Tuple[List[str], List[str]]:
    """
    Create dummy training data for demonstration.
    
    In production, this would be extracted from DynamoDB historical
    triage reports using extract_training_data.py.
    
    Returns:
        Tuples of (texts, labels)
    """
    data = [
        # INFO examples
        ("Application startup successful. All services initialized.", "INFO"),
        ("Connection pooling enabled with 10 connections.", "INFO"),
        ("Cache hit rate: 95%. Performance optimal.", "INFO"),
        ("Regular maintenance task completed.", "INFO"),
        
        # WARNING examples
        ("Response time increased by 20%. Investigate further.", "WARNING"),
        ("Memory usage at 75%. Monitor closely.", "WARNING"),
        ("Database query execution time slower than baseline.", "WARNING"),
        ("Retry attempt 2 of 5 for failed request.", "WARNING"),
        
        # HIGH examples
        ("Database connection timeout after 30s. Service degrading.", "HIGH"),
        ("Error rate spike: 5% of requests failing. Investigate urgently.", "HIGH"),
        ("Critical resource exhaustion detected. Immediate action needed.", "HIGH"),
        ("Multiple service failures cascading to dependent services.", "HIGH"),
        
        # CRITICAL examples
        ("FATAL: CPU usage at 98%. System unresponsive.", "CRITICAL"),
        ("CRITICAL: Unrecoverable database corruption detected.", "CRITICAL"),
        ("Emergency: Data loss detected. Failing over immediately.", "CRITICAL"),
        ("SEVERE: Security breach detected. Lockdown protocol activated.", "CRITICAL"),
    ]
    
    texts, labels = zip(*data)
    return list(texts), list(labels)


def main():
    """Main training entry point."""
    parser = argparse.ArgumentParser(
        description="Fine-tune BERT for log severity classification"
    )
    parser.add_argument(
        "--model_name",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="Pre-trained model name"
    )
    parser.add_argument(
        "--output_dir",
        default="./models/severity_classifier",
        help="Output directory for trained model"
    )
    parser.add_argument(
        "--num_epochs",
        type=int,
        default=5,
        help="Number of training epochs"
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=16,
        help="Batch size"
    )
    parser.add_argument(
        "--learning_rate",
        type=float,
        default=2e-5,
        help="Learning rate"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed"
    )
    
    args = parser.parse_args()
    
    # Set random seed
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    
    # Setup device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")
    
    # Create trainer
    trainer = SeverityClassifierTrainerTask(
        model_name=args.model_name,
        learning_rate=args.learning_rate,
        batch_size=args.batch_size,
        num_epochs=args.num_epochs,
        device=device
    )
    
    # Create dummy training data
    logger.info("Creating dummy training data...")
    texts, labels = create_dummy_training_data()
    logger.info(f"Training samples: {len(texts)}")
    
    # Train model
    logger.info(f"Training on {device}...")
    history = trainer.train(texts, labels)
    
    # Save model
    trainer.save(args.output_dir)
    
    # Save training history
    history_path = Path(args.output_dir) / "training_history.json"
    with open(history_path, "w") as f:
        json.dump(history, f, indent=2)
    logger.info(f"Training history saved to {history_path}")
    
    # Print summary
    final_accuracy = history["val_accuracy"][-1]
    logger.info(f"Training complete. Final validation accuracy: {final_accuracy:.4f}")


if __name__ == "__main__":
    main()
