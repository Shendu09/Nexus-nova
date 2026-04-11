"""DistilBERT-based severity classification."""

from __future__ import annotations
import logging
from dataclasses import dataclass
from novaml._config import settings
from novaml._models import Severity

logger = logging.getLogger(__name__)


@dataclass
class SeverityPrediction:
    """Result from severity classifier."""

    label: Severity
    confidence: float
    all_scores: dict


class SeverityClassifier:
    """Classify log severity using BERT + keyword fallback."""

    def __init__(self) -> None:
        self.model = None
        self.tokenizer = None
        self._load_model()

    def _load_model(self) -> None:
        """Lazy load DistilBERT model."""
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            logger.info("Loading DistilBERT severity classifier")
            model_name = "distilbert-base-uncased"
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                model_name,
                cache_dir=str(settings.models_dir_expanded / "classifiers"),
            )
        except Exception as e:
            logger.warning(f"Could not load BERT model: {e}")

    def predict(self, text: str) -> SeverityPrediction:
        """
        Predict severity of log text.

        Args:
            text: Log text to classify

        Returns:
            SeverityPrediction with label and confidence
        """
        # Try BERT first
        if self.model and self.tokenizer:
            try:
                pred = self._bert_predict(text)
                if pred:
                    return pred
            except Exception as e:
                logger.warning(f"BERT prediction failed: {e}")

        # Fall back to keyword-based
        return self._keyword_predict(text)

    def _bert_predict(self, text: str) -> SeverityPrediction | None:
        """Predict using BERT model."""
        try:
            import torch

            inputs = self.tokenizer(
                text,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            )

            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=1)[0]

            # Map to severity
            severity_order = [Severity.INFO, Severity.WARNING, Severity.HIGH, Severity.CRITICAL]
            idx = torch.argmax(probabilities).item()
            label = severity_order[idx]
            confidence = float(probabilities[idx].item())

            return SeverityPrediction(
                label=label,
                confidence=confidence,
                all_scores={s.value: float(probabilities[i].item()) for i, s in enumerate(severity_order)},
            )
        except Exception as e:
            logger.error(f"BERT error: {e}")
            return None

    def _keyword_predict(self, text: str) -> SeverityPrediction:
        """Keyword-based severity prediction."""
        text_lower = text.lower()

        if any(word in text_lower for word in ["fatal", "oom", "out of memory", "segfault", "panic"]):
            return SeverityPrediction(
                label=Severity.CRITICAL,
                confidence=0.7,
                all_scores={
                    "INFO": 0.0,
                    "WARNING": 0.1,
                    "HIGH": 0.2,
                    "CRITICAL": 0.7,
                },
            )

        if any(word in text_lower for word in ["error", "exception", "failed", "connection refused"]):
            return SeverityPrediction(
                label=Severity.HIGH,
                confidence=0.65,
                all_scores={
                    "INFO": 0.0,
                    "WARNING": 0.15,
                    "HIGH": 0.65,
                    "CRITICAL": 0.2,
                },
            )

        if any(word in text_lower for word in ["warn", "warning", "slow", "timeout"]):
            return SeverityPrediction(
                label=Severity.WARNING,
                confidence=0.6,
                all_scores={
                    "INFO": 0.1,
                    "WARNING": 0.6,
                    "HIGH": 0.2,
                    "CRITICAL": 0.1,
                },
            )

        # Default to INFO
        return SeverityPrediction(
            label=Severity.INFO,
            confidence=0.55,
            all_scores={
                "INFO": 0.55,
                "WARNING": 0.3,
                "HIGH": 0.1,
                "CRITICAL": 0.05,
            },
        )

    def train_severity_classifier(
        self, texts: list[str], labels: list[str], output_dir: str = "~/.novaml/models"
    ) -> dict:
        """Fine-tune severity classifier on labeled data."""
        try:
            import torch
            from torch.utils.data import TensorDataset, DataLoader
            from transformers import Trainer, TrainingArguments

            logger.info(f"Training severity classifier on {len(texts)} examples")

            if len(texts) < 10:
                return {"error": "Need at least 10 training examples"}

            # Tokenize
            inputs = self.tokenizer(
                texts,
                truncation=True,
                max_length=512,
                padding=True,
                return_tensors="pt",
            )

            # Map labels to class indices
            label2id = {
                "INFO": 0,
                "WARNING": 1,
                "HIGH": 2,
                "CRITICAL": 3,
            }
            label_ids = torch.tensor([label2id[l] for l in labels])

            dataset = TensorDataset(
                inputs["input_ids"],
                inputs["attention_mask"],
                label_ids,
            )

            # Split 80/20
            split = int(0.8 * len(dataset))
            train_dataset = TensorDataset(*[t[:split] for t in dataset.tensors])
            val_dataset = TensorDataset(*[t[split:] for t in dataset.tensors])

            training_args = TrainingArguments(
                output_dir=output_dir,
                num_train_epochs=3,
                per_device_train_batch_size=8,
                per_device_eval_batch_size=8,
                logging_steps=10,
                eval_strategy="epoch",
            )

            trainer = Trainer(
                model=self.model,
                args=training_args,
                train_dataset=train_dataset,
                eval_dataset=val_dataset,
            )

            trainer.train()
            logger.info(f"Training complete. Model saved to {output_dir}")

            return {
                "output_dir": output_dir,
                "num_examples": len(texts),
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Training failed: {e}")
            return {"error": str(e)}
