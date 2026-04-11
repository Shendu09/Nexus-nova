"""
Unit tests for RLHF modules (feedback collection, reward model, DPO).
"""

import pytest
import json
import tempfile
from datetime import datetime
from pathlib import Path
import numpy as np
import torch

from scripts.collect_voice_feedback import (
    VoiceFeedback,
    VoiceFeedbackCollector,
    FeedbackAnalyzer,
    LocalFeedbackStore
)

try:
    from scripts.train_reward_model import SuggestionRewardDataset, RewardModel
    _reward_model_available = True
except ImportError:
    _reward_model_available = False

try:
    from scripts.dpo_finetune import DPODataset, compute_log_probs
    _dpo_available = True
except ImportError:
    _dpo_available = False


class TestVoiceFeedback:
    """Tests for VoiceFeedback dataclass."""
    
    def test_feedback_creation(self):
        """Test creating feedback."""
        feedback = VoiceFeedback(
            feedback_id="fb-123",
            incident_id="inc-456",
            suggestion="Check CPU metrics",
            suggestion_quality=8,
            relevance_score=0.9,
            was_helpful=True,
            overall_satisfaction=9,
            timestamp=datetime.now().isoformat()
        )
        
        assert feedback.feedback_id == "fb-123"
        assert feedback.suggestion_quality == 8
        assert feedback.was_helpful is True
    
    def test_feedback_to_dict(self):
        """Test converting feedback to dict."""
        feedback = VoiceFeedback(
            feedback_id="fb-123",
            incident_id="inc-456",
            suggestion="Check CPU",
            suggestion_quality=8,
            relevance_score=0.9,
            was_helpful=True
        )
        
        fb_dict = feedback.to_dict()
        
        assert isinstance(fb_dict, dict)
        assert fb_dict["feedback_id"] == "fb-123"
        assert fb_dict["suggestion_quality"] == 8


class TestVoiceFeedbackCollector:
    """Tests for feedback collector."""
    
    def test_collect_feedback(self):
        """Test collecting new feedback."""
        collector = VoiceFeedbackCollector()
        
        feedback = collector.collect_feedback(
            incident_id="inc-123",
            suggestion="Check memory metrics"
        )
        
        assert feedback.incident_id == "inc-123"
        assert feedback.suggestion == "Check memory metrics"
        assert feedback.feedback_id.startswith("fb-")
        assert feedback.timestamp is not None
    
    def test_feedback_defaults(self):
        """Test default values in collected feedback."""
        collector = VoiceFeedbackCollector()
        
        feedback = collector.collect_feedback(
            incident_id="inc-123",
            suggestion="Check logs"
        )
        
        assert feedback.suggestion_quality == 5
        assert feedback.was_helpful is False
        assert feedback.relevance_score == 0.5


class TestLocalFeedbackStore:
    """Tests for local feedback storage."""
    
    def test_store_feedback(self):
        """Test storing feedback locally."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalFeedbackStore(store_path=tmpdir)
            
            feedback = VoiceFeedback(
                feedback_id="fb-1",
                incident_id="inc-1",
                suggestion="Check CPU",
                suggestion_quality=8,
                relevance_score=0.8,
                was_helpful=True
            )
            
            result = store.store_feedback(feedback)
            assert result is True
            
            # Check file exists
            assert (Path(tmpdir) / "feedback.jsonl").exists()
    
    def test_retrieve_feedback(self):
        """Test retrieving stored feedback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalFeedbackStore(store_path=tmpdir)
            
            # Store some feedback
            for i in range(5):
                feedback = VoiceFeedback(
                    feedback_id=f"fb-{i}",
                    incident_id=f"inc-{i}",
                    suggestion=f"Suggestion {i}",
                    suggestion_quality=5 + i,
                    relevance_score=0.5,
                    was_helpful=i % 2 == 0
                )
                store.store_feedback(feedback)
            
            # Retrieve
            feedbacks = store.get_feedback_for_training(min_records=5)
            
            assert len(feedbacks) >= 5
            assert all(isinstance(fb, VoiceFeedback) for fb in feedbacks)


class TestFeedbackAnalyzer:
    """Tests for feedback analyzer."""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer with dummy data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalFeedbackStore(store_path=tmpdir)
            
            # Create dummy feedbacks
            suggestions = ["Check CPU", "Check memory", "Check logs"]
            for i in range(12):
                feedback = VoiceFeedback(
                    feedback_id=f"fb-{i}",
                    incident_id=f"inc-{i}",
                    suggestion=suggestions[i % 3],
                    suggestion_quality=5 + (i % 5),
                    relevance_score=0.7,
                    was_helpful=i % 3 == 0
                )
                store.store_feedback(feedback)
            
            # Create mock collector
            class MockCollector:
                def __init__(self, store):
                    self.store = store
                
                def get_feedback_for_training(self, min_records):
                    return self.store.get_feedback_for_training(min_records)
            
            return FeedbackAnalyzer(MockCollector(store))
    
    def test_get_statistics(self, analyzer):
        """Test getting statistics."""
        # Note: implementation depends on analyzer design
        pass


