"""
Reward Model Training for RLHF

This module trains a reward model that learns to predict engineer satisfaction
based on suggestions and context. The reward model scores suggestions
and is used in DPO (Direct Preference Optimization) for fine-tuning.

The reward model:
- Encodes suggestions using BERT embeddings
- Includes context features (incident severity, service, etc.)
- Outputs a scalar reward (0-1)
- Trained with MSE loss on engineer feedback

Usage:
    python scripts/train_reward_model.py \
        --output_dir ./models/reward_model \
        --num_epochs 5 \
        --batch_size 32

Deployment:
    - Export to ONNX for Lambda inference
    - Or containerize for SageMaker endpoint
"""

import logging
import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import numpy as np

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, random_split
from transformers import AutoTokenizer, AutoModel, AdamW

try:
    from scripts.collect_voice_feedback import VoiceFeedback, VoiceFeedbackCollector
    _feedback_available = True
except ImportError:
    _feedback_available = False

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SuggestionRewardDataset(Dataset):
    """PyTorch dataset for reward model training."""
    
    def __init__(
        self,
        feedbacks: List[VoiceFeedback],
        tokenizer,
        max_length: int = 256
    ):
        """
        Initialize dataset.
        
        Args:
            feedbacks: List of VoiceFeedback objects
            tokenizer: Transformers tokenizer
            max_length: Max token length for suggestions
        """
        self.feedbacks = feedbacks
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self) -> int:
        return len(self.feedbacks)
    
    def __getitem__(self, idx: int) -> Dict:
        """
        Get a single training example.
        
        Returns:
            Dict with input_ids, attention_mask, and target reward
        """
        feedback = self.feedbacks[idx]
        
        # Tokenize suggestion
        encoding = self.tokenizer(
            feedback.suggestion,
            max_length=self.max_length,
            truncation=True,
            padding="max_length",
            return_tensors="pt"
        )
        
        # Target: normalize quality and helpfulness
        # quality: 0-10 → 0-1
        # helpfulness: 0 or 1 → 0 or 1
        quality_score = feedback.suggestion_quality / 10.0
        helpful_score = 1.0 if feedback.was_helpful else 0.0
        
        # Combined reward: 70% quality, 30% helpfulness
        target_reward = 0.7 * quality_score + 0.3 * helpful_score
        
        return {
            "input_ids": encoding["input_ids"][0],
            "attention_mask": encoding["attention_mask"][0],
            "target_reward": torch.tensor(target_reward, dtype=torch.float32)
        }


class RewardModel(nn.Module):
    """BERT-based reward model for suggestions."""
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        dropout: float = 0.1
    ):
        """
        Initialize reward model.
        
        Args:
            model_name: Pre-trained BERT model
            dropout: Dropout rate
        """
        super().__init__()
        
        self.encoder = AutoModel.from_pretrained(model_name)
        self.hidden_size = self.encoder.config.hidden_size
        
        # Prediction head
        self.head = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(self.hidden_size, 256),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(256, 1),
            nn.Sigmoid()  # Output in [0, 1]
        )
    
    def forward(self, input_ids, attention_mask):
        """
        Forward pass.
        
        Args:
            input_ids: Token IDs (batch_size, seq_len)
            attention_mask: Attention mask (batch_size, seq_len)
            
        Returns:
            Reward scores (batch_size, 1)
        """
        # Get BERT embeddings
        outputs = self.encoder(
            input_ids=input_ids,
            attention_mask=attention_mask
        )
        
        # Use [CLS] token embedding
        cls_embedding = outputs.last_hidden_state[:, 0, :]
        
        # Predict reward
        reward = self.head(cls_embedding)
        
        return reward


