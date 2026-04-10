"""
Unit tests for LSTM-based log anomaly detector (Module 1).

Covers:
- Model architecture and shapes
- Forward pass with different input sizes
- Hidden state management
- Dataset windowing and sequences
- Scorer interface (calibration, inference)
- Integration end-to-end
"""

import unittest
import torch
import torch.nn as nn
import numpy as np
from typing import Tuple

from nexus.models.lstm import (
    LogAnomalyLSTM,
    LogAnomalyLSTMConfig,
    LogSequenceDataset,
    LogAnomalyLSTMScorer
)


class TestLogAnomalyLSTMConfig(unittest.TestCase):
    """Test LSTM configuration."""
    
    def test_config_defaults(self):
        """Test default configuration values."""
        config = LogAnomalyLSTMConfig()
        
        self.assertEqual(config.embedding_dim, 768)
        self.assertEqual(config.hidden_dim, 256)
        self.assertEqual(config.num_layers, 2)
        self.assertEqual(config.dropout, 0.3)
        self.assertTrue(config.bidirectional)
        self.assertEqual(config.sequence_length, 16)
    
    def test_config_custom(self):
        """Test custom configuration."""
        config = LogAnomalyLSTMConfig(
            embedding_dim=512,
            hidden_dim=128,
            num_layers=3,
            dropout=0.5,
            bidirectional=False
        )
        
        self.assertEqual(config.embedding_dim, 512)
        self.assertEqual(config.hidden_dim, 128)
        self.assertEqual(config.num_layers, 3)
        self.assertEqual(config.dropout, 0.5)
        self.assertFalse(config.bidirectional)


class TestLogAnomalyLSTM(unittest.TestCase):
    """Test LSTM model architecture and forward pass."""
    
    def setUp(self):
        """Create model and config for each test."""
        self.config = LogAnomalyLSTMConfig(device="cpu")
        self.model = LogAnomalyLSTM(self.config)
    
    def test_model_initialization(self):
        """Test model instantiation."""
        self.assertIsNotNone(self.model)
        self.assertIsInstance(self.model.lstm, nn.LSTM)
        self.assertIsInstance(self.model.fc1, nn.Linear)
        self.assertIsInstance(self.model.fc2, nn.Linear)
    
    def test_forward_pass_shape(self):
        """Test forward pass with correct input shape."""
        batch_size = 32
        seq_len = self.config.sequence_length
        embedding_dim = self.config.embedding_dim
        
        # Create dummy input
        x = torch.randn(batch_size, seq_len, embedding_dim)
        
        # Forward pass
        predictions, (h_n, c_n) = self.model(x)
        
        # Check output shapes
        self.assertEqual(predictions.shape, (batch_size, 1))
        self.assertTrue(0 <= predictions.min() <= predictions.max() <= 1)  # Sigmoid output
    
    def test_forward_pass_single_sample(self):
        """Test forward pass with single sample."""
        x = torch.randn(1, self.config.sequence_length, self.config.embedding_dim)
        predictions, _ = self.model(x)
        
        self.assertEqual(predictions.shape, (1, 1))
        self.assertTrue(0 <= predictions.item() <= 1)
    
    def test_forward_pass_different_batch_sizes(self):
        """Test forward pass with various batch sizes."""
        for batch_size in [1, 16, 32, 64]:
            x = torch.randn(
                batch_size,
                self.config.sequence_length,
                self.config.embedding_dim
            )
            predictions, _ = self.model(x)
            self.assertEqual(predictions.shape, (batch_size, 1))
    
    def test_forward_pass_incorrect_shape_raises(self):
        """Test that incorrect input shapes raise errors."""
        # 2D input (missing sequence dimension)
        x = torch.randn(32, self.config.embedding_dim)
        with self.assertRaises(ValueError):
            self.model(x)
    
    def test_encode_sequence(self):
        """Test latent representation encoding."""
        batch_size = 16
        x = torch.randn(batch_size, self.config.sequence_length, self.config.embedding_dim)
        
        latent = self.model.encode_sequence(x)
        
        # Should return LSTM output dimension
        lstm_output_dim = self.config.hidden_dim * (2 if self.config.bidirectional else 1)
        self.assertEqual(latent.shape, (batch_size, lstm_output_dim))
    
    def test_compute_anomaly_score(self):
        """Test anomaly score computation."""
        batch_size = 32
        x = torch.randn(batch_size, self.config.sequence_length, self.config.embedding_dim)
        
        scores = self.model.compute_anomaly_score(x)
        
        # Should return numpy array with scores in [0, 1]
        self.assertIsInstance(scores, np.ndarray)
        self.assertEqual(scores.shape, (batch_size,))
        self.assertTrue(np.all(scores >= 0) and np.all(scores <= 1))
    
    def test_model_eval_mode(self):
        """Test that model respects eval/train mode."""
        self.model.train()
        self.assertTrue(self.model.training)
        
        self.model.eval()
        self.assertFalse(self.model.training)
    
    def test_gradient_flow(self):
        """Test that gradients flow properly."""
        x = torch.randn(
            8,
            self.config.sequence_length,
            self.config.embedding_dim,
            requires_grad=False
        )
        labels = torch.randint(0, 2, (8, 1)).float()
        
        predictions, _ = self.model(x)
        loss = nn.BCELoss()(predictions, labels)
        loss.backward()
        
        # Check that gradients are computed
        for param in self.model.parameters():
            if param.requires_grad:
                self.assertIsNotNone(param.grad)
                self.assertFalse(torch.all(param.grad == 0))


