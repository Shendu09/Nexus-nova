"""
Unit tests for BERT-based severity classifier module.
"""

import pytest
import torch
import numpy as np
from pathlib import Path
import tempfile

from nexus.models.bert_classifier import (
    SeverityClassifier,
    SeverityClassifierConfig,
    SeverityClassifierTrainer,
    SeverityPrediction
)


class TestSeverityClassifier:
    """Tests for base SeverityClassifier class."""
    
    @pytest.fixture
    def classifier(self):
        """Create classifier instance."""
        return SeverityClassifier(
            device=torch.device("cpu")
        )
    
    def test_init_default(self):
        """Test default initialization."""
        classifier = SeverityClassifier()
        assert classifier.device.type == "cpu"
        assert len(classifier.LABELS) == 4
        assert "INFO" in classifier.LABELS
        assert "CRITICAL" in classifier.LABELS
    
    def test_labels_mapping(self, classifier):
        """Test label-to-ID mapping."""
        assert classifier.LABEL_TO_ID["INFO"] == 0
        assert classifier.LABEL_TO_ID["WARNING"] == 1
        assert classifier.LABEL_TO_ID["HIGH"] == 2
        assert classifier.LABEL_TO_ID["CRITICAL"] == 3
        
        assert classifier.ID_TO_LABEL[0] == "INFO"
        assert classifier.ID_TO_LABEL[3] == "CRITICAL"
    
    def test_predict_info(self, classifier):
        """Test prediction on informational log."""
        text = "Application started successfully. All systems operational."
        prediction = classifier.predict(text)
        
        assert isinstance(prediction, SeverityPrediction)
        assert prediction.severity in classifier.LABELS
        assert 0 <= prediction.confidence <= 1
        assert len(prediction.logits) == 4
    
    def test_predict_critical(self, classifier):
        """Test prediction on critical log."""
        text = "CRITICAL: FATAL ERROR - System failure imminent. Immediate action required NOW!"
        prediction = classifier.predict(text)
        
        assert isinstance(prediction, SeverityPrediction)
        assert prediction.severity in classifier.LABELS
        assert prediction.confidence > 0.1  # Should have reasonable confidence
    
    def test_predict_truncation(self, classifier):
        """Test that long texts are truncated."""
        # Create very long text
        long_text = "Error: " * 1000
        prediction = classifier.predict(long_text)
        
        assert isinstance(prediction, SeverityPrediction)
        assert prediction.severity in classifier.LABELS
    
    def test_predict_batch(self, classifier):
        """Test batch prediction."""
        texts = [
            "Normal operation",
            "Warning: High CPU",
            "CRITICAL: System down",
            "Info message"
        ]
        
        predictions = classifier.predict_batch(texts)
        
        assert len(predictions) == 4
        assert all(isinstance(p, SeverityPrediction) for p in predictions)
        assert all(p.severity in classifier.LABELS for p in predictions)
        assert all(0 <= p.confidence <= 1 for p in predictions)
    
    def test_logits_dict_structure(self, classifier):
        """Test logits dictionary structure."""
        text = "Sample log message"
        prediction = classifier.predict(text)
        
        logits = prediction.logits
        assert len(logits) == 4
        assert all(label in logits for label in classifier.LABELS)
        assert all(isinstance(v, float) for v in logits.values())
    
    def test_save_and_load(self, classifier):
        """Test model save and load."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Save model
            classifier.save(tmpdir)
            
            # Check files exist
            assert (Path(tmpdir) / "config.json").exists()
            assert (Path(tmpdir) / "pytorch_model.bin").exists()
            
            # Load model
            loaded_classifier = SeverityClassifier.load(tmpdir)
            
            # Verify predictions are the same
            text = "Test message"
            pred1 = classifier.predict(text)
            pred2 = loaded_classifier.predict(text)
            
            assert pred1.severity == pred2.severity
            assert np.allclose(
                list(pred1.logits.values()),
                list(pred2.logits.values()),
                rtol=1e-5
            )


class TestSeverityClassifierConfig:
    """Tests for configuration class."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = SeverityClassifierConfig()
        
        assert config.num_labels == 4
        assert config.max_length == 512
        assert config.batch_size == 16
        assert config.num_epochs == 5
        assert config.learning_rate == 2e-5
        assert config.validation_split == 0.2
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = SeverityClassifierConfig(
            batch_size=32,
            num_epochs=10,
            learning_rate=1e-4
        )
        
        assert config.batch_size == 32
        assert config.num_epochs == 10
        assert config.learning_rate == 1e-4
    
    def test_device_assignment(self):
        """Test device assignment in config."""
        device = torch.device("cpu")
        config = SeverityClassifierConfig(device=device)
        
        assert config.device == device


