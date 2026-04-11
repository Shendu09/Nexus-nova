"""
Evaluation and policy analysis script for LinUCB RL agent.

This script evaluates a trained agent on held-out test incidents
and generates performance reports and policy analysis.

Usage:
    python scripts/evaluate_prefetch_policy.py \
        --agent_path ./models/linucb_agents \
        --num_test_episodes 1000 \
        --output_dir ./results/evaluation
"""

import logging
import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
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


class PolicyEvaluator:
    """Evaluate trained RL policy."""
    
    def __init__(self, agent_path: str):
        """Initialize evaluator with trained agent."""
        self.agent = LinUCBAgent.load(agent_path)
        self.strategy = RLPrefetchStrategy(self.agent)
        self.context_builder = ContextBuilder()
        
        # Evaluation metrics
        self.test_results = []
        self.action_frequencies = np.zeros(8)
        self.action_rewards = np.zeros(8)
    
    def sample_test_incident(self) -> Tuple[ContextFeatures, Dict]:
        """Generate a test incident."""
        alarm_types = list(ContextBuilder.ALARM_TYPES.keys())
        severities = list(ContextBuilder.SEVERITIES.keys())
        services = [
            "api-gateway", "user-service", "order-service",
            "payment-service", "inventory-service"
        ]
        
        alarm_type = random.choice(alarm_types)
        severity = random.choice(severities)
        service = random.choice(services)
        
        context = self.context_builder.build_context(
            alarm_type, severity, service
        )
        
        # Ground truth: which actions are helpful
        ground_truth = {
            "alarm_type": alarm_type,
            "severity": severity,
            "service": service,
        }
        
        return context, ground_truth
    
    def evaluate_on_test_set(self, num_episodes: int = 1000) -> Dict:
        """
        Evaluate policy on test set.
        
        Args:
            num_episodes: Number of test episodes
            
        Returns:
            Evaluation metrics dictionary
        """
        logger.info(f"Evaluating on {num_episodes} test episodes...")
        
        total_reward = 0.0
        total_actions = 0
        
        for episode in range(num_episodes):
            # Sample incident
            context, ground_truth = self.sample_test_incident()
            
            # Get policy action
            plan = self.strategy.compute_prefetch_plan(context, budget_actions=3)
            
            # Simulate feedback (in practice this would come from engineers)
            feedback = self._simulate_feedback(plan, ground_truth)
            
            total_reward += feedback
            total_actions += len(plan)
            
            # Track action frequencies
            for action_id in plan:
                self.action_frequencies[action_id] += 1
                self.action_rewards[action_id] += feedback / len(plan)
            
            self.test_results.append({
                "episode": episode,
                "actions": plan,
                "feedback": feedback,
                "context": {
                    "alarm_type": ground_truth["alarm_type"],
                    "severity": ground_truth["severity"],
                }
            })
            
            if (episode + 1) % 100 == 0:
                current_avg = total_reward / (episode + 1)
                logger.info(f"Episode {episode + 1}/{num_episodes} - Avg reward: {current_avg:.3f}")
        
        avg_reward = total_reward / num_episodes
        avg_actions_selected = total_actions / num_episodes
        
        return {
            "num_episodes": num_episodes,
            "avg_reward": float(avg_reward),
            "avg_actions_per_incident": float(avg_actions_selected),
            "total_reward": float(total_reward),
        }
    
    def _simulate_feedback(self, actions: List[int], ground_truth: Dict) -> float:
        """Simulate engineer feedback for selected actions."""
        alarm_type = ground_truth["alarm_type"]
        
        # Simple heuristic: give higher rewards for relevant actions
        reward = 0.0
        
        for action_id in actions:
            if action_id == 0 and alarm_type == "HighCPU":
                reward += 0.8
            elif action_id == 1 and alarm_type == "HighMemory":
                reward += 0.8
            elif action_id == 2 and alarm_type == "HighErrorRate":
                reward += 0.8
            elif action_id == 4:  # Logs are always somewhat useful
                reward += 0.3
            else:
                reward += 0.1  # Small reward for any action
        
        # Average reward across actions
        return reward / max(len(actions), 1)
    
    def generate_report(self, output_dir: str):
        """Generate comprehensive evaluation report."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Summary metrics
        if self.test_results:
            episode_rewards = [r["feedback"] for r in self.test_results]
            summary = {
                "evaluation_timestamp": datetime.now().isoformat(),
                "num_episodes": len(self.test_results),
                "avg_reward": float(np.mean(episode_rewards)),
                "std_reward": float(np.std(episode_rewards)),
                "min_reward": float(np.min(episode_rewards)),
                "max_reward": float(np.max(episode_rewards)),
                "agent_stats": {
                    "total_interactions": self.agent.interaction_count,
                    "total_training_reward": float(self.agent.total_reward),
                }
            }
        else:
            summary = {"episodes": 0}
        
        with open(output_dir / "evaluation_summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        
        # Action analysis
        total_selections = self.action_frequencies.sum()
        action_analysis = []
        
        for action_id in range(8):
            action = self.agent.get_action_details(action_id)
            freq = self.action_frequencies[action_id]
            selection_rate = freq / total_selections if total_selections > 0 else 0
            avg_reward = self.action_rewards[action_id] / freq if freq > 0 else 0
            
            action_analysis.append({
                "action_id": action_id,
                "name": action.name,
                "description": action.description,
                "total_selections": int(freq),
                "selection_rate": float(selection_rate),
                "avg_reward": float(avg_reward),
                "estimated_cost": action.estimated_cost,
                "estimated_latency_ms": action.estimated_latency_ms
            })
        
        with open(output_dir / "action_analysis.json", "w") as f:
            json.dump(action_analysis, f, indent=2)
        
        # Save raw results
        with open(output_dir / "test_results.json", "w") as f:
            json.dump(self.test_results, f, indent=2)
        
        # Generate text report
        with open(output_dir / "evaluation_report.txt", "w") as f:
            f.write("=" * 70 + "\n")
            f.write("LinUCB Prefetch Policy Evaluation Report\n")
            f.write("=" * 70 + "\n\n")
            
            f.write("Summary Metrics\n")
            f.write("-" * 70 + "\n")
            for key, value in summary.items():
                if key != "agent_stats":
                    f.write(f"{key}: {value}\n")
            
            f.write("\n\nAction Selection Analysis\n")
            f.write("-" * 70 + "\n")
            f.write(f"{'Action':<20} {'Selections':<12} {'Rate':<10} {'Reward':<10}\n")
            f.write("-" * 70 + "\n")
            
            for action_info in action_analysis:
                f.write(
                    f"{action_info['name']:<20} "
                    f"{action_info['total_selections']:<12} "
                    f"{action_info['selection_rate']:<10.2%} "
                    f"{action_info['avg_reward']:<10.3f}\n"
                )
            
            f.write("\n\nRecommendations\n")
            f.write("-" * 70 + "\n")
            
            # Find best and worst actions
            if action_analysis:
                best_action = max(action_analysis, key=lambda x: x["avg_reward"])
                worst_action = min(action_analysis, key=lambda x: x["avg_reward"] if x["total_selections"] > 0 else 1)
                
                f.write(f"Best performing action: {best_action['name']} "
                        f"(Reward: {best_action['avg_reward']:.3f})\n")
                f.write(f"Worst performing action: {worst_action['name']} "
                        f"(Reward: {worst_action['avg_reward']:.3f})\n")
        
        logger.info(f"Evaluation report saved to {output_dir}")


def main():
    """Main evaluation entry point."""
    parser = argparse.ArgumentParser(
        description="Evaluate trained LinUCB prefetch policy"
    )
    parser.add_argument(
        "--agent_path",
        default="./models/linucb_agents",
        help="Path to trained agent"
    )
    parser.add_argument(
        "--num_test_episodes",
        type=int,
        default=1000,
        help="Number of test episodes"
    )
    parser.add_argument(
        "--output_dir",
        default="./results/evaluation",
        help="Output directory for reports"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed"
    )
    
    args = parser.parse_args()
    
    # Set seed
    random.seed(args.seed)
    np.random.seed(args.seed)
    
    # Evaluate
    evaluator = PolicyEvaluator(args.agent_path)
    metrics = evaluator.evaluate_on_test_set(args.num_test_episodes)
    
    # Generate report
    evaluator.generate_report(args.output_dir)
    
    # Print summary
    logger.info("\nEvaluation Summary:")
    for key, value in metrics.items():
        logger.info(f"  {key}: {value}")


if __name__ == "__main__":
    main()
