"""
ILE Reinforcement Learning Engine

Minimal contextual bandit engine for adaptive decision-making across ILE domains.
Uses Thompson Sampling for exploration-exploitation balance.

Author: Aetherion Development Team
Date: November 15, 2025
"""

import json
import logging
from collections import defaultdict
from typing import Dict, List, Optional
import numpy as np

logger = logging.getLogger(__name__)


# ============================================================================
# CONTEXTUAL BANDIT ENGINE
# ============================================================================

class RLEngine:
    """
    Contextual bandit engine using Thompson Sampling.
    
    Maintains reward distributions for (context, action) pairs and
    recommends actions based on uncertainty-aware sampling.
    """
    
    def __init__(self, db_manager=None, redis_client=None):
        """
        Initialize RL engine.
        
        Args:
            db_manager: Database manager for persistent storage
            redis_client: Redis client for fast in-memory access
        """
        self.db_manager = db_manager
        self.redis_client = redis_client
        
        # In-memory storage of reward statistics
        # Key: (context_key, action) -> {'successes': int, 'failures': int}
        self.statistics: Dict[tuple, Dict[str, int]] = defaultdict(
            lambda: {'successes': 1, 'failures': 1}  # Prior: Beta(1, 1)
        )
        
        # Track total updates per context
        self.update_counts: Dict[str, int] = defaultdict(int)
        
        logger.info("RL Engine initialized")
    
    def _context_key(self, context: Dict) -> str:
        """
        Convert context dictionary to hashable key.
        
        Args:
            context: Context features
        
        Returns:
            String representation of context
        """
        # Sort keys for consistency
        sorted_items = sorted(context.items())
        return json.dumps(sorted_items, sort_keys=True)
    
    async def update(
        self,
        context: Dict,
        action: str,
        reward: float
    ) -> None:
        """
        Update reward statistics for a (context, action) pair.
        
        Args:
            context: Context features (dict)
            action: Action taken (string)
            reward: Reward received (-1.0 to 1.0, or binary 0/1)
        """
        context_key = self._context_key(context)
        key = (context_key, action)
        
        # Convert reward to success/failure
        # If reward is in [0, 1], treat as probability
        # If reward is in [-1, 1], convert to [0, 1]
        if -1.0 <= reward <= 1.0:
            # Normalize to [0, 1]
            normalized_reward = (reward + 1.0) / 2.0
            
            # Bernoulli sampling: treat as probability of success
            is_success = normalized_reward > 0.5
        else:
            # Binary reward
            is_success = bool(reward)
        
        # Update statistics
        if is_success:
            self.statistics[key]['successes'] += 1
        else:
            self.statistics[key]['failures'] += 1
        
        # Track update count
        self.update_counts[context_key] += 1
        
        # Persist to storage if available
        await self._persist_statistics(context_key, action)
        
        logger.debug(
            f"Updated RL: context={context_key[:50]}..., action={action}, "
            f"reward={reward:.2f}, success={is_success}"
        )
    
    async def best_action(
        self,
        context: Dict,
        candidate_actions: Optional[List[str]] = None
    ) -> str:
        """
        Select best action for given context using Thompson Sampling.
        
        Args:
            context: Context features (dict)
            candidate_actions: List of possible actions (if None, use all seen actions)
        
        Returns:
            Recommended action
        """
        context_key = self._context_key(context)
        
        # Load from storage if needed
        await self._load_statistics_if_needed(context_key)
        
        # Get candidate actions
        if candidate_actions is None:
            # Find all actions seen in this context
            candidate_actions = list(set(
                action for (ctx, action) in self.statistics.keys()
                if ctx == context_key
            ))
        
        if not candidate_actions:
            logger.warning(f"No candidate actions for context: {context}")
            return "default"
        
        # Thompson Sampling: sample from Beta distributions
        sampled_rewards = {}
        
        for action in candidate_actions:
            key = (context_key, action)
            stats = self.statistics[key]
            
            # Sample from Beta(successes, failures)
            alpha = stats['successes']
            beta = stats['failures']
            sampled_reward = np.random.beta(alpha, beta)
            
            sampled_rewards[action] = sampled_reward
        
        # Select action with highest sampled reward
        best_action = max(sampled_rewards, key=sampled_rewards.get)
        
        logger.debug(
            f"Best action for context={context_key[:50]}...: {best_action} "
            f"(sampled rewards: {sampled_rewards})"
        )
        
        return best_action
    
    async def get_action_scores(
        self,
        context: Dict,
        candidate_actions: List[str]
    ) -> Dict[str, float]:
        """
        Get expected reward scores for all candidate actions.
        
        Args:
            context: Context features
            candidate_actions: List of possible actions
        
        Returns:
            Dictionary mapping actions to expected rewards
        """
        context_key = self._context_key(context)
        await self._load_statistics_if_needed(context_key)
        
        scores = {}
        
        for action in candidate_actions:
            key = (context_key, action)
            stats = self.statistics[key]
            
            # Expected value of Beta(alpha, beta) = alpha / (alpha + beta)
            alpha = stats['successes']
            beta = stats['failures']
            expected_reward = alpha / (alpha + beta)
            
            scores[action] = expected_reward
        
        return scores
    
    async def export_policy(self) -> Dict:
        """
        Export complete policy for serialization.
        
        Returns:
            Dictionary representation of policy
        """
        policy = {
            'statistics': {
                f"{ctx}_{action}": stats
                for (ctx, action), stats in self.statistics.items()
            },
            'update_counts': dict(self.update_counts)
        }
        
        return policy
    
    async def import_policy(self, policy: Dict) -> None:
        """
        Import policy from serialized format.
        
        Args:
            policy: Dictionary representation of policy
        """
        # Clear existing statistics
        self.statistics.clear()
        self.update_counts.clear()
        
        # Import statistics
        for key, stats in policy.get('statistics', {}).items():
            # Parse key back to (context_key, action)
            parts = key.rsplit('_', 1)
            if len(parts) == 2:
                context_key, action = parts
                self.statistics[(context_key, action)] = stats
        
        # Import update counts
        self.update_counts.update(policy.get('update_counts', {}))
        
        logger.info(f"Imported policy with {len(self.statistics)} statistics")
    
    async def _persist_statistics(self, context_key: str, action: str) -> None:
        """Persist statistics to Redis/Postgres if available"""
        if not self.redis_client:
            return
        
        try:
            key = (context_key, action)
            stats = self.statistics[key]
            
            # Store in Redis with TTL
            redis_key = f"rl:stats:{context_key}:{action}"
            await self.redis_client.setex(
                redis_key,
                86400,  # 24 hour TTL
                json.dumps(stats)
            )
        except Exception as e:
            logger.error(f"Error persisting RL statistics: {e}")
    
    async def _load_statistics_if_needed(self, context_key: str) -> None:
        """Load statistics from Redis if not in memory"""
        if not self.redis_client:
            return
        
        # Check if we already have stats for this context
        has_stats = any(
            ctx == context_key
            for (ctx, _) in self.statistics.keys()
        )
        
        if has_stats:
            return
        
        try:
            # Load all actions for this context from Redis
            pattern = f"rl:stats:{context_key}:*"
            keys = await self.redis_client.keys(pattern)
            
            for redis_key in keys:
                # Extract action from key
                action = redis_key.split(':')[-1]
                
                # Load statistics
                stats_json = await self.redis_client.get(redis_key)
                if stats_json:
                    stats = json.loads(stats_json)
                    key = (context_key, action)
                    self.statistics[key] = stats
        
        except Exception as e:
            logger.error(f"Error loading RL statistics: {e}")


