"""
BERT-based Log Severity Classification

This module fine-tunes a BERT model to classify log triage severity as:
INFO, WARNING, HIGH, or CRITICAL.

Base Model: sentence-transformers/all-MiniLM-L6-v2 (80 MB, CPU-optimized)

This model can run efficiently in Lambda to predict severity before
calling Nova 2 Lite, reducing costs and latency for straightforward cases.
"""

import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from typing import Dict, Tuple, Optional, List
import numpy as np
from dataclasses import dataclass


@dataclass
class SeverityPrediction:
    """Output from severity classifier."""
    severity: str
    confidence: float
    logits: Dict[str, float]


class SeverityClassifier:
    """
    BERT-based classifier for log triage severity prediction.
    
    Classifies concatenated anomalous log sections as:
    - INFO (level 0): Non-critical, informational
    - WARNING (level 1): Should be monitored
    - HIGH (level 2): Significant issue, needs attention
    - CRITICAL (level 3): Urgent, immediate action required
    """
    
    LABELS = ["INFO", "WARNING", "HIGH", "CRITICAL"]
    LABEL_TO_ID = {label: idx for idx, label in enumerate(LABELS)}
    ID_TO_LABEL = {idx: label for label, idx in LABEL_TO_ID.items()}
    
    BASE_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    MAX_LENGTH = 512
    
    def __init__(
        self,
        model_name_or_path: str = BASE_MODEL,
        num_labels: int = 4,
        device: Optional[torch.device] = None
    ):
        """
        Initialize severity classifier.
        
        Args:
            model_name_or_path: HuggingFace model name or local path
            num_labels: Number of classification labels (default: 4)
            device: torch.device (CPU or CUDA)
        """
        self.device = device or torch.device("cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name_or_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_name_or_path,
            num_labels=num_labels
        ).to(self.device)
        self.model.eval()
    
    def predict(self, text: str) -> SeverityPrediction:
        """
        Predict severity for a log section.
        
        Args:
            text: Log text to classify (will be truncated to MAX_LENGTH)
            
        Returns:
            SeverityPrediction with severity, confidence, and logits
        """
        # Tokenize
        inputs = self.tokenizer(
            text,
            max_length=self.MAX_LENGTH,
            truncation=True,
            return_tensors="pt"
        ).to(self.device)
        
        # Forward pass
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits[0]
        
        # Get predictions
        probabilities = torch.softmax(logits, dim=-1)
        predicted_id = torch.argmax(probabilities).item()
        confidence = probabilities[predicted_id].item()
        
        # Build logits dict
        logits_dict = {
            self.ID_TO_LABEL[i]: float(logits[i].item())
            for i in range(len(self.LABELS))
        }
        
        return SeverityPrediction(
            severity=self.ID_TO_LABEL[predicted_id],
            confidence=confidence,
            logits=logits_dict
        )
    
    def predict_batch(self, texts: List[str]) -> List[SeverityPrediction]:
        """
        Predict severity for multiple log sections.
        
        Args:
            texts: List of log texts
            
        Returns:
            List of SeverityPrediction objects
        """
        return [self.predict(text) for text in texts]
    
    def save(self, save_path: str):
        """Save model and tokenizer."""
        self.model.save_pretrained(save_path)
        self.tokenizer.save_pretrained(save_path)
    
    @classmethod
    def load(
        cls,
        model_path: str,
        device: Optional[torch.device] = None
    ) -> "SeverityClassifier":
        """Load model and tokenizer from disk."""
        device = device or torch.device("cpu")
        return cls(model_name_or_path=model_path, device=device)


class SeverityClassifierConfig:
    """Configuration for fine-tuning severity classifier."""
    
    def __init__(
        self,
        base_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        num_labels: int = 4,
        max_length: int = 512,
        batch_size: int = 16,
        num_epochs: int = 5,
        learning_rate: float = 2e-5,
        validation_split: float = 0.2,
        device: Optional[torch.device] = None
    ):
        """Initialize configuration."""
        self.base_model = base_model
        self.num_labels = num_labels
        self.max_length = max_length
        self.batch_size = batch_size
        self.num_epochs = num_epochs
        self.learning_rate = learning_rate
        self.validation_split = validation_split
        self.device = device or torch.device("cpu")


class SeverityClassifierTrainer:
    """Trainer for severity classifier fine-tuning."""
    
    def __init__(self, config: SeverityClassifierConfig):
        """Initialize trainer."""
        self.config = config
        self.classifier = SeverityClassifier(
            model_name_or_path=config.base_model,
            num_labels=config.num_labels,
            device=config.device
        )
    
    def compute_metrics(
        self,
        predictions: np.ndarray,
        labels: np.ndarray
    ) -> Dict[str, float]:
        """
        Compute evaluation metrics.
        
        Args:
            predictions: Predicted label IDs
            labels: Ground truth label IDs
            
        Returns:
            Dict with accuracy and per-class metrics
        """
        accuracy = np.mean(predictions == labels)
        
        # Per-class metrics
        metrics = {"accuracy": accuracy}
        
        for label_id, label_name in SeverityClassifier.ID_TO_LABEL.items():
            mask = labels == label_id
            if mask.sum() > 0:
                class_accuracy = np.mean(predictions[mask] == labels[mask])
                metrics[f"accuracy_{label_name}"] = class_accuracy
        
        return metrics
