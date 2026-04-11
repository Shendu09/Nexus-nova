"""
Reinforcement Learning-based Pre-fetch Optimization using LinUCB

This module implements a contextual bandit algorithm (LinUCB) to learn
optimal query prefetching strategies from voice call feedback.

The LinUCB algorithm:
- Maintains confidence bounds on query reward estimates
- Explores queries with highest uncertainty
- Exploits queries with highest expected value
- Learns from voice call post-incident ratings

Context features:
- Alarm type (e.g., HighCPU, HighMemory, HighErrorRate)
- Severity (INFO, WARNING, HIGH, CRITICAL)
- Service name
- Time features (hour of day, day of week)

Actions (queries to prefetch):
- Fetch CPU metrics
- Fetch memory metrics
- Fetch error rate metrics
- Fetch latency metrics
- Query recent logs
- Check service dependencies
- Query database performance metrics
- Check DynamoDB throttling status
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ContextFeatures:
    """Context vector for LinUCB algorithm."""
    alarm_type_idx: int      # 0-7: CPU, Memory, ErrorRate, Latency, etc.
    severity_idx: int        # 0-3: INFO, WARNING, HIGH, CRITICAL
    service_idx: int         # 0-N: service identifier
    hour_of_day: float       # 0-23 (normalized to 0-1)
    day_of_week: float       # 0-6 (normalized to 0-1)
    is_business_hours: float # 0 or 1
    
    def to_vector(self) -> np.ndarray:
        """Convert to feature vector for computation."""
        return np.array([
            self.alarm_type_idx / 8.0,
            self.severity_idx / 4.0,
            self.service_idx / 100.0,  # Assume max 100 services
            self.hour_of_day,
            self.day_of_week,
            self.is_business_hours
        ], dtype=np.float32)


@dataclass
class Action:
    """Query action to prefetch."""
    action_id: int
    name: str
    description: str
    estimated_cost: float  # Relative cost estimate
    estimated_latency_ms: float


class LinUCBAgent:
    """
    LinUCB (Linear Upper Confidence Bound) Contextual Bandit Agent.
    
    Learns which queries to prefetch based on context and feedback.
    """
    
    # Action definitions (8 total actions)
    ACTIONS = [
        Action(0, "cpu_metrics", "Fetch CPU utilization metrics", 1.0, 100),
        Action(1, "memory_metrics", "Fetch memory usage metrics", 1.0, 100),
        Action(2, "error_rate", "Fetch error rate metrics", 1.2, 150),
        Action(3, "latency_p99", "Fetch P99 latency metrics", 1.2, 150),
        Action(4, "recent_logs", "Query recent error logs", 2.0, 300),
        Action(5, "dependencies", "Check service dependencies", 1.5, 200),
        Action(6, "database_perf", "Query database performance", 1.8, 250),
        Action(7, "dynamodb_throttle", "Check DynamoDB throttling", 1.0, 120),
    ]
    
    NUM_ACTIONS = len(ACTIONS)
    CONTEXT_DIM = 6  # Number of context features
    
    def __init__(
        self,
        alpha: float = 0.1,  # Exploration/exploitation tradeoff
        lambda_reg: float = 1.0,  # L2 regularization
    ):
        """
        Initialize LinUCB agent.
        
        Args:
            alpha: Exploration parameter (higher = more exploration)
            lambda_reg: Regularization for matrix inversion
        """
        self.alpha = alpha
        self.lambda_reg = lambda_reg
        
        # A_a: Design matrix for each action (context_dim x context_dim)
        self.A = [np.eye(self.CONTEXT_DIM) * lambda_reg for _ in range(self.NUM_ACTIONS)]
        
        # b_a: Cumulative reward vector for each action (context_dim,)
        self.b = [np.zeros(self.CONTEXT_DIM) for _ in range(self.NUM_ACTIONS)]
        
        # Tracking
        self.interaction_count = 0
        self.total_reward = 0.0
    
    def select_action(self, context: ContextFeatures) -> Tuple[int, float]:
        """
        Select action using LinUCB algorithm.
        
        Args:
            context: Context features
            
        Returns:
            Tuple of (action_id, estimated_reward)
        """
        x = context.to_vector()
        
        best_action = 0
        best_ucb = -np.inf
        
        # Compute UCB for each action
        for a in range(self.NUM_ACTIONS):
            # Estimate: theta_a^T * x
            A_inv = np.linalg.inv(self.A[a])
            theta_a = A_inv @ self.b[a]
            estimate = theta_a @ x
            
            # Confidence radius
            confidence = self.alpha * np.sqrt(x @ A_inv @ x)
            
            # UCB = estimate + confidence
            ucb = estimate + confidence
            
            if ucb > best_ucb:
                best_ucb = ucb
                best_action = a
        
        return best_action, float(best_ucb)
    
    def update(
        self,
        action_id: int,
        context: ContextFeatures,
        reward: float
    ):
        """
        Update agent with reward feedback.
        
        Args:
            action_id: Action that was taken
            context: Context when action was taken
            reward: Reward received (0-1, where 1 = excellent)
        """
        x = context.to_vector()
        
        # Update A and b for the chosen action
        self.A[action_id] += np.outer(x, x)
        self.b[action_id] += reward * x
        
        self.interaction_count += 1
        self.total_reward += reward
        
        # Log update
        if self.interaction_count % 10 == 0:
            avg_reward = self.total_reward / self.interaction_count
            logger.info(
                f"LinUCB update #{self.interaction_count}: "
                f"action={action_id}, reward={reward:.3f}, avg_reward={avg_reward:.3f}"
            )
    
    def get_action_details(self, action_id: int) -> Action:
        """Get action details."""
        return self.ACTIONS[action_id]
    
    def save(self, save_path: str):
        """Save agent state to disk."""
        save_path = Path(save_path)
        save_path.mkdir(parents=True, exist_ok=True)
        
        # Convert numpy arrays to lists for JSON serialization
        state = {
            "alpha": self.alpha,
            "lambda_reg": self.lambda_reg,
            "interaction_count": self.interaction_count,
            "total_reward": float(self.total_reward),
            "A": [a.tolist() for a in self.A],
            "b": [b.tolist() for b in self.b],
        }
        
        with open(save_path / "linucb_agent.json", "w") as f:
            json.dump(state, f, indent=2)
        
        logger.info(f"Saved LinUCB agent to {save_path}")
    
    @classmethod
    def load(cls, save_path: str) -> "LinUCBAgent":
        """Load agent state from disk."""
        with open(Path(save_path) / "linucb_agent.json") as f:
            state = json.load(f)
        
        agent = cls(
            alpha=state["alpha"],
            lambda_reg=state["lambda_reg"]
        )
        
        agent.A = [np.array(a) for a in state["A"]]
        agent.b = [np.array(b) for b in state["b"]]
        agent.interaction_count = state["interaction_count"]
        agent.total_reward = state["total_reward"]
        
        logger.info(f"Loaded LinUCB agent from {save_path}")
        return agent


class RLPrefetchStrategy:
    """
    High-level interface for RL-based prefetching strategy.
    """
    
    def __init__(self, agent: LinUCBAgent):
        """Initialize strategy."""
        self.agent = agent
    
    def compute_prefetch_plan(self, context: ContextFeatures, budget_actions: int = 3) -> List[int]:
        """
        Compute prefetch plan using RL policy.
        
        Args:
            context: Context for this incident
            budget_actions: Number of actions to prefetch
            
        Returns:
            List of action IDs to execute
        """
        plan = []
        
        # Select top-k actions using LinUCB
        for _ in range(budget_actions):
            action_id, ucb = self.agent.select_action(context)
            plan.append(action_id)
        
        return sorted(set(plan))[:budget_actions]  # Remove duplicates, respect budget
    
    def apply_feedback(
        self,
        selected_actions: List[int],
        context: ContextFeatures,
        feedback_score: float,
        action_helpful_flags: Optional[List[bool]] = None
    ):
        """
        Apply feedback from engineers to improve policy.
        
        Args:
            selected_actions: Actions that were prefetched
            context: Context from the incident
            feedback_score: Overall satisfaction (0-1)
            action_helpful_flags: Per-action helpfulness (optional)
        """
        if action_helpful_flags is None:
            # Distribute feedback equally among actions
            action_helpful_flags = [True] * len(selected_actions)
        
        for action_id, was_helpful in zip(selected_actions, action_helpful_flags):
            # Reward based on helpfulness and overall feedback
            reward = feedback_score if was_helpful else feedback_score * 0.5
            self.agent.update(action_id, context, reward)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get agent performance statistics."""
        avg_reward = (
            self.agent.total_reward / self.agent.interaction_count
            if self.agent.interaction_count > 0
            else 0.0
        )
        
        return {
            "total_interactions": self.agent.interaction_count,
            "total_reward": float(self.agent.total_reward),
            "average_reward": avg_reward,
            "num_actions": self.NUM_ACTIONS,
            "alpha": self.agent.alpha,
            "lambda": self.agent.lambda_reg,
        }
    
    @property
    def NUM_ACTIONS(self):
        """Number of actions."""
        return self.agent.NUM_ACTIONS


