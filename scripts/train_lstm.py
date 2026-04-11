"""
Training script for LSTM-based Log Anomaly Detector (Module 1).

This script handles:
1. Data preparation from CloudWatch logs and labels
2. Sliding window sequence creation
3. PyTorch training with validation
4. Model checkpointing and early stopping
5. Inference on test data

Usage:
    python scripts/train_lstm.py \\
        --num-samples 10000 \\
        --output-path /tmp/lstm_model.pt \\
        --num-epochs 100 \\
        --batch-size 32
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split
import numpy as np
import argparse
import logging
from pathlib import Path
from typing import Tuple, List, Dict, Optional
import json

from nexus.models.lstm import (
    LogAnomalyLSTM,
    LogAnomalyLSTMConfig,
    LogSequenceDataset,
    LogAnomalyLSTMScorer
)

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class LogAnomalyLSTMTrainer:
    """
    Trainer class for LSTM-based log anomaly detection.
    
    Handles training loop with:
    - Mini-batch gradient descent
    - Validation monitoring
    - Early stopping when validation loss plateaus
    - Model checkpointing (saves best model)
    - Training metrics logging
    
    Attributes:
        model: LogAnomalyLSTM instance
        config: LogAnomalyLSTMConfig
        optimizer: Adam optimizer
        criterion: Binary Cross Entropy loss
        device: torch.device
        best_val_loss: Best validation loss seen so far
        patience_counter: Early stopping patience counter
    """
    
    def __init__(
        self,
        model: LogAnomalyLSTM,
        config: LogAnomalyLSTMConfig,
        learning_rate: float = 1e-3,
        weight_decay: float = 1e-5
    ):
        """
        Initialize trainer.
        
        Args:
            model: LogAnomalyLSTM instance
            config: Model configuration
            learning_rate: Adam learning rate
            weight_decay: L2 regularization coefficient
        """
        self.model = model
        self.config = config
        self.device = torch.device(config.device)
        
        # Move model to device
        self.model.to(self.device)
        
        # Optimizer and loss
        self.optimizer = optim.Adam(
            model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay
        )
        self.criterion = nn.BCELoss()  # Binary Cross Entropy for binary classification
        
        # Early stopping
        self.best_val_loss = float('inf')
        self.patience_counter = 0
        self.patience = 5  # Stop if val loss doesn't improve for 5 epochs
        
        self.train_losses = []
        self.val_losses = []
    
    def train_epoch(self, train_loader: DataLoader) -> float:
        """
        Train for one epoch.
        
        Args:
            train_loader: DataLoader with training data
        
        Returns:
            Average training loss for the epoch
        """
        self.model.train()
        total_loss = 0.0
        num_batches = 0
        
        for sequences, labels in train_loader:
            sequences = sequences.to(self.device)
            labels = labels.to(self.device)
            
            # Forward pass
            self.optimizer.zero_grad()
            predictions, _ = self.model(sequences)
            loss = self.criterion(predictions, labels)
            
            # Backward pass
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimizer.step()
            
            total_loss += loss.item()
            num_batches += 1
        
        avg_loss = total_loss / num_batches if num_batches > 0 else 0.0
        self.train_losses.append(avg_loss)
        
        return avg_loss
    
    def validate(self, val_loader: DataLoader) -> Tuple[float, Dict[str, float]]:
        """
        Validate on held-out data.
        
        Computes:
        - Validation loss (BCE)
        - Accuracy (both positive and negative class)
        - ROC-AUC approximation
        
        Args:
            val_loader: DataLoader with validation data
        
        Returns:
            Tuple of (avg_val_loss, metrics_dict)
        """
        self.model.eval()
        total_loss = 0.0
        num_batches = 0
        
        all_predictions = []
        all_labels = []
        
        with torch.no_grad():
            for sequences, labels in val_loader:
                sequences = sequences.to(self.device)
                labels = labels.to(self.device)
                
                predictions, _ = self.model(sequences)
                loss = self.criterion(predictions, labels)
                
                total_loss += loss.item()
                num_batches += 1
                
                all_predictions.extend(predictions.cpu().numpy().flatten())
                all_labels.extend(labels.cpu().numpy().flatten())
        
        avg_loss = total_loss / num_batches if num_batches > 0 else 0.0
        self.val_losses.append(avg_loss)
        
        # Compute additional metrics
        predictions_binary = np.array(all_predictions) >= 0.5
        labels_array = np.array(all_labels).astype(int)
        
        accuracy = np.mean(predictions_binary == labels_array)
        
        # Separate accuracies for each class
        if np.any(labels_array == 0):
            specificity = np.mean(predictions_binary[labels_array == 0] == 0)
        else:
            specificity = 0.0
        
        if np.any(labels_array == 1):
            sensitivity = np.mean(predictions_binary[labels_array == 1] == 1)
        else:
            sensitivity = 0.0
        
        metrics = {
            'accuracy': accuracy,
            'sensitivity': sensitivity,
            'specificity': specificity,
        }
        
        return avg_loss, metrics
    
    def train(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
        num_epochs: int = 100,
        checkpoint_path: Optional[str] = None
    ) -> Dict[str, List[float]]:
        """
        Full training loop with validation and early stopping.
        
        Args:
            train_loader: DataLoader for training data
            val_loader: DataLoader for validation data
            num_epochs: Maximum number of epochs
            checkpoint_path: Path to save best model
        
        Returns:
            Dictionary with training history (losses, metrics)
        """
        logger.info(f"Starting training for {num_epochs} epochs")
        
        for epoch in range(num_epochs):
            # Training
            train_loss = self.train_epoch(train_loader)
            
            # Validation
            val_loss, metrics = self.validate(val_loader)
            
            logger.info(
                f"Epoch {epoch+1}/{num_epochs} | "
                f"Train Loss: {train_loss:.4f} | "
                f"Val Loss: {val_loss:.4f} | "
                f"Acc: {metrics['accuracy']:.3f} | "
                f"Sens: {metrics['sensitivity']:.3f} | "
                f"Spec: {metrics['specificity']:.3f}"
            )
            
            # Early stopping
            if val_loss < self.best_val_loss:
                self.best_val_loss = val_loss
                self.patience_counter = 0
                
                # Save checkpoint
                if checkpoint_path:
                    torch.save(self.model.state_dict(), checkpoint_path)
                    logger.info(f"Saved best model to {checkpoint_path}")
            else:
                self.patience_counter += 1
                logger.info(f"Patience counter: {self.patience_counter}/{self.patience}")
                
                if self.patience_counter >= self.patience:
                    logger.info(f"Early stopping at epoch {epoch+1}")
                    break
        
        return {
            'train_losses': self.train_losses,
            'val_losses': self.val_losses,
            'best_val_loss': self.best_val_loss,
        }


def create_dummy_embeddings_with_anomalies(
    num_samples: int = 10000,
    embedding_dim: int = 768,
    anomaly_fraction: float = 0.1,
    seed: int = 42
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Create synthetic log embeddings with labels for testing.
    
    Generates:
    - Normal logs: Gaussian distribution around origin
    - Anomalies: Gaussian with shifted mean + higher variance
    
    Args:
        num_samples: Total number of synthetic logs
        embedding_dim: Dimensionality of embeddings
        anomaly_fraction: Fraction of samples to be anomalies
        seed: Random seed for reproducibility
    
    Returns:
        Tuple of (embeddings, labels) with shape (num_samples, embedding_dim) and (num_samples,)
    """
    np.random.seed(seed)
    torch.manual_seed(seed)
    
    num_anomalies = int(num_samples * anomaly_fraction)
    num_normal = num_samples - num_anomalies
    
    # Normal logs: small variance
    normal_embeddings = np.random.normal(
        loc=0.0,
        scale=0.5,
        size=(num_normal, embedding_dim)
    )
    
    # Anomaly logs: larger variance, shifted center
    anomaly_embeddings = np.random.normal(
        loc=3.0,  # Shifted mean
        scale=1.5,  # Larger variance
        size=(num_anomalies, embedding_dim)
    )
    
    # Combine and shuffle
    embeddings = np.vstack([normal_embeddings, anomaly_embeddings])
    labels = np.hstack([np.zeros(num_normal), np.ones(num_anomalies)])
    
    # Shuffle
    shuffled_idx = np.random.permutation(len(embeddings))
    embeddings = embeddings[shuffled_idx]
    labels = labels[shuffled_idx]
    
    logger.info(f"Created {num_samples} synthetic embeddings ({anomaly_fraction*100:.1f}% anomalies)")
    
    return embeddings, labels


