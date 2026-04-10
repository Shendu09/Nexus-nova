"""
Training script for LogAutoencoder model.

This script trains the autoencoder on "normal" log embeddings
from a baseline period. The resulting model learns to reconstruct
normal logs and flag anomalies by high reconstruction error.

Usage:
    python scripts/train_autoencoder.py \
        --data-source dynamodb \
        --log-group /aws/lambda/my-app \
        --baseline-days 7 \
        --output-path s3://my-bucket/models/autoencoder.pt
"""

import argparse
import json
import logging
import torch
import torch.nn as nn
from torch.optim import Adam
from torch.utils.data import DataLoader, TensorDataset
from typing import Tuple, List
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from nexus.models.autoencoder import LogAutoencoder, AutoencoderScorerConfig

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class AutoencoderTrainer:
    """Trainer class for autoencoder models."""
    
    def __init__(
        self,
        model: LogAutoencoder,
        config: AutoencoderScorerConfig,
        device: torch.device = None
    ):
        """
        Initialize trainer.
        
        Args:
            model: LogAutoencoder instance
            config: AutoencoderScorerConfig
            device: torch.device
        """
        self.model = model
        self.config = config
        self.device = device or torch.device("cpu")
        self.optimizer = Adam(model.parameters(), lr=config.learning_rate)
        self.criterion = nn.MSELoss()
        self.history = {"train_loss": [], "val_loss": []}
    
    def train_epoch(self, train_loader: DataLoader) -> float:
        """
        Train for one epoch.
        
        Args:
            train_loader: DataLoader for training data
            
        Returns:
            Average training loss
        """
        self.model.train()
        total_loss = 0.0
        n_batches = 0
        
        for batch_x in train_loader:
            batch_x = batch_x[0].to(self.device)
            
            self.optimizer.zero_grad()
            reconstructed, _ = self.model(batch_x)
            loss = self.criterion(reconstructed, batch_x)
            
            loss.backward()
            self.optimizer.step()
            
            total_loss += loss.item()
            n_batches += 1
        
        avg_loss = total_loss / n_batches
        return avg_loss
    
    def validate(self, val_loader: DataLoader) -> float:
        """
        Validate model on validation set.
        
        Args:
            val_loader: DataLoader for validation data
            
        Returns:
            Average validation loss
        """
        self.model.eval()
        total_loss = 0.0
        n_batches = 0
        
        with torch.no_grad():
            for batch_x in val_loader:
                batch_x = batch_x[0].to(self.device)
                reconstructed, _ = self.model(batch_x)
                loss = self.criterion(reconstructed, batch_x)
                
                total_loss += loss.item()
                n_batches += 1
        
        avg_loss = total_loss / n_batches
        return avg_loss
    
    def train(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader
    ) -> dict:
        """
        Train model for multiple epochs.
        
        Args:
            train_loader: Training data loader
            val_loader: Validation data loader
            
        Returns:
            Training history dict
        """
        best_val_loss = float('inf')
        best_model_state = None
        
        for epoch in range(self.config.num_epochs):
            train_loss = self.train_epoch(train_loader)
            val_loss = self.validate(val_loader)
            
            self.history["train_loss"].append(train_loss)
            self.history["val_loss"].append(val_loss)
            
            if (epoch + 1) % 5 == 0:
                logger.info(
                    f"Epoch {epoch+1}/{self.config.num_epochs} | "
                    f"Train Loss: {train_loss:.6f} | Val Loss: {val_loss:.6f}"
                )
            
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_model_state = self.model.state_dict().copy()
        
        if best_model_state:
            self.model.load_state_dict(best_model_state)
            logger.info(f"Loaded best model with val_loss: {best_val_loss:.6f}")
        
        return self.history


def create_dummy_embeddings(n_samples: int = 10000) -> np.ndarray:
    """
    Create dummy embeddings for demonstration.
    (In production, these come from CloudWatch logs + Nova Embeddings API)
    
    Args:
        n_samples: Number of embeddings to create
        
    Returns:
        Array of shape (n_samples, 768)
    """
    # Simulate normal log embeddings
    embeddings = np.random.normal(0, 0.1, (n_samples, 768)).astype(np.float32)
    return embeddings


def train_autoencoder(
    n_samples: int = 10000,
    output_path: str = "/tmp/autoencoder.pt",
    batch_size: int = 128,
    num_epochs: int = 50
):
    """
    Main training function.
    
    Args:
        n_samples: Number of training samples
        output_path: Where to save the trained model
        batch_size: Training batch size
        num_epochs: Number of epochs to train
    """
    logger.info("="*60)
    logger.info("LogAutoencoder Training")
    logger.info("="*60)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")
    
    # Create dummy training data
    logger.info(f"Generating {n_samples} dummy embeddings...")
    embeddings = create_dummy_embeddings(n_samples)
    embeddings_tensor = torch.from_numpy(embeddings).float()
    
    # Create config and model
    config = AutoencoderScorerConfig(
        batch_size=batch_size,
        num_epochs=num_epochs,
        device=device
    )
    model = LogAutoencoder(device=device)
    
    # Create train/val split
    n_train = int(n_samples * (1 - config.validation_split))
    train_data = embeddings_tensor[:n_train]
    val_data = embeddings_tensor[n_train:]
    
    train_dataset = TensorDataset(train_data)
    val_dataset = TensorDataset(val_data)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    
    # Train
    trainer = AutoencoderTrainer(model, config, device)
    history = trainer.train(train_loader, val_loader)
    
    # Save model
    torch.save(model.state_dict(), output_path)
    logger.info(f"Model saved to {output_path}")
    
    # Log final losses
    logger.info(f"Final Train Loss: {history['train_loss'][-1]:.6f}")
    logger.info(f"Final Val Loss: {history['val_loss'][-1]:.6f}")
    
    return model, history


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train LogAutoencoder on log embeddings"
    )
    parser.add_argument(
        "--n-samples",
        type=int,
        default=10000,
        help="Number of training samples"
    )
    parser.add_argument(
        "--output-path",
        type=str,
        default="/tmp/autoencoder.pt",
        help="Path to save trained model"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=128,
        help="Training batch size"
    )
    parser.add_argument(
        "--num-epochs",
        type=int,
        default=50,
        help="Number of training epochs"
    )
    
    args = parser.parse_args()
    
    model, history = train_autoencoder(
        n_samples=args.n_samples,
        output_path=args.output_path,
        batch_size=args.batch_size,
        num_epochs=args.num_epochs
    )
    
    logger.info("Training complete!")
