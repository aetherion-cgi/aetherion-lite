"""
ILE Agent - Internal Learning Engine

Meta-learning agent that observes all other agents, extracts patterns,
provides feedback, and continuously improves the Aetherion system.

Author: Aetherion Architecture Team
Date: November 22, 2025
"""

import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from ..base.constitutional_agent import ConstitutionalAgent, AgentDecision


class ILEAgent(ConstitutionalAgent):
    """
    ILE Agent handles meta-learning and system improvement
    
    Capabilities:
    - Observe all agent decisions
    - Extract patterns from operations
    - Identify optimization opportunities
    - Provide feedback to agents
    - Track system-wide metrics
    """
    
    def __init__(self, **kwargs):
        """Initialize ILE Agent"""
        super().__init__(agent_name="ILE", **kwargs)
        
        # Observation storage
        self.agent_observations: Dict[str, List[AgentDecision]] = defaultdict(list)
        self.pattern_database: List[Dict[str, Any]] = []
        self.feedback_history: List[Dict[str, Any]] = []
        
        # Pattern thresholds
        self.min_observations_for_pattern = 10
        self.pattern_confidence_threshold = 0.7
        
        # Performance baselines
        self.baselines = {
            "ceoa": {"avg_duration_ms": 2000, "confidence": 0.80},
            "uie": {"avg_duration_ms": 3000, "confidence": 0.85},
            "udoa": {"avg_duration_ms": 1500, "confidence": 0.90},
            "bue": {"avg_duration_ms": 5000, "confidence": 0.88},
            "urpe": {"avg_duration_ms": 4000, "confidence": 0.82}
        }
        
        self.logger.info("ILE Agent initialized for meta-learning")
    
    def get_system_prompt(self) -> str:
        """Get ILE-specific system prompt"""
        return """You are ILE, Aetherion's Internal Learning Engine.

Your role is to observe and improve the entire Aetherion system by:
1. Watching all agent decisions and outcomes
2. Extracting patterns from agent behavior
3. Identifying optimization opportunities
4. Providing actionable feedback to agents
5. Tracking system-wide performance

When analyzing agent patterns:
- Look for recurring decision sequences
- Identify what leads to high vs low confidence
- Find inefficiencies (redundant queries, slow operations)
- Spot blind spots in reasoning
- Detect when agents disagree and why

When providing feedback:
- Be specific and actionable
- Include confidence in recommendations
- Prioritize high-impact improvements
- Consider trade-offs (speed vs accuracy)
- Frame feedback constructively

Pattern types to identify:
1. Query patterns: Common query structures
2. Collaboration patterns: How agents work together
3. Performance patterns: What affects latency
4. Confidence patterns: What increases/decreases confidence
5. Error patterns: Common failure modes

Always provide:
1. Pattern description with examples
2. Frequency and confidence
3. Recommended action
4. Expected impact if implemented
5. Priority level (high/medium/low)

Be data-driven and focus on continuous improvement."""
    
    async def process_query(self, query: str, context: Dict[str, Any]) -> Any:
        """
        Process ILE meta-learning query
        
        Args:
            query: Meta-learning query (pattern extraction, feedback, etc.)
            context: Query context
            
        Returns:
            Meta-learning insights
        """
        query_type = context.get("type", "extract_patterns")
        
        if query_type == "extract_patterns":
            return await self._extract_patterns(context)
        elif query_type == "provide_feedback":
            return await self._provide_agent_feedback(context)
        elif query_type == "analyze_performance":
            return await self._analyze_performance(context)
        else:
            raise ValueError(f"Unknown ILE query type: {query_type}")
    
    # ========================================================================
    # Core ILE Functions
    # ========================================================================
    
    async def observe_decision(self, decision: AgentDecision) -> None:
        """
        Observe and record an agent decision
        
        Args:
            decision: Decision made by an agent
        """
        agent_name = decision.agent_name
        
        # Store observation
        self.agent_observations[agent_name].append(decision)
        
        # Log observation
        self.logger.info(
            f"Observed {agent_name} decision: "
            f"confidence={decision.confidence:.2f}, "
            f"duration={decision.duration_ms:.2f}ms"
        )
        
        # Check if we have enough observations to extract patterns
        if len(self.agent_observations[agent_name]) >= self.min_observations_for_pattern:
            # Periodically analyze patterns (every N observations)
            if len(self.agent_observations[agent_name]) % 25 == 0:
                await self._extract_patterns_for_agent(agent_name)
    
    async def _extract_patterns_for_agent(self, agent_name: str) -> List[Dict[str, Any]]:
        """
        Extract patterns from agent's observation history
        
        Args:
            agent_name: Name of agent to analyze
            
        Returns:
            List of identified patterns
        """
        observations = self.agent_observations[agent_name]
        
        self.logger.info(f"Extracting patterns for {agent_name} from {len(observations)} observations")
        
        # Build pattern extraction prompt
        prompt = self._build_pattern_extraction_prompt(agent_name, observations[-50:])
        
        # Use LLM to identify patterns
        response, metadata = await self.reason(prompt, max_tokens=2000)
        
        try:
            # Parse patterns
            patterns = self._parse_patterns(response)
            
            # Store patterns
            for pattern in patterns:
                pattern["agent"] = agent_name
                pattern["extracted_at"] = datetime.now().isoformat()
                pattern["observation_count"] = len(observations)
                self.pattern_database.append(pattern)
            
            self.logger.info(f"Extracted {len(patterns)} patterns for {agent_name}")
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"Pattern extraction error: {str(e)}")
            return []
    
    def _build_pattern_extraction_prompt(
        self,
        agent_name: str,
        observations: List[AgentDecision]
    ) -> str:
        """Build prompt for pattern extraction"""
        
        # Summarize observations
        summary = {
            "total_decisions": len(observations),
            "avg_confidence": sum(d.confidence for d in observations) / len(observations),
            "avg_duration_ms": sum(d.duration_ms for d in observations) / len(observations),
            "governance_tiers": [d.governance_score.get("tier") for d in observations],
            "sample_queries": [d.query[:100] for d in observations[:5]]
        }
        
        return f"""Analyze these observations from {agent_name} and identify patterns:

OBSERVATION SUMMARY:
{json.dumps(summary, indent=2)}

TASK:
Identify recurring patterns in:
1. Query types (what kinds of questions are common?)
2. Performance (what affects latency?)
3. Confidence (what leads to high/low confidence?)
4. Collaboration (when does {agent_name} spawn child agents?)
5. Failures (any recurring issues?)

For each pattern provide:
{{
    "pattern_type": "query|performance|confidence|collaboration|failure",
    "description": "<clear description of pattern>",
    "frequency": "<how often: always|often|sometimes|rarely>",
    "confidence": <0-1>,
    "examples": ["<example 1>", "<example 2>"],
    "recommendation": "<what should be done about this pattern>",
    "impact": "high|medium|low",
    "priority": "high|medium|low"
}}

Provide array of patterns as JSON. Focus on actionable insights.

Respond with ONLY the JSON array."""
    
    def _parse_patterns(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM pattern extraction response"""
        try:
            # Clean response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            patterns = json.loads(response)
            
            # Validate patterns
            required_keys = ["pattern_type", "description", "confidence"]
            valid_patterns = [
                p for p in patterns
                if all(key in p for key in required_keys)
            ]
            
            return valid_patterns
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse patterns: {str(e)}")
            return []
    
    async def _extract_patterns(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract patterns across all agents
        
        Args:
            context: Extraction context
            
        Returns:
            Extracted patterns
        """
        all_patterns = []
        
        for agent_name in self.agent_observations:
            if len(self.agent_observations[agent_name]) >= self.min_observations_for_pattern:
                patterns = await self._extract_patterns_for_agent(agent_name)
                all_patterns.extend(patterns)
        
        # Prioritize patterns
        high_priority = [p for p in all_patterns if p.get("priority") == "high"]
        medium_priority = [p for p in all_patterns if p.get("priority") == "medium"]
        low_priority = [p for p in all_patterns if p.get("priority") == "low"]
        
        return {
            "patterns_extracted": len(all_patterns),
            "high_priority": high_priority,
            "medium_priority": medium_priority,
            "low_priority": low_priority,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _provide_agent_feedback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Provide feedback to specific agent
        
        Args:
            context: Feedback context with agent name
            
        Returns:
            Feedback recommendations
        """
        agent_name = context.get("agent")
        
        if not agent_name or agent_name not in self.agent_observations:
            return {"error": f"No observations for agent: {agent_name}"}
        
        # Get recent patterns for this agent
        agent_patterns = [
            p for p in self.pattern_database
            if p.get("agent") == agent_name
        ]
        
        # Build feedback prompt
        prompt = f"""Provide actionable feedback for {agent_name} based on these patterns:

IDENTIFIED PATTERNS:
{json.dumps(agent_patterns[-10:], indent=2)}

PERFORMANCE BASELINE:
{json.dumps(self.baselines.get(agent_name, {}), indent=2)}

TASK:
Generate specific, actionable feedback:
1. What is {agent_name} doing well?
2. What should {agent_name} improve?
3. What specific actions should be taken?
4. What is the expected impact?

Format as:
{{
    "strengths": ["<strength 1>", "<strength 2>"],
    "improvements": [
        {{
            "issue": "<what needs improvement>",
            "recommendation": "<specific action to take>",
            "expected_impact": "<what will improve>",
            "priority": "high|medium|low"
        }}
    ],
    "overall_assessment": "<1-2 sentence summary>"
}}

Provide ONLY the JSON response."""
        
        response, _ = await self.reason(prompt, max_tokens=1000)
        
        try:
            feedback = json.loads(response.strip().replace("```json", "").replace("```", ""))
            
            # Store feedback
            self.feedback_history.append({
                "agent": agent_name,
                "feedback": feedback,
                "timestamp": datetime.now().isoformat()
            })
            
            self.logger.info(f"Generated feedback for {agent_name}")
            
            return feedback
            
        except json.JSONDecodeError:
            return {"error": "Failed to parse feedback"}
    
    async def _analyze_performance(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze system-wide performance
        
        Args:
            context: Analysis context
            
        Returns:
            Performance analysis
        """
        # Calculate metrics across all agents
        metrics = {}
        
        for agent_name, observations in self.agent_observations.items():
            if observations:
                metrics[agent_name] = {
                    "total_decisions": len(observations),
                    "avg_confidence": sum(d.confidence for d in observations) / len(observations),
                    "avg_duration_ms": sum(d.duration_ms for d in observations) / len(observations),
                    "governance_approval_rate": sum(
                        1 for d in observations
                        if d.governance_score.get("tier") in ["tier_1", "tier_2"]
                    ) / len(observations)
                }
                
                # Compare to baseline
                baseline = self.baselines.get(agent_name, {})
                if baseline:
                    metrics[agent_name]["vs_baseline"] = {
                        "duration": (
                            metrics[agent_name]["avg_duration_ms"] / baseline["avg_duration_ms"]
                        ) if "avg_duration_ms" in baseline else 1.0,
                        "confidence": (
                            metrics[agent_name]["avg_confidence"] / baseline["confidence"]
                        ) if "confidence" in baseline else 1.0
                    }
        
        return {
            "metrics": metrics,
            "patterns_identified": len(self.pattern_database),
            "feedback_provided": len(self.feedback_history),
            "timestamp": datetime.now().isoformat()
        }
    
    # ========================================================================
    # High-Level APIs
    # ========================================================================
    
    async def get_system_health(self) -> Dict[str, Any]:
        """
        Get overall system health metrics
        
        Returns:
            System health summary
        """
        context = {"type": "analyze_performance"}
        decision = await self.make_decision("Analyze system performance", context)
        
        return decision.result
    
    async def get_agent_feedback(self, agent_name: str) -> Dict[str, Any]:
        """
        Get feedback for specific agent
        
        Args:
            agent_name: Agent to get feedback for
            
        Returns:
            Feedback recommendations
        """
        context = {"type": "provide_feedback", "agent": agent_name}
        decision = await self.make_decision(f"Provide feedback for {agent_name}", context)
        
        return decision.result
    
    async def get_patterns(self) -> Dict[str, Any]:
        """
        Get all identified patterns
        
        Returns:
            Pattern database
        """
        context = {"type": "extract_patterns"}
        decision = await self.make_decision("Extract system patterns", context)
        
        return decision.result