class TestLogSequenceDataset(unittest.TestCase):
    """Test log sequence dataset creation and windowing."""
    
    def setUp(self):
        """Create dummy embeddings and labels."""
        np.random.seed(42)
        self.num_logs = 1000
        self.embedding_dim = 768
        self.embeddings = np.random.randn(self.num_logs, self.embedding_dim)
        self.labels = np.random.randint(0, 2, self.num_logs)
    
    def test_dataset_creation(self):
        """Test basic dataset creation."""
        dataset = LogSequenceDataset(
            self.embeddings,
            self.labels,
            sequence_length=16,
            stride=4
        )
        
        self.assertGreater(len(dataset), 0)
        self.assertEqual(len(dataset.sequences), len(dataset.labels))
    
    def test_sequence_shape(self):
        """Test that sequences have correct shape."""
        dataset = LogSequenceDataset(
            self.embeddings,
            self.labels,
            sequence_length=16,
            stride=4
        )
        
        seq, label = dataset[0]
        self.assertEqual(seq.shape, (16, self.embedding_dim))
        self.assertEqual(label.shape, (1,))
    
    def test_sequence_length_constraint(self):
        """Test that all sequences have correct length."""
        seq_len = 16
        dataset = LogSequenceDataset(
            self.embeddings,
            self.labels,
            sequence_length=seq_len,
            stride=1  # No overlap
        )
        
        for i in range(min(10, len(dataset))):
            seq, _ = dataset[i]
            self.assertEqual(seq.shape[0], seq_len)
    
    def test_stride_affects_count(self):
        """Test that stride affects number of windows."""
        stride_1 = LogSequenceDataset(
            self.embeddings,
            self.labels,
            sequence_length=16,
            stride=1
        )
        
        stride_4 = LogSequenceDataset(
            self.embeddings,
            self.labels,
            sequence_length=16,
            stride=4
        )
        
        # More windows with smaller stride
        self.assertGreater(len(stride_1), len(stride_4))
    
    def test_labels_are_binary(self):
        """Test that labels are binary (0 or 1)."""
        dataset = LogSequenceDataset(
            self.embeddings,
            self.labels,
            sequence_length=16,
            stride=4
        )
        
        for i in range(min(100, len(dataset))):
            _, label = dataset[i]
            self.assertIn(label.item(), [0.0, 1.0])
    
    def test_small_dataset_handling(self):
        """Test handling of dataset smaller than sequence length."""
        small_embeddings = np.random.randn(10, self.embedding_dim)
        small_labels = np.random.randint(0, 2, 10)
        
        dataset = LogSequenceDataset(
            small_embeddings,
            small_labels,
            sequence_length=16,
            stride=4
        )
        
        # Should handle gracefully (will create 0 or 1 sequence)
        self.assertGreaterEqual(len(dataset), 0)


