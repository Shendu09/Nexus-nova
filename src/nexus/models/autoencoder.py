"""
Autoencoder-Based Log Anomaly Detection

This module implements an unsupervised anomaly detection model using autoencoder
neural networks. It learns the distribution of normal log embeddings and flags
logs with high reconstruction error as anomalous.

Architecture:
    Encoder: 768 → 256 → 64 (ReLU)
    Bottleneck: 64-dim latent space
    Decoder: 64 → 256 → 768 (ReLU + Linear)
    Loss: Mean Squared Error (MSE)
"""

import torch
import torch.nn as nn
from typing import Tuple, Optional
import numpy as np


class LogAutoencoder(nn.Module):
    """
    Autoencoder for detecting anomalies in log embeddings.
    
    Learns to reconstruct normal log embeddings. Logs with high 
    reconstruction error are flagged as anomalous.
    
    Attributes:
        encoder (nn.Sequential): Encoding network
        decoder (nn.Sequential): Decoding network
        device (torch.device): CPU or CUDA device
    """
    
    def __init__(
        self,
        input_dim: int = 768,
        hidden_dim: int = 256,
        latent_dim: int = 64,
        device: Optional[torch.device] = None
    ):
        """
        Initialize the autoencoder architecture.
        
        Args:
            input_dim: Dimension of input embeddings (default: 768 for Nova Embeddings)
            hidden_dim: Dimension of hidden layer (default: 256)
            latent_dim: Dimension of bottleneck/latent space (default: 64)
            device: torch.device (CPU or CUDA)
        """
        super(LogAutoencoder, self).__init__()
        
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.latent_dim = latent_dim
        self.device = device or torch.device("cpu")
        
        # Encoder: 768 → 256 → 64
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, latent_dim),
            nn.ReLU()
        ).to(self.device)
        
        # Decoder: 64 → 256 → 768
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, input_dim)
        ).to(self.device)
        
        self.to(self.device)
    
    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """Encode input to latent space."""
        return self.encoder(x)
    
    def decode(self, z: torch.Tensor) -> torch.Tensor:
        """Decode latent representation back to input space."""
        return self.decoder(z)
    
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass through encoder and decoder.
        
        Args:
            x: Input tensor of shape (batch_size, input_dim)
            
        Returns:
            Tuple of (reconstructed_output, latent_representation)
        """
        z = self.encode(x)
        reconstructed = self.decode(z)
        return reconstructed, z
    
    def compute_reconstruction_error(
        self, 
        embeddings: torch.Tensor
    ) -> np.ndarray:
        """
        Compute reconstruction error (MSE) for each embedding.
        
        Args:
            embeddings: Tensor of shape (n_samples, input_dim)
            
        Returns:
            Array of reconstruction errors, shape (n_samples,)
        """
        self.eval()
        with torch.no_grad():
            embeddings = embeddings.to(self.device)
            reconstructed, _ = self.forward(embeddings)
            
            # Compute MSE per sample
            errors = torch.mean(
                (embeddings - reconstructed) ** 2,
                dim=1
            )
        
        return errors.cpu().numpy()
    
    def get_latent_representation(
        self,
        embeddings: torch.Tensor
    ) -> np.ndarray:
        """
        Get latent space representations for embeddings.
        
        Args:
            embeddings: Tensor of shape (n_samples, input_dim)
            
        Returns:
            Latent representations, shape (n_samples, latent_dim)
        """
        self.eval()
        with torch.no_grad():
            embeddings = embeddings.to(self.device)
            z = self.encode(embeddings)
        
        return z.cpu().numpy()


class AutoencoderScorerConfig:
    """Configuration for autoencoder-based anomaly scoring."""
    
    def __init__(
        self,
        input_dim: int = 768,
        hidden_dim: int = 256,
        latent_dim: int = 64,
        batch_size: int = 128,
        num_epochs: int = 50,
        learning_rate: float = 1e-3,
        validation_split: float = 0.2,
        std_multiplier: float = 3.0,
        device: Optional[torch.device] = None
    ):
        """
        Initialize configuration.
        
        Args:
            input_dim: Input embedding dimension
            hidden_dim: Hidden layer dimension
            latent_dim: Latent space dimension
            batch_size: Training batch size
            num_epochs: Number of training epochs
            learning_rate: Adam optimizer learning rate
            validation_split: Train/validation split ratio
            std_multiplier: Multiplier for standard deviation in threshold
            device: torch.device
        """
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.latent_dim = latent_dim
        self.batch_size = batch_size
        self.num_epochs = num_epochs
        self.learning_rate = learning_rate
        self.validation_split = validation_split
        self.std_multiplier = std_multiplier
        self.device = device or torch.device("cpu")


class AutoencoderScorer:
    """
    High-level anomaly scorer using trained autoencoder.
    
    This class wraps the trained model and provides methods for:
    - Computing anomaly scores
    - Threshold calculation
    - Identifying anomalous logs
    """
    
    def __init__(
        self,
        model: LogAutoencoder,
        threshold: Optional[float] = None
    ):
        """
        Initialize the scorer.
        
        Args:
            model: Trained LogAutoencoder instance
            threshold: Anomaly threshold (if None, will be computed from baseline)
        """
        self.model = model
        self.threshold = threshold
        self.baseline_mean: Optional[float] = None
        self.baseline_std: Optional[float] = None
    
    def calibrate_threshold(
        self,
        baseline_embeddings: torch.Tensor,
        std_multiplier: float = 3.0
    ) -> float:
        """
        Calibrate anomaly threshold based on baseline (normal) data.
        
        Args:
            baseline_embeddings: Tensor of normal log embeddings
            std_multiplier: Number of standard deviations above mean
            
        Returns:
            Computed threshold value
        """
        errors = self.model.compute_reconstruction_error(baseline_embeddings)
        
        self.baseline_mean = float(np.mean(errors))
        self.baseline_std = float(np.std(errors))
        
        self.threshold = self.baseline_mean + (std_multiplier * self.baseline_std)
        
        return self.threshold
    
    def score_logs(
        self,
        embeddings: torch.Tensor
    ) -> dict:
        """
        Score logs for anomalies.
        
        Args:
            embeddings: Tensor of log embeddings, shape (n_logs, 768)
            
        Returns:
            Dict containing:
                - scores: array of anomaly scores (reconstruction errors)
                - is_anomaly: boolean array
                - anomaly_indices: indices of anomalous logs
                - n_anomalies: count of anomalies
        """
        scores = self.model.compute_reconstruction_error(embeddings)
        
        is_anomaly = scores > (self.threshold or np.inf)
        anomaly_indices = np.where(is_anomaly)[0]
        
        return {
            "scores": scores,
            "is_anomaly": is_anomaly,
            "anomaly_indices": anomaly_indices.tolist(),
            "n_anomalies": int(np.sum(is_anomaly)),
            "threshold": self.threshold
        }