class TestSeverityClassifierTrainer:
    """Tests for trainer class."""
    
    def test_trainer_init(self):
        """Test trainer initialization."""
        config = SeverityClassifierConfig()
        trainer = SeverityClassifierTrainer(config)
        
        assert trainer.config == config
        assert trainer.classifier is not None
        assert trainer.classifier.model is not None
    
    def test_compute_metrics(self):
        """Test metrics computation."""
        config = SeverityClassifierConfig()
        trainer = SeverityClassifierTrainer(config)
        
        # Create sample predictions and labels
        predictions = np.array([0, 1, 2, 3, 0, 1, 2, 3])
        labels = np.array([0, 1, 2, 3, 0, 1, 2, 3])
        
        metrics = trainer.compute_metrics(predictions, labels)
        
        assert "accuracy" in metrics
        assert metrics["accuracy"] == 1.0
    
    def test_compute_metrics_with_errors(self):
        """Test metrics with prediction errors."""
        config = SeverityClassifierConfig()
        trainer = SeverityClassifierTrainer(config)
        
        predictions = np.array([0, 1, 2, 3, 1, 1, 3, 0])  # Some wrong
        labels = np.array([0, 1, 2, 3, 0, 1, 2, 3])
        
        metrics = trainer.compute_metrics(predictions, labels)
        
        assert "accuracy" in metrics
        assert 0 < metrics["accuracy"] < 1.0
        assert metrics["accuracy"] == 0.5
    
    def test_train_with_small_batch(self):
        """Test training with small data."""
        config = SeverityClassifierConfig(
            num_epochs=1,
            batch_size=2
        )
        trainer = SeverityClassifierTrainer(config)
        
        texts = [
            "Normal operation",
            "Warning message",
            "High severity error",
            "Critical failure"
        ]
        labels = ["INFO", "WARNING", "HIGH", "CRITICAL"]
        
        history = trainer.train(texts, labels)
        
        assert "train_loss" in history
        assert "val_loss" in history
        assert "val_accuracy" in history
        
        assert len(history["train_loss"]) == 1
        assert len(history["val_loss"]) == 1
        assert len(history["val_accuracy"]) == 1
    
    def test_train_with_validation_data(self):
        """Test training with separate validation data."""
        config = SeverityClassifierConfig(
            num_epochs=1,
            batch_size=2
        )
        trainer = SeverityClassifierTrainer(config)
        
        train_texts = ["Normal", "Warning", "High", "Critical"]
        train_labels = ["INFO", "WARNING", "HIGH", "CRITICAL"]
        
        val_texts = ["Normal again", "Warning again"]
        val_labels = ["INFO", "WARNING"]
        
        history = trainer.train(
            train_texts,
            train_labels,
            val_texts,
            val_labels
        )
        
        assert len(history["val_loss"]) == 1
        assert len(history["val_accuracy"]) == 1


class TestSeverityPrediction:
    """Tests for prediction output."""
    
    def test_prediction_dataclass(self):
        """Test SeverityPrediction dataclass."""
        logits = {
            "INFO": 0.1,
            "WARNING": 0.2,
            "HIGH": 0.5,
            "CRITICAL": 0.2
        }
        
        pred = SeverityPrediction(
            severity="HIGH",
            confidence=0.5,
            logits=logits
        )
        
        assert pred.severity == "HIGH"
        assert pred.confidence == 0.5
        assert pred.logits == logits


class TestSeverityClassifierIntegration:
    """Integration tests for severity classifier."""
    
    def test_end_to_end_prediction_pipeline(self):
        """Test complete prediction pipeline."""
        classifier = SeverityClassifier()
        
        # Create diverse log samples
        logs = [
            ("Successfully processed 1000 requests", "INFO"),
            ("Memory usage at 80%, monitor closely", "WARNING"),
            ("Database timeout, service degrading", "HIGH"),
            ("CRITICAL: System shutdown initiated", "CRITICAL")
        ]
        
        predictions = []
        for log_text, expected_severity in logs:
            pred = classifier.predict(log_text)
            predictions.append(pred)
            
            assert pred.severity in SeverityClassifier.LABELS
            assert pred.confidence > 0
        
        assert len(predictions) == 4
    
    def test_confidence_scores_valid_range(self):
        """Test that confidence scores are in valid range."""
        classifier = SeverityClassifier()
        
        texts = [
            "Normal log",
            "Error occurred",
            "Critical failure",
            "Warning message"
        ]
        
        for text in texts:
            pred = classifier.predict(text)
            assert 0 <= pred.confidence <= 1
            assert isinstance(pred.confidence, float)
