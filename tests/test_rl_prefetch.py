"""
Unit tests for RL-based prefetch module.
"""

import pytest
import numpy as np
from datetime import datetime
import json
import tempfile
from pathlib import Path

from nexus.models.rl_prefetch import (
    LinUCBAgent,
    ContextFeatures,
    RLPrefetchStrategy,
    ContextBuilder,
    Action
)


class TestContextFeatures:
    """Tests for context vector."""
    
    def test_context_creation(self):
        """Test creating context."""
        context = ContextFeatures(
            alarm_type_idx=0,
            severity_idx=2,
            service_idx=5,
            hour_of_day=0.5,
            day_of_week=0.3,
            is_business_hours=1.0
        )
        
        assert context.alarm_type_idx == 0
        assert context.severity_idx == 2
        assert context.is_business_hours == 1.0
    
    def test_context_to_vector(self):
        """Test converting context to vector."""
        context = ContextFeatures(
            alarm_type_idx=1,
            severity_idx=2,
            service_idx=5,
            hour_of_day=0.5,
            day_of_week=0.3,
            is_business_hours=1.0
        )
        
        vector = context.to_vector()
        
        assert isinstance(vector, np.ndarray)
        assert len(vector) == 6
        assert vector.dtype == np.float32
        assert all(0 <= v <= 1 for v in vector)


class TestAction:
    """Tests for Action dataclass."""
    
    def test_action_creation(self):
        """Test creating action."""
        action = Action(
            action_id=0,
            name="test_action",
            description="Test action",
            estimated_cost=1.5,
            estimated_latency_ms=200
        )
        
        assert action.action_id == 0
        assert action.name == "test_action"
        assert action.estimated_cost == 1.5


class TestLinUCBAgent:
    """Tests for LinUCB agent."""
    
    @pytest.fixture
    def agent(self):
        """Create agent instance."""
        return LinUCBAgent(alpha=0.1, lambda_reg=1.0)
    
    def test_init(self, agent):
        """Test initialization."""
        assert agent.NUM_ACTIONS == 8
        assert agent.CONTEXT_DIM == 6
        assert agent.alpha == 0.1
        assert agent.lambda_reg == 1.0
        assert agent.interaction_count == 0
    
    def test_actions_defined(self, agent):
        """Test that all actions are defined."""
        assert len(agent.ACTIONS) == 8
        
        action_names = set(a.name for a in agent.ACTIONS)
        assert "cpu_metrics" in action_names
        assert "memory_metrics" in action_names
        assert "recent_logs" in action_names
    
    def test_select_action(self, agent):
        """Test action selection."""
        context = ContextFeatures(
            alarm_type_idx=0,
            severity_idx=1,
            service_idx=3,
            hour_of_day=0.5,
            day_of_week=0.3,
            is_business_hours=1.0
        )
        
        action_id, ucb = agent.select_action(context)
        
        assert 0 <= action_id < agent.NUM_ACTIONS
        assert isinstance(ucb, float)
    
    def test_update(self, agent):
        """Test agent update with reward."""
        context = ContextFeatures(
            alarm_type_idx=1,
            severity_idx=2,
            service_idx=5,
            hour_of_day=0.7,
            day_of_week=0.4,
            is_business_hours=1.0
        )
        
        # Update agent
        agent.update(action_id=3, context=context, reward=0.8)
        
        assert agent.interaction_count == 1
        assert agent.total_reward == 0.8
    
    def test_multiple_updates(self, agent):
        """Test multiple updates."""
        contexts = [
            ContextFeatures(0, 0, i, 0.5, 0.3, 1.0)
            for i in range(5)
        ]
        
        for i, context in enumerate(contexts):
            reward = 0.5 + 0.1 * i
            agent.update(action_id=i % 8, context=context, reward=reward)
        
        assert agent.interaction_count == 5
        expected_total = sum(0.5 + 0.1 * i for i in range(5))
        assert np.isclose(agent.total_reward, expected_total)
    
    def test_get_action_details(self, agent):
        """Test getting action details."""
        action = agent.get_action_details(0)
        
        assert isinstance(action, Action)
        assert action.action_id == 0
        assert action.name == "cpu_metrics"
    
    def test_save_and_load(self, agent):
        """Test saving and loading agent."""
        # Train agent slightly
        context = ContextFeatures(0, 1, 2, 0.5, 0.3, 1.0)
        agent.update(0, context, 0.7)
        agent.update(1, context, 0.5)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Save
            agent.save(tmpdir)
            
            assert (Path(tmpdir) / "linucb_agent.json").exists()
            
            # Load
            loaded_agent = LinUCBAgent.load(tmpdir)
            
            # Verify state
            assert loaded_agent.interaction_count == agent.interaction_count
            assert np.isclose(loaded_agent.total_reward, agent.total_reward)
            assert loaded_agent.alpha == agent.alpha