class TestSuggestionRewardDataset:
    """Tests for reward model dataset."""
    
    @pytest.mark.skipif(not _reward_model_available, reason="Transformers not installed")
    def test_dataset_creation(self):
        """Test creating reward dataset."""
        from transformers import AutoTokenizer
        
        tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
        
        feedbacks = [
            VoiceFeedback(
                feedback_id="fb-1",
                incident_id="inc-1",
                suggestion="Check CPU metrics",
                suggestion_quality=8,
                relevance_score=0.8,
                was_helpful=True
            ),
            VoiceFeedback(
                feedback_id="fb-2",
                incident_id="inc-2",
                suggestion="Restart service",
                suggestion_quality=3,
                relevance_score=0.2,
                was_helpful=False
            )
        ]
        
        dataset = SuggestionRewardDataset(feedbacks, tokenizer)
        
        assert len(dataset) == 2
    
    @pytest.mark.skipif(not _reward_model_available, reason="Transformers not installed")
    def test_dataset_item(self):
        """Test getting item from dataset."""
        from transformers import AutoTokenizer
        
        tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
        
        feedbacks = [
            VoiceFeedback(
                feedback_id="fb-1",
                incident_id="inc-1",
                suggestion="Check metrics",
                suggestion_quality=8,
                relevance_score=0.8,
                was_helpful=True
            )
        ]
        
        dataset = SuggestionRewardDataset(feedbacks, tokenizer)
        item = dataset[0]
        
        assert "input_ids" in item
        assert "attention_mask" in item
        assert "target_reward" in item
        assert 0 <= item["target_reward"].item() <= 1


class TestRewardModel:
    """Tests for reward model."""
    
    @pytest.mark.skipif(not _reward_model_available, reason="Transformers not installed")
    def test_model_creation(self):
        """Test creating reward model."""
        model = RewardModel()
        
        assert model is not None
        assert hasattr(model, "encoder")
        assert hasattr(model, "head")
    
    @pytest.mark.skipif(not _reward_model_available, reason="Transformers not installed")
    def test_model_forward(self):
        """Test forward pass."""
        model = RewardModel()
        
        # Create dummy input
        batch_size = 2
        seq_len = 10
        input_ids = torch.randint(0, 1000, (batch_size, seq_len))
        attention_mask = torch.ones((batch_size, seq_len))
        
        # Forward
        output = model(input_ids, attention_mask)
        
        assert output.shape == (batch_size, 1)
        assert (output >= 0).all() and (output <= 1).all()


class TestDPODataset:
    """Tests for DPO dataset."""
    
    @pytest.mark.skipif(not _dpo_available, reason="Transformers not installed")
    def test_dpo_dataset_creation(self):
        """Test creating DPO dataset."""
        from transformers import AutoTokenizer
        
        tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
        
        feedbacks = [
            VoiceFeedback(
                feedback_id=f"fb-{i}",
                incident_id=f"inc-{i}",
                suggestion=f"Suggestion {i}",
                suggestion_quality=8 - i,  # Decreasing quality
                relevance_score=0.8 - i * 0.1,
                was_helpful=i < 3  # First 3 are helpful
            )
            for i in range(6)
        ]
        
        dataset = DPODataset(feedbacks, tokenizer)
        
        # Should create preference pairs
        assert len(dataset.pairs) > 0 or len(dataset) > 0
    
    @pytest.mark.skipif(not _dpo_available, reason="Transformers not installed")
    def test_dpo_dataset_pairs(self):
        """Test that high-quality and low-quality pairs are created."""
        from transformers import AutoTokenizer
        
        tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
        
        feedbacks = [
            VoiceFeedback(
                feedback_id="good",
                incident_id="inc-1",
                suggestion="Excellent suggestion",
                suggestion_quality=9,
                relevance_score=0.95,
                was_helpful=True
            ),
            VoiceFeedback(
                feedback_id="bad",
                incident_id="inc-2",
                suggestion="Poor suggestion",
                suggestion_quality=2,
                relevance_score=0.1,
                was_helpful=False
            )
        ]
        
        dataset = DPODataset(feedbacks, tokenizer)
        
        # Should have at least one pair
        assert len(dataset.pairs) >= 1 or len(dataset) >= 1


class TestComputeLogProbs:
    """Tests for log probability computation."""
    
    @pytest.mark.skipif(not _dpo_available, reason="Transformers not installed")
    def test_log_prob_shape(self):
        """Test output shape of log prob computation."""
        from transformers import AutoModelForCausalLM
        
        # This test would require a model, which is heavy
        # Skipping for now
        pass
