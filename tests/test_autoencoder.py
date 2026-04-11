"""
Unit tests for autoencoder anomaly detection module.

Tests cover:
- Model initialization and forward pass
- Reconstruction error computation
- Threshold calibration
- Anomaly scoring
"""

import unittest
import numpy as np
import torch
from typing import Tuple

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from nexus.models.autoencoder import (
    LogAutoencoder,
    AutoencoderScorer,
    AutoencoderScorerConfig
)


class TestLogAutoencoder(unittest.TestCase):
    """Test LogAutoencoder model."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.device = torch.device("cpu")
        self.model = LogAutoencoder(device=self.device)
        self.batch_size = 32
        self.input_dim = 768
    
    def test_model_initialization(self):
        """Test that model initializes correctly."""
        self.assertIsNotNone(self.model.encoder)
        self.assertIsNotNone(self.model.decoder)
        self.assertEqual(self.model.input_dim, 768)
        self.assertEqual(self.model.latent_dim, 64)
    
    def test_forward_pass(self):
        """Test forward pass through encoder and decoder."""
        x = torch.randn(self.batch_size, self.input_dim)
        reconstructed, latent = self.model(x)
        
        # Check output shapes
        self.assertEqual(reconstructed.shape, x.shape)
        self.assertEqual(latent.shape, (self.batch_size, 64))
    
    def test_encoder_output_shape(self):
        """Test encoder produces correct latent dimension."""
        x = torch.randn(self.batch_size, self.input_dim)
        z = self.model.encode(x)
        
        self.assertEqual(z.shape, (self.batch_size, 64))
    
    def test_decoder_output_shape(self):
        """Test decoder produces correct reconstruction dimension."""
        z = torch.randn(self.batch_size, 64)
        reconstructed = self.model.decode(z)
        
        self.assertEqual(reconstructed.shape, (self.batch_size, self.input_dim))
    
    def test_reconstruction_error_computation(self):
        """Test reconstruction error computation."""
        x = torch.randn(self.batch_size, self.input_dim)
        errors = self.model.compute_reconstruction_error(x)
        
        # Check output shape
        self.assertEqual(len(errors), self.batch_size)
        
        # Check values are non-negative and finite
        self.assertTrue(np.all(errors >= 0))
        self.assertTrue(np.all(np.isfinite(errors)))
    
    def test_latent_representation(self):
        """Test latent representation extraction."""
        x = torch.randn(self.batch_size, self.input_dim)
        latent = self.model.get_latent_representation(x)
        
        # Check shape
        self.assertEqual(latent.shape, (self.batch_size, 64))
        
        # Check it's a numpy array
        self.assertIsInstance(latent, np.ndarray)


class TestAutoencoderScorerConfig(unittest.TestCase):
    """Test AutoencoderScorerConfig."""
    
    def test_config_initialization_defaults(self):
        """Test config initializes with defaults."""
        config = AutoencoderScorerConfig()
        
        self.assertEqual(config.input_dim, 768)
        self.assertEqual(config.batch_size, 128)
        self.assertEqual(config.num_epochs, 50)
    
    def test_config_initialization_custom(self):
        """Test config initializes with custom values."""
        config = AutoencoderScorerConfig(
            batch_size=256,
            num_epochs=100,
            std_multiplier=2.5
        )
        
        self.assertEqual(config.batch_size, 256)
        self.assertEqual(config.num_epochs, 100)
        self.assertEqual(config.std_multiplier, 2.5)


class TestAutoencoderScorer(unittest.TestCase):
    """Test AutoencoderScorer."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.device = torch.device("cpu")
        self.model = LogAutoencoder(device=self.device)
        self.scorer = AutoencoderScorer(self.model)
        
        # Create dummy baseline embeddings
        np.random.seed(42)
        self.baseline = torch.randn(1000, 768)
    
    def test_scorer_initialization(self):
        """Test scorer initializes correctly."""
        self.assertIsNotNone(self.scorer.model)
        self.assertIsNone(self.scorer.threshold)
    
    def test_threshold_calibration(self):
        """Test threshold calibration."""
        threshold = self.scorer.calibrate_threshold(self.baseline)
        
        # Check that threshold was set
        self.assertIsNotNone(threshold)
        self.assertGreater(threshold, 0)
        
        # Check that baseline stats were computed
        self.assertIsNotNone(self.scorer.baseline_mean)
        self.assertIsNotNone(self.scorer.baseline_std)
    
    def test_score_logs_after_calibration(self):
        """Test log scoring after threshold calibration."""
        # Calibrate first
        self.scorer.calibrate_threshold(self.baseline)
        
        # Score some logs
        test_logs = torch.randn(100, 768)
        result = self.scorer.score_logs(test_logs)
        
        # Check result structure
        self.assertIn("scores", result)
        self.assertIn("is_anomaly", result)
        self.assertIn("anomaly_indices", result)
        self.assertIn("n_anomalies", result)
        self.assertIn("threshold", result)
        
        # Check shapes
        self.assertEqual(len(result["scores"]), 100)
        self.assertEqual(len(result["is_anomaly"]), 100)
    
    def test_anomaly_detection_threshold(self):
        """Test that anomalies are correctly identified based on threshold."""
        # Calibrate with baseline
        self.scorer.calibrate_threshold(self.baseline, std_multiplier=1.0)
        
        # Create test data with some outliers
        normal_logs = torch.randn(90, 768)
        # Create some "abnormal" logs with larger noise
        abnormal_logs = torch.randn(10, 768) + 5.0  # Offset to increase error
        test_logs = torch.cat([normal_logs, abnormal_logs])
        
        result = self.scorer.score_logs(test_logs)
        
        # Should detect some anomalies
        self.assertGreater(result["n_anomalies"], 0)
    
    def test_score_logs_without_calibration_uses_default(self):
        """Test that scoring works even without explicit calibration."""
        # Set a manual threshold
        self.scorer.threshold = 0.5
        
        test_logs = torch.randn(50, 768)
        result = self.scorer.score_logs(test_logs)
        
        # Should still work
        self.assertIn("n_anomalies", result)
        self.assertGreaterEqual(result["n_anomalies"], 0)


class TestAutoencoderIntegration(unittest.TestCase):
    """Integration tests for full autoencoder pipeline."""
    
    def test_end_to_end_pipeline(self):
        """Test complete pipeline: create model → train → calibrate → score."""
        device = torch.device("cpu")
        
        # 1. Create model
        model = LogAutoencoder(device=device)
        self.assertIsNotNone(model)
        
        # 2. Create scorer
        scorer = AutoencoderScorer(model)
        
        # 3. Create baseline and test data
        baseline = torch.randn(500, 768)
        test_data = torch.randn(100, 768)
        
        #  4. Calibrate
        threshold = scorer.calibrate_threshold(baseline)
        self.assertIsNotNone(threshold)
        
        # 5. Score
        result = scorer.score_logs(test_data)
        
        # Verify results
        self.assertEqual(len(result["scores"]), 100)
        self.assertGreaterEqual(result["n_anomalies"], 0)
        self.assertLessEqual(result["n_anomalies"], 100)


if __name__ == "__main__":
    unittest.main()