# ============================================================================
# MULTI-ARMED BANDIT (Simpler Version)
# ============================================================================

class MultiArmedBandit:
    """
    Simpler multi-armed bandit without context.
    Useful for simple action selection.
    """
    
    def __init__(self):
        self.statistics: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {'successes': 1, 'failures': 1}
        )
    
    def update(self, action: str, reward: float) -> None:
        """Update reward for action"""
        is_success = reward > 0
        
        if is_success:
            self.statistics[action]['successes'] += 1
        else:
            self.statistics[action]['failures'] += 1
    
    def best_action(self, candidate_actions: List[str]) -> str:
        """Select best action using Thompson Sampling"""
        if not candidate_actions:
            return "default"
        
        sampled_rewards = {}
        
        for action in candidate_actions:
            stats = self.statistics[action]
            alpha = stats['successes']
            beta = stats['failures']
            sampled_reward = np.random.beta(alpha, beta)
            sampled_rewards[action] = sampled_reward
        
        return max(sampled_rewards, key=sampled_rewards.get)
    
    def get_expected_rewards(self, candidate_actions: List[str]) -> Dict[str, float]:
        """Get expected rewards for actions"""
        rewards = {}
        
        for action in candidate_actions:
            stats = self.statistics[action]
            alpha = stats['successes']
            beta = stats['failures']
            rewards[action] = alpha / (alpha + beta)
        
        return rewards


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        # Test contextual bandit
        rl = RLEngine()
        
        # Simulate learning
        contexts = [
            {"task_type": "underwriting", "complexity": "high"},
            {"task_type": "underwriting", "complexity": "low"},
            {"task_type": "risk_analysis", "complexity": "high"},
        ]
        
        actions = ["model_a", "model_b", "model_c"]
        
        # Simulate some rewards
        for _ in range(100):
            context = contexts[np.random.randint(0, len(contexts))]
            action = actions[np.random.randint(0, len(actions))]
            
            # Simulate reward (model_a is best for underwriting, model_b for risk_analysis)
            if context["task_type"] == "underwriting" and action == "model_a":
                reward = 0.8
            elif context["task_type"] == "risk_analysis" and action == "model_b":
                reward = 0.7
            else:
                reward = 0.3
            
            reward += np.random.normal(0, 0.1)  # Add noise
            reward = np.clip(reward, -1, 1)
            
            await rl.update(context, action, reward)
        
        # Test best action selection
        for context in contexts:
            best = await rl.best_action(context, actions)
            scores = await rl.get_action_scores(context, actions)
            print(f"\nContext: {context}")
            print(f"Best action: {best}")
            print(f"Action scores: {scores}")
        
        # Test policy export/import
        policy = await rl.export_policy()
        print(f"\nPolicy exported: {len(policy['statistics'])} entries")
        
        # Test simple bandit
        print("\n--- Testing Multi-Armed Bandit ---")
        bandit = MultiArmedBandit()
        
        for _ in range(50):
            action = actions[np.random.randint(0, len(actions))]
            reward = 0.7 if action == "model_a" else 0.3
            reward += np.random.normal(0, 0.1)
            bandit.update(action, reward)
        
        best = bandit.best_action(actions)
        rewards = bandit.get_expected_rewards(actions)
        print(f"Best action: {best}")
        print(f"Expected rewards: {rewards}")
        
        print("\n✅ RL Engine test completed!")
    
    asyncio.run(test())