class TestRLPrefetchStrategy:
    """Tests for RL prefetch strategy."""
    
    @pytest.fixture
    def strategy(self):
        """Create strategy instance."""
        agent = LinUCBAgent()
        return RLPrefetchStrategy(agent)
    
    def test_compute_prefetch_plan(self, strategy):
        """Test computing prefetch plan."""
        context = ContextFeatures(0, 1, 2, 0.5, 0.3, 1.0)
        
        plan = strategy.compute_prefetch_plan(context, budget_actions=3)
        
        assert isinstance(plan, list)
        assert len(plan) <= 3
        assert all(0 <= a < 8 for a in plan)
    
    def test_prefetch_plan_budget_respected(self, strategy):
        """Test that budget is respected."""
        context = ContextFeatures(0, 1, 2, 0.5, 0.3, 1.0)
        
        for budget in [1, 2, 3, 5]:
            plan = strategy.compute_prefetch_plan(context, budget_actions=budget)
            assert len(plan) <= budget
    
    def test_apply_feedback(self, strategy):
        """Test feedback application."""
        context = ContextFeatures(0, 1, 2, 0.5, 0.3, 1.0)
        actions = [0, 2, 4]
        helpful_flags = [True, False, True]
        
        # Apply feedback
        strategy.apply_feedback(
            actions,
            context,
            feedback_score=0.7,
            action_helpful_flags=helpful_flags
        )
        
        assert strategy.agent.interaction_count == 3
    
    def test_get_performance_stats(self, strategy):
        """Test getting performance stats."""
        context = ContextFeatures(0, 1, 2, 0.5, 0.3, 1.0)
        
        # Do some training
        strategy.apply_feedback([0, 1], context, 0.8)
        strategy.apply_feedback([2, 3], context, 0.6)
        
        stats = strategy.get_performance_stats()
        
        assert "total_interactions" in stats
        assert "average_reward" in stats
        assert stats["total_interactions"] == 2


class TestContextBuilder:
    """Tests for context builder."""
    
    @pytest.fixture
    def builder(self):
        """Create builder instance."""
        return ContextBuilder()
    
    def test_build_context(self, builder):
        """Test building context."""
        timestamp = datetime(2024, 1, 15, 14, 30)  # 2:30 PM, Monday
        
        context = builder.build_context(
            alarm_type="HighCPU",
            severity="HIGH",
            service="api-gateway",
            timestamp=timestamp
        )
        
        assert isinstance(context, ContextFeatures)
        assert context.alarm_type_idx == ContextBuilder.ALARM_TYPES["HighCPU"]
        assert context.severity_idx == ContextBuilder.SEVERITIES["HIGH"]
    
    def test_service_id_consistency(self, builder):
        """Test that same service gets same ID."""
        service = "payment-service"
        
        context1 = builder.build_context("HighCPU", "WARNING", service)
        context2 = builder.build_context("HighMemory", "HIGH", service)
        
        assert context1.service_idx == context2.service_idx
    
    def test_business_hours_detection(self, builder):
        """Test business hours detection."""
        # Business hours: 9 AM - 6 PM
        business_time = datetime(2024, 1, 15, 14, 0)
        off_time = datetime(2024, 1, 15, 22, 0)
        
        context_business = builder.build_context(
            "HighCPU", "WARNING", "service", business_time
        )
        context_off = builder.build_context(
            "HighCPU", "WARNING", "service", off_time
        )
        
        assert context_business.is_business_hours == 1.0
        assert context_off.is_business_hours == 0.0
    
    def test_alarm_type_mapping(self, builder):
        """Test alarm type to index mapping."""
        for alarm_type in ContextBuilder.ALARM_TYPES.keys():
            context = builder.build_context(alarm_type, "WARNING", "service")
            expected_idx = ContextBuilder.ALARM_TYPES[alarm_type]
            assert context.alarm_type_idx == expected_idx


class TestLinUCBIntegration:
    """Integration tests for LinUCB workflow."""
    
    def test_full_training_cycle(self):
        """Test complete training cycle."""
        agent = LinUCBAgent(alpha=0.1)
        strategy = RLPrefetchStrategy(agent)
        
        # Simulate 10 incidents
        for episode in range(10):
            context = ContextFeatures(
                alarm_type_idx=episode % 8,
                severity_idx=episode % 4,
                service_idx=episode % 5,
                hour_of_day=0.5,
                day_of_week=0.3,
                is_business_hours=1.0
            )
            
            # Plan prefetch
            plan = strategy.compute_prefetch_plan(context, budget_actions=3)
            
            # Simulate feedback
            helpful_flags = [episode % 2 == 0] * len(plan)
            feedback = 0.5 + 0.1 * episode
            
            strategy.apply_feedback(plan, context, feedback, helpful_flags)
        
        # Verify training occurred
        assert agent.interaction_count == 10
        stats = strategy.get_performance_stats()
        assert stats["average_reward"] > 0
