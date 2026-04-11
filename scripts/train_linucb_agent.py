"""
Training script for LinUCB RL prefetch agent.

This script simulates incidents and feedback to train the RL agent
on optimal prefetch policies. In production, this would use historical
incident data and engineer feedback from voice calls.

Usage:
    python scripts/train_linucb_agent.py \
        --episodes 1000 \
        --output_dir ./models/linucb_agents \
        --seed 42

Data Source:
    - Simulated incidents with realistic patterns
    - Random feedback to simulate engineer satisfaction
    - In production: DynamoDB incident records + voice call ratings
"""

import logging
import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple
import random
import numpy as np

from nexus.models.rl_prefetch import (
    LinUCBAgent,
    RLPrefetchStrategy,
    ContextBuilder,
    ContextFeatures
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IncidentSimulator:
    """Simulate incidents with realistic patterns."""
    
    ALARM_TYPES = list(ContextBuilder.ALARM_TYPES.keys())
    SEVERITIES = list(ContextBuilder.SEVERITIES.keys())
    SERVICES = [
        "api-gateway",
        "user-service",
        "order-service",
        "payment-service",
        "inventory-service",
        "catalog-service",
        "notification-service",
        "analytics-service"
    ]
    
    def __init__(self, seed: int = 42):
        """Initialize simulator."""
        random.seed(seed)
        np.random.seed(seed)
    
    def sample_incident(self) -> Tuple[ContextFeatures, List[Tuple[int, bool]]]:
        """
        Sample a realistic incident.
        
        Returns:
            Tuple of (context, true_action_helpfulness)
            where true_action_helpfulness is list of (action_id, was_helpful)
        """
        # Biased sampling toward realistic patterns
        if random.random() < 0.3:
            # HighCPU with high severity is more common
            alarm_type = "HighCPU"
            severity = random.choice(["WARNING", "HIGH", "CRITICAL"])
        elif random.random() < 0.25:
            # Memory issues during business hours
            alarm_type = "HighMemory"
            severity = random.choice(["HIGH", "CRITICAL"])
        elif random.random() < 0.2:
            # Error rate spikes
            alarm_type = "HighErrorRate"
            severity = random.choice(["WARNING", "HIGH"])
        else:
            # Other issues
            alarm_type = random.choice(self.ALARM_TYPES)
            severity = random.choice(self.SEVERITIES)
        
        service = random.choice(self.SERVICES)
        
        # Random timestamp (could bias toward business hours)
        days_back = random.randint(0, 30)
        timestamp = datetime.now() - timedelta(days=days_back)
        timestamp = timestamp.replace(hour=random.randint(0, 23), minute=0, second=0)
        
        # Build context
        context_builder = ContextBuilder()
        context = context_builder.build_context(alarm_type, severity, service, timestamp)
        
        # Simulate which actions would be helpful
        # Use simple heuristic: higher severity = more actions helpful
        severity_idx = ContextBuilder.SEVERITIES[severity]
        num_helpful = max(1, severity_idx + 1)
        
        helpful_actions = []
        for action_id in range(8):
            # Bias certain actions as more helpful
            if action_id == 0 and alarm_type == "HighCPU":  # CPU query for CPU alarm
                is_helpful = True
            elif action_id == 1 and alarm_type == "HighMemory":  # Memory query for memory alarm
                is_helpful = True
            elif action_id == 2 and alarm_type == "HighErrorRate":  # Error rate query
                is_helpful = True
            elif action_id == 4:  # Recent logs always somewhat helpful
                is_helpful = random.random() < 0.7
            elif action_id == 5 and alarm_type == "DependencyFailure":  # Dependencies for dep issues
                is_helpful = True
            else:
                is_helpful = random.random() < 0.3
            
            if is_helpful:
                helpful_actions.append((action_id, True))
            elif random.random() < 0.2:  # Some false positives
                helpful_actions.append((action_id, False))
        
        if not helpful_actions:
            helpful_actions = [(random.randint(0, 7), True)]
        
        return context, helpful_actions
    
    def sample_feedback_score(self, num_helpful_actions: int) -> float:
        """
        Sample engineer feedback score based on helpful actions.
        
        Args:
            num_helpful_actions: Number of actions that were helpful
            
        Returns:
            Feedback score 0-1
        """
        # More helpful actions = higher satisfaction
        base_score = num_helpful_actions / 8.0
        noise = np.random.normal(0, 0.1)
        score = np.clip(base_score + noise, 0, 1)
        return float(score)


class LinUCBTrainer:
    """Trainer for LinUCB agent."""
    
    def __init__(self, alpha: float = 0.1, lambda_reg: float = 1.0):
        """Initialize trainer."""
        self.agent = LinUCBAgent(alpha=alpha, lambda_reg=lambda_reg)
        self.strategy = RLPrefetchStrategy(self.agent)
        self.simulator = IncidentSimulator()
        self.training_history = []
    
    def train(self, num_episodes: int = 1000, budget_actions: int = 3):
        """
        Train agent on simulated incidents.
        
        Args:
            num_episodes: Number of training episodes
            budget_actions: Number of actions to select per episode
        """
        logger.info(f"Starting training for {num_episodes} episodes...")
        
        for episode in range(num_episodes):
            # Sample incident
            context, ground_truth_helpful = self.simulator.sample_incident()
            
            # Agent selects actions
            selected_actions = self.strategy.compute_prefetch_plan(context, budget_actions)
            
            # Determine help for selected actions
            helpful_map = dict(ground_truth_helpful)
            action_helpful_flags = [
                helpful_map.get(action_id, False)
                for action_id in selected_actions
            ]
            
            # Get feedback score
            num_helpful = sum(action_helpful_flags)
            feedback_score = self.simulator.sample_feedback_score(num_helpful)
            
            # Update agent
            self.strategy.apply_feedback(
                selected_actions,
                context,
                feedback_score,
                action_helpful_flags
            )
            
            # Record history
            self.training_history.append({
                "episode": episode,
                "feedback_score": float(feedback_score),
                "num_helpful": num_helpful,
                "actions_selected": selected_actions
            })
            
            if (episode + 1) % 100 == 0:
                avg_score = np.mean([
                    h["feedback_score"] for h in self.training_history[-100:]
                ])
                logger.info(f"Episode {episode + 1}/{num_episodes} - Avg reward: {avg_score:.3f}")
        
        logger.info("Training complete!")
    
    def save_checkpoint(self, save_path: str):
        """Save trained agent and history."""
        save_path = Path(save_path)
        save_path.mkdir(parents=True, exist_ok=True)
        
        # Save agent
        self.agent.save(str(save_path / "agent"))
        
        # Save training history
        with open(save_path / "training_history.json", "w") as f:
            json.dump(self.training_history, f, indent=2)
        
        # Save summary statistics
        if self.training_history:
            scores = [h["feedback_score"] for h in self.training_history]
            summary = {
                "total_episodes": len(self.training_history),
                "avg_feedback_score": float(np.mean(scores)),
                "max_feedback_score": float(np.max(scores)),
                "min_feedback_score": float(np.min(scores)),
                "std_feedback_score": float(np.std(scores)),
                "agent_interactions": self.agent.interaction_count,
                "agent_total_reward": float(self.agent.total_reward),
            }
            
            with open(save_path / "training_summary.json", "w") as f:
                json.dump(summary, f, indent=2)
        
        logger.info(f"Checkpoint saved to {save_path}")


def main():
    """Main training entry point."""
    parser = argparse.ArgumentParser(
        description="Train LinUCB agent for prefetch optimization"
    )
    parser.add_argument(
        "--episodes",
        type=int,
        default=1000,
        help="Number of training episodes"
    )
    parser.add_argument(
        "--output_dir",
        default="./models/linucb_agents",
        help="Output directory"
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.1,
        help="Exploration parameter"
    )
    parser.add_argument(
        "--lambda",
        type=float,
        default=1.0,
        dest="lambda_reg",
        help="Regularization parameter"
    )
    parser.add_argument(
        "--budget_actions",
        type=int,
        default=3,
        help="Number of actions to select per incident"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed"
    )
    
    args = parser.parse_args()
    
    # Set seeds
    random.seed(args.seed)
    np.random.seed(args.seed)
    
    # Train
    trainer = LinUCBTrainer(alpha=args.alpha, lambda_reg=args.lambda_reg)
    trainer.train(num_episodes=args.episodes, budget_actions=args.budget_actions)
    
    # Save
    trainer.save_checkpoint(args.output_dir)
    
    # Print summary
    stats = trainer.strategy.get_performance_stats()
    logger.info(f"\nFinal Statistics:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")


if __name__ == "__main__":
    main()
