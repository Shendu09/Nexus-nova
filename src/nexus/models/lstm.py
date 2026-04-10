"""
LSTM-based Log Anomaly Detector for Nexus Nova.

Module 1: Replaces Cordon's kNN anomaly scorer with a trained LSTM neural network
that understands sequential log patterns and detects anomalies in time-series data.

Architecture:
    - Input: Sequence of log embeddings (batch_size, seq_len, embedding_dim=768)
    - LSTM layers: Hidden dim 256, 2 layers, dropout 0.3
    - Output: Binary classification (normal vs anomaly) with sigmoid activation
    - Loss: Binary Cross Entropy (BCE)

Key Differences from Autoencoder (Module 2):
    - Supervised vs unsupervised (requires labeled data)
    - Time-series aware (learns patterns in sequential logs)
    - Better for drift detection (captures temporal dependencies)
    - Requires sequential context (16-log windows)
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from dataclasses import dataclass
from typing import Tuple, List, Optional, Dict, Any
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class LogAnomalyLSTMConfig:
    """Configuration for LSTM anomaly detector."""
    
    embedding_dim: int = 768  # Nova Embeddings output dimension
    hidden_dim: int = 256  # LSTM hidden dimension
    num_layers: int = 2  # Number of LSTM layers
    dropout: float = 0.3  # Dropout probability
    bidirectional: bool = True  # Use bidirectional LSTM
    sequence_length: int = 16  # Sliding window size
    batch_size: int = 32
    learning_rate: float = 1e-3
    weight_decay: float = 1e-5
    device: str = "cpu"  # "cpu" (Lambda) or "cuda" (training)
    output_dim: int = 1  # Binary classification (anomaly yes/no)
    

class LogAnomalyLSTM(nn.Module):
    """
    LSTM-based neural network for time-series log anomaly detection.
    
    Learns sequential patterns in normal logs and detects deviations.
    
    Architecture:
        Input (768) → LSTM (256, 2 layers, dropout=0.3) 
        → Dense (128) → Output (1, sigmoid)
    
    Attributes:
        embedding_dim: Input embedding dimension (Nova Embeddings)
        hidden_dim: LSTM hidden state dimension
        num_layers: Number of stacked LSTM layers
        dropout: Dropout probability
        bidirectional: Whether to use bidirectional LSTM
    
    Methods:
        forward: Execute forward pass (batch_size, seq_len, embedding_dim) → (batch_size, 1)
        encode_sequence: Get LSTM hidden state representation
        compute_anomaly_score: Get raw probability of anomaly
    """
    
    def __init__(self, config: LogAnomalyLSTMConfig):
        """
        Initialize LSTM anomaly detector.
        
        Args:
            config: LogAnomalyLSTMConfig with model hyperparameters
        """
        super().__init__()
        self.config = config
        self.device_str = config.device
        
        # LSTM layers
        self.lstm = nn.LSTM(
            input_size=config.embedding_dim,
            hidden_size=config.hidden_dim,
            num_layers=config.num_layers,
            dropout=config.dropout if config.num_layers > 1 else 0.0,
            bidirectional=config.bidirectional,
            batch_first=True
        )
        
        # Calculate size after LSTM
        lstm_output_dim = config.hidden_dim * (2 if config.bidirectional else 1)
        
        # Fully connected layers
        self.fc1 = nn.Linear(lstm_output_dim, 128)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(config.dropout)
        self.fc2 = nn.Linear(128, config.output_dim)
        self.sigmoid = nn.Sigmoid()
    
    def forward(
        self, 
        x: torch.Tensor, 
        h: Optional[Tuple[torch.Tensor, torch.Tensor]] = None
    ) -> Tuple[torch.Tensor, Tuple[torch.Tensor, torch.Tensor]]:
        """
        Forward pass through LSTM for anomaly scoring.
        
        Args:
            x: Input batch of log sequences (batch_size, seq_len, embedding_dim)
            h: Optional initial hidden state tuple (h_0, c_0)
        
        Returns:
            Tuple of:
                - anomaly_scores: Probability of anomaly per sequence (batch_size, 1)
                - (h_n, c_n): Final hidden and cell states from LSTM
        
        Raises:
            ValueError: If x has wrong shape
        """
        if len(x.shape) != 3:
            raise ValueError(
                f"Expected 3D input (batch_size, seq_len, embedding_dim), "
                f"got {x.shape}"
            )
        
        # LSTM forward pass
        # Output shape: (batch_size, seq_len, lstm_output_dim)
        lstm_out, (h_n, c_n) = self.lstm(x, h)
        
        # Take last timestep output
        # Shape: (batch_size, lstm_output_dim)
        last_out = lstm_out[:, -1, :]
        
        # Fully connected layers
        fc1_out = self.relu(self.fc1(last_out))  # (batch_size, 128)
        fc1_out = self.dropout(fc1_out)
        
        # Sigmoid output for binary classification
        anomaly_scores = self.sigmoid(self.fc2(fc1_out))  # (batch_size, 1)
        
        return anomaly_scores, (h_n, c_n)
    
    def encode_sequence(self, x: torch.Tensor) -> torch.Tensor:
        """
        Get latent representation of log sequence from LSTM.
        
        Useful for visualization, similarity search, or clustering.
        
        Args:
            x: Log sequence batch (batch_size, seq_len, embedding_dim)
        
        Returns:
            LSTM hidden state representation (batch_size, lstm_output_dim)
        """
        with torch.no_grad():
            lstm_out, _ = self.lstm(x)
            last_out = lstm_out[:, -1, :]
        return last_out
    
    def compute_anomaly_score(self, x: torch.Tensor) -> np.ndarray:
        """
        Compute anomaly score for batch of sequences.
        
        Args:
            x: Log sequence batch (batch_size, seq_len, embedding_dim)
        
        Returns:
            Anomaly scores as numpy array (batch_size,)
        """
        with torch.no_grad():
            scores, _ = self.forward(x)
        return scores.squeeze(-1).cpu().numpy()


class LogSequenceDataset(Dataset):
    """
    PyTorch Dataset for log sequences with labels.
    
    Transforms flat embeddings into overlapping sequences using sliding window.
    
    Attributes:
        sequences: Windowed log sequences (num_windows, seq_len, embedding_dim)
        labels: Binary labels (0=normal, 1=anomaly) (num_windows,)
    
    Example:
        embeddings: (1000, 768)  # 1000 logs, 768-dim embeddings
        dataset = LogSequenceDataset(embeddings, labels, seq_len=16, stride=4)
        # Creates ~250 windows of 16-log sequences
    """
    
    def __init__(
        self,
        embeddings: np.ndarray,
        labels: np.ndarray,
        sequence_length: int = 16,
        stride: int = 4
    ):
        """
        Create windowed dataset from flat embeddings.
        
        Args:
            embeddings: Array of shape (num_logs, embedding_dim)
            labels: Binary labels for each log (num_logs,)
            sequence_length: Number of logs per sequence window
            stride: Step size between windows (stride < seq_len for overlap)
        
        Attributes set:
            sequences: Windowed sequences (num_windows, seq_len, embedding_dim)
            labels: Labels per window (num_windows,)
        """
        self.sequences = []
        self.labels = []
        
        # Create sliding windows
        for i in range(0, len(embeddings) - sequence_length + 1, stride):
            window = embeddings[i:i + sequence_length]
            # Use majority vote for window label
            window_label = 1 if np.mean(labels[i:i + sequence_length]) > 0.5 else 0
            
            self.sequences.append(torch.FloatTensor(window))
            self.labels.append(torch.FloatTensor([float(window_label)]))
    
    def __len__(self) -> int:
        """Return number of sequences."""
        return len(self.sequences)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Get sequence and label by index.
        
        Returns:
            Tuple of (sequence tensor, label tensor)
        """
        return self.sequences[idx], self.labels[idx]