class TestLogAnomalyLSTMScorer(unittest.TestCase):
    """Test high-level LSTM scorer interface."""
    
    def setUp(self):
        """Create model and scorer."""
        self.config = LogAnomalyLSTMConfig(device="cpu")
        self.model = LogAnomalyLSTM(self.config)
        self.scorer = LogAnomalyLSTMScorer(self.model, threshold=0.5, config=self.config)
    
    def test_scorer_initialization(self):
        """Test scorer creation."""
        self.assertIsNotNone(self.scorer)
        self.assertEqual(self.scorer.threshold, 0.5)
    
    def test_calibrate_threshold(self):
        """Test threshold calibration from baseline data."""
        # Create synthetic normal embeddings
        np.random.seed(42)
        baseline_embeddings = np.random.randn(1000, self.config.embedding_dim)
        baseline_labels = np.zeros(1000)  # All normal
        
        threshold = self.scorer.calibrate_threshold(
            baseline_embeddings,
            baseline_labels,
            percentile=95.0
        )
        
        self.assertIsInstance(threshold, float)
        self.assertTrue(0 <= threshold <= 1)
    
    def test_score_single_sequence(self):
        """Test scoring a single sequence."""
        # Create dummy sequence
        embedding = np.random.randn(self.config.embedding_dim)
        
        score = self.scorer.score_sequence(embedding)
        
        self.assertIsInstance(score, (float, np.floating))
        self.assertTrue(0 <= score <= 1)
    
    def test_score_sequence_batch(self):
        """Test scoring batch of sequences."""
        batch = np.random.randn(32, self.config.embedding_dim)
        
        scores = self.scorer.score_sequences_batch(batch)
        
        self.assertEqual(scores.shape, (32,))
        self.assertTrue(np.all(scores >= 0) and np.all(scores <= 1))
    
    def test_predict_anomaly_binary(self):
        """Test binary anomaly predictions."""
        batch = np.random.randn(32, self.config.embedding_dim)
        
        result = self.scorer.predict_anomaly(batch, return_scores=True)
        
        self.assertIn('predictions', result)
        self.assertIn('scores', result)
        self.assertIn('threshold', result)
        
        # Predictions should be binary
        predictions = result['predictions']
        self.assertTrue(np.all(np.isin(predictions, [0, 1])))
    
    def test_threshold_effect_on_predictions(self):
        """Test that threshold affects predictions."""
        batch = np.random.randn(32, self.config.embedding_dim)
        
        # Low threshold → more positives
        self.scorer.threshold = 0.1
        result_low = self.scorer.predict_anomaly(batch)
        low_positives = np.sum(result_low['predictions'])
        
        # High threshold → fewer positives
        self.scorer.threshold = 0.9
        result_high = self.scorer.predict_anomaly(batch)
        high_positives = np.sum(result_high['predictions'])
        
        # Lower threshold should give more positive predictions
        self.assertGreaterEqual(low_positives, high_positives)


class TestLogAnomalyLSTMIntegration(unittest.TestCase):
    """Integration tests for complete LSTM pipeline."""
    
    def test_end_to_end_pipeline(self):
        """Test full pipeline: data → model → scoring."""
        # 1. Create synthetic data
        np.random.seed(42)
        torch.manual_seed(42)
        
        embeddings = np.random.randn(500, 768)
        labels = np.random.randint(0, 2, 500)
        
        # 2. Create dataset
        dataset = LogSequenceDataset(embeddings, labels, sequence_length=16, stride=4)
        self.assertGreater(len(dataset), 0)
        
        # 3. Create model
        config = LogAnomalyLSTMConfig(device="cpu")
        model = LogAnomalyLSTM(config)
        
        # 4. Single forward pass
        seq, label = dataset[0]
        seq_batch = seq.unsqueeze(0)  # Add batch dimension
        predictions, _ = model(seq_batch)
        
        self.assertEqual(predictions.shape, (1, 1))
        self.assertTrue(0 <= predictions.item() <= 1)
        
        # 5. Create scorer
        scorer = LogAnomalyLSTMScorer(model, threshold=0.5, config=config)
        
        # 6. Calibrate threshold
        baseline = np.random.randn(500, 768)
        baseline_labels = np.zeros(500)
        scorer.calibrate_threshold(baseline, baseline_labels, percentile=90)
        
        # 7. Score batch
        test_batch = np.random.randn(32, 768)
        scores = scorer.score_sequences_batch(test_batch)
        self.assertEqual(len(scores), 32)
    
    def test_model_save_load(self):
        """Test model serialization and loading."""
        import tempfile
        import os
        
        # Create and train for 1 epoch
        config = LogAnomalyLSTMConfig(device="cpu")
        model1 = LogAnomalyLSTM(config)
        
        # Get initial predictions
        x = torch.randn(8, config.sequence_length, config.embedding_dim)
        pred1, _ = model1(x)
        
        # Save model
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = os.path.join(tmpdir, "model.pt")
            torch.save(model1.state_dict(), model_path)
            
            # Load into new model
            model2 = LogAnomalyLSTM(config)
            model2.load_state_dict(torch.load(model_path))
            
            # Get predictions with loaded model
            pred2, _ = model2(x)
            
            # Should be identical
            torch.testing.assert_close(pred1, pred2)


if __name__ == "__main__":
    unittest.main()