class ContextBuilder:
    """Helper to build context vectors from incident data."""
    
    ALARM_TYPES = {
        "HighCPU": 0,
        "HighMemory": 1,
        "HighErrorRate": 2,
        "HighLatency": 3,
        "ServiceDown": 4,
        "DatabaseIssue": 5,
        "DependencyFailure": 6,
        "UnexpectedBehavior": 7,
    }
    
    SEVERITIES = {
        "INFO": 0,
        "WARNING": 1,
        "HIGH": 2,
        "CRITICAL": 3,
    }
    
    def __init__(self):
        """Initialize builder."""
        self.service_map: Dict[str, int] = {}
        self.next_service_id = 0
    
    def build_context(
        self,
        alarm_type: str,
        severity: str,
        service: str,
        timestamp: Optional[datetime] = None
    ) -> ContextFeatures:
        """
        Build context features from incident data.
        
        Args:
            alarm_type: Type of alarm
            severity: Severity level
            service: Service name
            timestamp: Incident timestamp
            
        Returns:
            ContextFeatures object
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Get or assign service ID
        if service not in self.service_map:
            self.service_map[service] = self.next_service_id
            self.next_service_id += 1
        
        service_id = self.service_map[service]
        
        # Extract time features
        hour = timestamp.hour / 24.0  # 0-1
        day = timestamp.weekday() / 7.0  # 0-1
        is_business_hours = 1.0 if 9 <= timestamp.hour < 18 else 0.0
        
        return ContextFeatures(
            alarm_type_idx=self.ALARM_TYPES.get(alarm_type, 0),
            severity_idx=self.SEVERITIES.get(severity, 0),
            service_idx=service_id,
            hour_of_day=hour,
            day_of_week=day,
            is_business_hours=is_business_hours,
        )
