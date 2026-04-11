"""
Replaces: Nova 2 Lite freeform severity judgment
With: Fine-tuned BERT classifier (HuggingFace)
Cost: FREE — local inference after one-time training
"""

from __future__ import annotations
import logging
import torch
from pathlib import Path
from dataclasses import dataclass
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
)
from src.config import settings

logger = logging.getLogger(__name__)

LABELS = ["INFO", "WARNING", "HIGH", "CRITICAL"]
MODEL_BASE = "distilbert-base-uncased"


@dataclass
class SeverityPrediction:
    """Output of severity classifier."""
    label: str
    confidence: float
    all_scores: dict[str, float]


class SeverityClassifier:
    """
    DistilBERT fine-tuned to classify log severity.
    Falls back to keyword rules if model not trained yet.
    """

    def __init__(self) -> None:
        self._tokenizer = None
        self._model = None
        self._load()

    def _load(self) -> None:
        """Load fine-tuned model if it exists."""
        model_path = settings.models_dir / "severity_classifier"
        if model_path.exists():
            try:
                self._tokenizer = AutoTokenizer.from_pretrained(str(model_path))
                self._model = AutoModelForSequenceClassification.from_pretrained(
                    str(model_path)
                )
                self._model.eval()
                logger.info("Severity classifier loaded from disk")
            except Exception as e:
                logger.warning(f"Could not load classifier: {e}")

    def predict(self, log_text: str) -> SeverityPrediction:
        """
        Predict severity of a log section.

        Args:
            log_text: Log lines joined as a string (max 512 tokens)

        Returns:
            SeverityPrediction with label and confidence
        """
        if self._model is not None:
            return self._bert_predict(log_text)
        return self._keyword_predict(log_text)

    def _bert_predict(self, text: str) -> SeverityPrediction:
        """Run BERT inference."""
        inputs = self._tokenizer(
            text[:1024],
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True,
        )
        with torch.no_grad():
            logits = self._model(**inputs).logits
        probs = torch.softmax(logits, dim=-1).squeeze().tolist()
        idx = int(torch.argmax(logits).item())
        return SeverityPrediction(
            label=LABELS[idx],
            confidence=probs[idx],
            all_scores=dict(zip(LABELS, probs)),
        )

    def _keyword_predict(self, text: str) -> SeverityPrediction:
        """Rule-based fallback."""
        lower = text.lower()
        if any(k in lower for k in ["fatal", "critical", "oom", "panic", "crash"]):
            label, conf = "CRITICAL", 0.7
        elif any(k in lower for k in ["error", "exception", "failed", "refused"]):
            label, conf = "HIGH", 0.65
        elif any(k in lower for k in ["warn", "slow", "retry", "degraded"]):
            label, conf = "WARNING", 0.6
        else:
            label, conf = "INFO", 0.55
        scores = {l: 0.1 for l in LABELS}
        scores[label] = conf
        return SeverityPrediction(label=label, confidence=conf, all_scores=scores)


def train_severity_classifier(
    texts: list[str],
    labels: list[str],
    output_dir: str = "models/severity_classifier",
    epochs: int = 5,
) -> None:
    """
    Fine-tune DistilBERT for severity classification.

    Args:
        texts: Log sections (strings)
        labels: Severity labels ("INFO", "WARNING", "HIGH", "CRITICAL")
        output_dir: Where to save the model
        epochs: Training epochs
    """
    from transformers import Trainer, TrainingArguments
    from torch.utils.data import Dataset

    label2id = {l: i for i, l in enumerate(LABELS)}
    tokenizer = AutoTokenizer.from_pretrained(MODEL_BASE)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_BASE,
        num_labels=len(LABELS),
        id2label={i: l for i, l in enumerate(LABELS)},
        label2id=label2id,
    )

    class LogDataset(Dataset):
        def __init__(self, texts, labels):
            self.encodings = tokenizer(
                texts, truncation=True, padding=True, max_length=512
            )
            self.labels = [label2id[l] for l in labels]

        def __len__(self):
            return len(self.labels)

        def __getitem__(self, idx):
            item = {k: torch.tensor(v[idx]) for k, v in self.encodings.items()}
            item["labels"] = torch.tensor(self.labels[idx])
            return item

    dataset = LogDataset(texts, labels)
    split = int(0.8 * len(dataset))
    train_ds = torch.utils.data.Subset(dataset, range(split))
    eval_ds = torch.utils.data.Subset(dataset, range(split, len(dataset)))

    args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=16,
        learning_rate=2e-5,
        evaluation_strategy="epoch",
        save_strategy="best",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        logging_dir="logs/training",
        report_to="none",
    )
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
    )
    trainer.train()
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    logger.info(f"Severity classifier saved to {output_dir}")