class LogAnomalyLSTMScorer:
    """
    High-level interface for LSTM-based log anomaly scoring.
    
    Wraps LogAnomalyLSTM for inference with threshold-based decision making.
    
    Attributes:
        model: LogAnomalyLSTM instance
        config: LogAnomalyLSTMConfig
        threshold: Anomaly probability threshold for decisions
        device: torch device (cpu/cuda)
    
    Methods:
        calibrate_threshold: Set anomaly threshold from baseline distribution
        score_sequence: Get anomaly probability for single sequence
        score_sequences_batch: Vectorized scoring for multiple sequences
        predict_anomaly: Binary decision with threshold
    """
    
    def __init__(
        self,
        model: LogAnomalyLSTM,
        threshold: float = 0.5,
        config: Optional[LogAnomalyLSTMConfig] = None
    ):
        """
        Initialize LSTM scorer.
        
        Args:
            model: Trained LogAnomalyLSTM instance
            threshold: Probability threshold for anomaly classification
            config: Config object (optional, defaults to model.config)
        """
        self.model = model
        self.config = config or model.config
        self.threshold = threshold
        self.device = torch.device(self.config.device)
        self.model.to(self.device)
        self.model.eval()
    
    def calibrate_threshold(
        self,
        baseline_embeddings: np.ndarray,
        baseline_labels: np.ndarray,
        percentile: float = 95.0
    ) -> float:
        """
        Calibrate anomaly threshold from baseline (normal) data.
        
        Sets threshold at specified percentile of normal log distribution.
        Default 95th percentile means ~5% false positive rate on normal logs.
        
        Args:
            baseline_embeddings: Normal log embeddings (num_logs, embedding_dim)
            baseline_labels: Known labels (0=normal, 1=anomaly)
            percentile: Threshold percentile (default 95 for 5% FPR)
        
        Returns:
            Calibrated threshold value
        
        Note:
            Baseline should come from a known-healthy period without alarms.
        """
        # Create sequences from baseline
        dataset = LogSequenceDataset(
            baseline_embeddings,
            baseline_labels,
            sequence_length=self.config.sequence_length
        )
        loader = DataLoader(dataset, batch_size=self.config.batch_size, shuffle=False)
        
        # Score all baseline sequences
        all_scores = []
        with torch.no_grad():
            for sequences, _ in loader:
                sequences = sequences.to(self.device)
                scores = self.model.compute_anomaly_score(sequences)
                all_scores.extend(scores)
        
        # Compute percentile across normal logs only
        normal_scores = [
            all_scores[i] for i in range(len(all_scores))
            if dataset.labels[i].item() == 0.0
        ]
        
        if not normal_scores:
            logger.warning("No normal sequences found in baseline; using default threshold")
            self.threshold = 0.5
        else:
            self.threshold = float(np.percentile(normal_scores, percentile))
        
        logger.info(f"Calibrated LSTM threshold: {self.threshold:.4f} at {percentile}th percentile")
        return self.threshold
    
    def score_sequence(self, embedding: np.ndarray) -> float:
        """
        Score a single log sequence.
        
        Args:
            embedding: Single log embedding or sequence (embedding_dim,) or (seq_len, embedding_dim)
        
        Returns:
            Anomaly probability in [0, 1]
        """
        # Ensure 3D batch shape
        if embedding.ndim == 1:
            # Single embedding, need to tile into sequence
            embedding = np.tile(embedding, (self.config.sequence_length, 1))
        
        if embedding.ndim == 2:
            embedding = np.expand_dims(embedding, 0)
        
        tensor = torch.FloatTensor(embedding).to(self.device)
        return self.model.compute_anomaly_score(tensor)[0]
    
    def score_sequences_batch(
        self,
        embeddings: np.ndarray,
        sequence_length: Optional[int] = None
    ) -> np.ndarray:
        """
        Score batch of log sequences efficiently.
        
        Args:
            embeddings: Batch of embeddings (batch_size, embedding_dim) or
                       (batch_size, seq_len, embedding_dim)
            sequence_length: Optional sequence length for windowing
        
        Returns:
            Anomaly scores array (batch_size,)
        """
        if embeddings.ndim == 2:
            # Single embeddings, create sequences by padding/repeating
            batch_size = embeddings.shape[0]
            seq_len = sequence_length or self.config.sequence_length
            
            # Create sequences by repeating each embedding
            sequences = []
            for emb in embeddings:
                seq = np.tile(emb, (seq_len, 1))
                sequences.append(seq)
            embeddings = np.array(sequences)
        
        tensor = torch.FloatTensor(embeddings).to(self.device)
        return self.model.compute_anomaly_score(tensor)
    
    def predict_anomaly(
        self,
        embeddings: np.ndarray,
        return_scores: bool = False
    ) -> Dict[str, Any]:
        """
        Binary classification decision with threshold.
        
        Args:
            embeddings: Log embeddings
            return_scores: Whether to return raw scores
        
        Returns:
            Dictionary with:
                - 'predictions': Binary predictions (0/1)
                - 'scores': Raw anomaly probabilities (optional)
                - 'threshold': Decision threshold used
        """
        scores = self.score_sequences_batch(embeddings)
        predictions = (scores >= self.threshold).astype(int)
        
        result = {
            'predictions': predictions,
            'threshold': self.threshold
        }
        
        if return_scores:
            result['scores'] = scores
        
        return result