class RewardModelTrainer:
    """Trainer for reward model."""
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        learning_rate: float = 1e-4,
        batch_size: int = 32,
        num_epochs: int = 5,
        device: Optional[torch.device] = None
    ):
        """Initialize trainer."""
        self.device = device or torch.device("cpu")
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.num_epochs = num_epochs
        
        # Load model and tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = RewardModel(model_name).to(self.device)
        
        logger.info(f"Reward model with {sum(p.numel() for p in self.model.parameters())} parameters")
    
    def train(
        self,
        feedbacks: List[VoiceFeedback],
        val_split: float = 0.2
    ) -> Dict[str, List[float]]:
        """
        Train reward model.
        
        Args:
            feedbacks: List of VoiceFeedback objects
            val_split: Validation split ratio
            
        Returns:
            Training history
        """
        logger.info(f"Training on {len(feedbacks)} feedbacks...")
        
        # Create dataset
        dataset = SuggestionRewardDataset(feedbacks, self.tokenizer)
        
        # Split
        val_size = int(len(dataset) * val_split)
        train_size = len(dataset) - val_size
        train_dataset, val_dataset = random_split(
            dataset,
            [train_size, val_size]
        )
        
        # Create loaders
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
        optimizer = AdamW(self.model.parameters(), lr=self.learning_rate)
        criterion = nn.MSELoss()
        
        history = {
            "train_loss": [],
            "val_loss": [],
            "val_mse": []
        }
        
        for epoch in range(self.num_epochs):
            # Training
            self.model.train()
            total_loss = 0.0
            
            for batch in train_loader:
                input_ids = batch["input_ids"].to(self.device)
                attention_mask = batch["attention_mask"].to(self.device)
                targets = batch["target_reward"].to(self.device).unsqueeze(1)
                
                # Forward
                outputs = self.model(input_ids, attention_mask)
                loss = criterion(outputs, targets)
                
                # Backward
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item()
            
            avg_train_loss = total_loss / len(train_loader)
            history["train_loss"].append(avg_train_loss)
            
            # Validation
            self.model.eval()
            val_loss = 0.0
            all_preds = []
            all_targets = []
            
            with torch.no_grad():
                for batch in val_loader:
                    input_ids = batch["input_ids"].to(self.device)
                    attention_mask = batch["attention_mask"].to(self.device)
                    targets = batch["target_reward"].to(self.device).unsqueeze(1)
                    
                    outputs = self.model(input_ids, attention_mask)
                    loss = criterion(outputs, targets)
                    
                    val_loss += loss.item()
                    all_preds.extend(outputs.cpu().numpy().flatten())
                    all_targets.extend(targets.cpu().numpy().flatten())
            
            avg_val_loss = val_loss / len(val_loader)
            history["val_loss"].append(avg_val_loss)
            
            # Correlation metric
            correlation = np.corrcoef(all_preds, all_targets)[0, 1]
            
            logger.info(
                f"Epoch {epoch + 1}/{self.num_epochs} - "
                f"Train Loss: {avg_train_loss:.4f}, "
                f"Val Loss: {avg_val_loss:.4f}, "
                f"Correlation: {correlation:.3f}"
            )
        
        return history
    
    def save(self, save_path: str):
        """Save model and tokenizer."""
        save_path = Path(save_path)
        save_path.mkdir(parents=True, exist_ok=True)
        
        self.model.save_pretrained(str(save_path / "model"))
        self.tokenizer.save_pretrained(str(save_path / "tokenizer"))
        
        logger.info(f"Saved reward model to {save_path}")
    
    @classmethod
    def load(cls, model_path: str, device: Optional[torch.device] = None):
        """Load trained reward model."""
        model_path = Path(model_path)
        trainer = cls(device=device)
        
        trainer.model = RewardModel.load_from_pretrained(str(model_path / "model"))
        trainer.tokenizer = AutoTokenizer.from_pretrained(str(model_path / "tokenizer"))
        trainer.model.to(trainer.device)
        
        return trainer


def create_dummy_feedbacks() -> List[VoiceFeedback]:
    """Create dummy feedbacks for demo."""
    suggestions = [
        "Check CPU metrics for the service",
        "Review recent error logs",
        "Check database connection pool",
        "Analyze memory usage trends",
        "Review dependency health",
        "Check network latency",
        "Monitor queue depths",
        "Check cache hit rates"
    ]
    
    feedbacks = []
    for i, sugg in enumerate(suggestions):
        fb = VoiceFeedback(
            feedback_id=f"fb-{i}",
            incident_id=f"inc-{i}",
            suggestion=sugg,
            suggestion_quality=np.random.randint(3, 10),
            relevance_score=np.random.random(),
            was_helpful=np.random.random() > 0.3,
            overall_satisfaction=np.random.randint(4, 10),
            timestamp=datetime.now().isoformat()
        )
        feedbacks.append(fb)
        
        # Add more similar variations
        for j in range(5):
            fb_var = VoiceFeedback(
                feedback_id=f"fb-{i}-{j}",
                incident_id=f"inc-{i}-{j}",
                suggestion=sugg + f" (variant {j})",
                suggestion_quality=np.random.randint(3, 10),
                relevance_score=np.random.random(),
                was_helpful=np.random.random() > 0.3,
                overall_satisfaction=np.random.randint(4, 10),
                timestamp=datetime.now().isoformat()
            )
            feedbacks.append(fb_var)
    
    return feedbacks


def main():
    """Main training entry point."""
    parser = argparse.ArgumentParser(
        description="Train reward model for RLHF"
    )
    parser.add_argument(
        "--output_dir",
        default="./models/reward_model",
        help="Output directory"
    )
    parser.add_argument(
        "--num_epochs",
        type=int,
        default=5,
        help="Number of epochs"
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=32,
        help="Batch size"
    )
    parser.add_argument(
        "--learning_rate",
        type=float,
        default=1e-4,
        help="Learning rate"
    )
    parser.add_argument(
        "--model_name",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="Pre-trained model name"
    )
    
    args = parser.parse_args()
    
    # Setup device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")
    
    # Create trainer
    trainer = RewardModelTrainer(
        model_name=args.model_name,
        learning_rate=args.learning_rate,
        batch_size=args.batch_size,
        num_epochs=args.num_epochs,
        device=device
    )
    
    # Get feedbacks (try from collector, fallback to dummy)
    if _feedback_available:
        try:
            collector = VoiceFeedbackCollector()
            feedbacks = collector.get_feedback_for_training(min_records=100)
            if not feedbacks:
                logger.warning("No feedback found, using dummy data")
                feedbacks = create_dummy_feedbacks()
        except Exception as e:
            logger.warning(f"Error loading feedbacks: {e}, using dummy data")
            feedbacks = create_dummy_feedbacks()
    else:
        feedbacks = create_dummy_feedbacks()
    
    logger.info(f"Training on {len(feedbacks)} feedbacks")
    
    # Train
    history = trainer.train(feedbacks)
    
    # Save
    trainer.save(args.output_dir)
    
    # Save history
    with open(Path(args.output_dir) / "training_history.json", "w") as f:
        json.dump(history, f, indent=2)
    
    logger.info("Training complete!")


if __name__ == "__main__":
    main()