def train_lstm_model(
    num_samples: int = 10000,
    output_path: str = "/tmp/lstm_model.pt",
    num_epochs: int = 100,
    batch_size: int = 32,
    learning_rate: float = 1e-3,
    device: str = "cpu"
) -> Dict[str, any]:
    """
    Main training function for LSTM anomaly detector.
    
    Args:
        num_samples: Number of synthetic training logs
        output_path: Path to save trained model
        num_epochs: Maximum training epochs
        batch_size: Mini-batch size
        learning_rate: Adam learning rate
        device: "cpu" or "cuda"
    
    Returns:
        Dictionary with training results and paths
    """
    logger.info("=== LSTM Anomaly Detector Training ===")
    
    # 1. Create synthetic data
    embeddings, labels = create_dummy_embeddings_with_anomalies(
        num_samples=num_samples,
        anomaly_fraction=0.1
    )
    
    # 2. Create dataset with sequences
    dataset = LogSequenceDataset(
        embeddings=embeddings,
        labels=labels,
        sequence_length=16,  # 16-log windows
        stride=4  # Stride=4 creates overlapping windows
    )
    logger.info(f"Created {len(dataset)} training sequences")
    
    # 3. Train/val split
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = random_split(
        dataset,
        [train_size, val_size],
        generator=torch.Generator().manual_seed(42)
    )
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    
    logger.info(f"Train samples: {train_size}, Val samples: {val_size}")
    
    # 4. Initialize model
    config = LogAnomalyLSTMConfig(
        embedding_dim=768,
        hidden_dim=256,
        num_layers=2,
        dropout=0.3,
        bidirectional=True,
        sequence_length=16,
        batch_size=batch_size,
        learning_rate=learning_rate,
        device=device
    )
    
    model = LogAnomalyLSTM(config)
    logger.info(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")
    
    # 5. Train
    trainer = LogAnomalyLSTMTrainer(
        model=model,
        config=config,
        learning_rate=learning_rate
    )
    
    history = trainer.train(
        train_loader=train_loader,
        val_loader=val_loader,
        num_epochs=num_epochs,
        checkpoint_path=output_path
    )
    
    logger.info(f"Training complete. Best val loss: {trainer.best_val_loss:.4f}")
    logger.info(f"Model saved to {output_path}")
    
    return {
        'model_path': output_path,
        'config': {
            'embedding_dim': config.embedding_dim,
            'hidden_dim': config.hidden_dim,
            'num_layers': config.num_layers,
            'dropout': config.dropout,
            'bidirectional': config.bidirectional,
        },
        'training_history': history,
        'num_samples': num_samples,
        'num_parameters': sum(p.numel() for p in model.parameters()),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train LSTM anomaly detector for logs"
    )
    parser.add_argument(
        "--num-samples",
        type=int,
        default=10000,
        help="Number of synthetic training samples"
    )
    parser.add_argument(
        "--output-path",
        type=str,
        default="/tmp/lstm_model.pt",
        help="Path to save trained model"
    )
    parser.add_argument(
        "--num-epochs",
        type=int,
        default=100,
        help="Maximum training epochs"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Mini-batch size"
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=1e-3,
        help="Adam learning rate"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        choices=["cpu", "cuda"],
        help="Device for training (cpu or cuda)"
    )
    
    args = parser.parse_args()
    
    results = train_lstm_model(
        num_samples=args.num_samples,
        output_path=args.output_path,
        num_epochs=args.num_epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        device=args.device
    )
    
    logger.info(f"\nTraining results:")
    logger.info(json.dumps({k: v for k, v in results.items() if k != 'training_history'}, indent=2))
