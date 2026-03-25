"""
BUE Parent Agent - Core Intelligence Orchestrator

This agent wraps the existing BUE engine (7,500 LOC) and adds:
- Multi-agent coordination
- Child agent spawning
- UDOA/URPE/UIE/Governance integration
- Meta-learning capabilities
- Manifest-driven configuration

Total: ~800 LOC (wraps existing BUE, doesn't replace it)
"""

import uuid
import yaml
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class AnalysisStrategy(Enum):
    """Analysis execution strategies"""
    SIMPLE = "simple"  # Direct BUE analysis only
    ENHANCED = "enhanced"  # BUE + external data
    STRATEGIC = "strategic"  # BUE + URPE context
    COMPREHENSIVE = "comprehensive"  # All engines + child agents
    SPECIALIZED = "specialized"  # Custom child agent configuration


@dataclass
class Analysis:
    """Analysis result from BUE Agent"""
    analysis_id: str
    query: str
    industry: str
    recommendation: str
    risk_score: float
    confidence_score: float
    reasoning_chain: List[Dict[str, Any]]
    child_agent_results: List[Dict[str, Any]] = field(default_factory=list)
    external_data_used: bool = False
    strategic_context: Optional[Dict[str, Any]] = None
    governance_approved: bool = True
    governance_feedback: Optional[Dict[str, Any]] = None
    meta_insights: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ChildAgentSpec:
    """Specification for spawning a child agent"""
    agent_type: str
    priority: int
    required_data: List[str]
    timeout_seconds: int = 30


class BUEParentAgent:
    """
    BUE Parent Agent - Intelligent wrapper around existing BUE engine
    
    Responsibilities:
    - Load industry manifests (YAML configuration)
    - Spawn specialized child agents for complex analyses
    - Coordinate with UDOA, URPE, UIE, Governance, ILE
    - Meta-learning from analysis patterns
    - Constitutional governance integration
    
    Usage:
        agent = BUEParentAgent(manifest="saas.yaml")
        analysis = await agent.analyze(company_data, "Should we invest?")
    """
    
    def __init__(
        self,
        manifest_path: str,
        bue_engine=None,  # Existing BUE engine instance
        udoa_client=None,
        urpe_client=None,
        uie_client=None,
        governance_client=None,
        ile_client=None
    ):
        """
        Initialize BUE Parent Agent
        
        Args:
            manifest_path: Path to industry YAML manifest
            bue_engine: Existing BUE engine instance (keeps all 7,500 LOC intact)
            *_client: Integration clients for other Aetherion components
        """
        self.agent_id = str(uuid.uuid4())
        self.manifest_path = manifest_path
        
        # Load industry configuration from manifest
        self.manifest = self._load_manifest(manifest_path)
        self.industry = self.manifest['industry']
        self.category = self.manifest.get('category', '')
        
        # Connect to existing BUE engine (NO CHANGES to existing code)
        self.bue_engine = bue_engine or self._initialize_bue_engine()
        
        # Connect to other Aetherion components
        self.udoa = udoa_client or self._initialize_udoa()
        self.urpe = urpe_client or self._initialize_urpe()
        self.uie = uie_client or self._initialize_uie()
        self.governance = governance_client or self._initialize_governance()
        self.ile = ile_client or self._initialize_ile()
        
        # Child agent management
        self.active_children: Dict[str, Any] = {}
        self.child_results: List[Dict[str, Any]] = []
        
        # Meta-learning state
        self.analysis_count = 0
        self.success_patterns: Dict[str, float] = {}
        
        print(f"✓ BUE Parent Agent initialized for industry: {self.industry}")
        print(f"  Agent ID: {self.agent_id}")
        print(f"  Strategy: {self.manifest['analysis_strategy'].get('default', 'enhanced')}")
    
    async def analyze(
        self,
        company_data: Dict[str, Any],
        query: str,
        strategy: Optional[AnalysisStrategy] = None
    ) -> Analysis:
        """
        Main intelligence loop - orchestrates entire analysis
        
        This is the PRIMARY method that replaces direct BUE calls
        
        Flow:
        1. Determine analysis strategy from manifest
        2. Spawn child agents if needed
        3. Run existing BUE analysis (untouched)
        4. Get UDOA external data if configured
        5. Get URPE strategic context if configured
        6. Constitutional governance validation
        7. Synthesize all results
        8. Meta-learning feedback to ILE
        
        Args:
            company_data: Company information dict
            query: Analysis question
            strategy: Override default strategy
            
        Returns:
            Analysis object with complete results
        """
        analysis_id = str(uuid.uuid4())
        reasoning_chain = []
        
        # Step 1: Determine strategy
        if strategy is None:
            strategy = self._determine_strategy(query, company_data)
        
        print(f"\n🧠 BUE Agent Analysis Starting")
        print(f"   Query: {query}")
        print(f"   Industry: {self.industry}")
        print(f"   Strategy: {strategy.value}")
        
        # Step 2: Spawn child agents if strategy requires
        child_results = []
        if self._requires_child_agents(strategy, query):
            print(f"   Spawning child agents...")
            children = await self._spawn_child_agents(query, company_data)
            child_results = await self._run_child_agents(children, company_data)
            reasoning_chain.append({
                "step": "child_agents",
                "count": len(children),
                "results": [r['summary'] for r in child_results]
            })
        
        # Step 3: Run existing BUE analysis (CORE ENGINE - UNTOUCHED)
        print(f"   Running BUE core analysis...")
        bue_result = await self._run_bue_analysis(company_data, query)
        reasoning_chain.append({
            "step": "bue_core",
            "risk_score": bue_result.get('risk_score'),
            "recommendation": bue_result.get('recommendation')
        })
        
        # Step 4: UDOA external data (if manifest requires)
        external_data = None
        if self.manifest['analysis_strategy'].get('requires_external_data', False):
            print(f"   Fetching external data via UDOA...")
            external_data = await self._fetch_external_data(company_data)
            bue_result = self._enrich_with_external(bue_result, external_data)
            reasoning_chain.append({
                "step": "external_data",
                "sources": len(external_data) if external_data else 0
            })
        
        # Step 5: URPE strategic context (if manifest requires)
        strategic_context = None
        if self.manifest['analysis_strategy'].get('requires_strategic_context', False):
            print(f"   Getting strategic context from URPE...")
            strategic_context = await self._get_strategic_context(company_data, query)
            bue_result = self._add_strategic_context(bue_result, strategic_context)
            reasoning_chain.append({
                "step": "strategic_context",
                "insights": len(strategic_context.get('insights', [])) if strategic_context else 0
            })
        
        # Step 6: Constitutional Governance validation
        print(f"   Validating with Constitutional Governance...")
        governance_decision = await self._validate_governance(
            bue_result,
            company_data,
            query
        )
        
        if not governance_decision['approved']:
            print(f"   ⚠️  Governance requires refinement")
            bue_result = await self._refine_with_governance(
                bue_result,
                governance_decision
            )
        
        reasoning_chain.append({
            "step": "governance",
            "approved": governance_decision['approved'],
            "benefit_score": governance_decision.get('benefit_score'),
            "harm_score": governance_decision.get('harm_score')
        })
        
        # Step 7: Synthesize everything into final analysis
        print(f"   Synthesizing final analysis...")
        final_analysis = await self._synthesize_results(
            bue_core=bue_result,
            children=child_results,
            external=external_data,
            strategic=strategic_context,
            governance=governance_decision,
            query=query,
            company_data=company_data
        )
        
        # Step 8: Meta-learning - send pattern to ILE
        print(f"   Recording pattern to ILE...")
        await self._record_meta_learning({
            "analysis_id": analysis_id,
            "query_type": self._classify_query(query),
            "industry": self.industry,
            "strategy": strategy.value,
            "child_agents_used": len(child_results),
            "external_data_used": external_data is not None,
            "strategic_context_used": strategic_context is not None,
            "governance_approved": governance_decision['approved'],
            "confidence_score": final_analysis.confidence_score
        })
        
        # Build complete Analysis object
        analysis = Analysis(
            analysis_id=analysis_id,
            query=query,
            industry=self.industry,
            recommendation=final_analysis.recommendation,
            risk_score=final_analysis.risk_score,
            confidence_score=final_analysis.confidence_score,
            reasoning_chain=reasoning_chain,
            child_agent_results=child_results,
            external_data_used=external_data is not None,
            strategic_context=strategic_context,
            governance_approved=governance_decision['approved'],
            governance_feedback=governance_decision.get('feedback'),
            meta_insights=None  # Will be populated by ILE over time
        )
        
        self.analysis_count += 1
        print(f"✓ Analysis complete (ID: {analysis_id[:8]}...)")
        print(f"  Recommendation: {analysis.recommendation[:100]}...")
        print(f"  Confidence: {analysis.confidence_score:.1%}")
        
        return analysis
    
    async def _spawn_child_agents(
        self,
        query: str,
        company_data: Dict[str, Any]
    ) -> List[Any]:
        """
        Create specialized child agents based on query and manifest
        
        Child agents are ephemeral micro-reasoners that handle
        specific aspects of the analysis
        """
        from .bue_child_agent import BUEChildAgent
        
        child_specs = self._determine_needed_children(query)
        children = []
        
        for spec in child_specs:
            child = BUEChildAgent(
                agent_type=spec.agent_type,
                manifest_subset=self.manifest.get(spec.agent_type, {}),
                parent_context=self._get_context(),
                bue_engine=self.bue_engine
            )
            children.append(child)
            self.active_children[child.agent_id] = child
        
        return children
    
    async def _run_child_agents(
        self,
        children: List[Any],
        company_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Execute all child agents in parallel
        """
        tasks = [child.analyze(company_data) for child in children]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out failures, log them
        valid_results = []
        for child, result in zip(children, results):
            if isinstance(result, Exception):
                print(f"   ⚠️  Child agent {child.agent_type} failed: {result}")
            else:
                valid_results.append(result)
        
        return valid_results
    
    async def _run_bue_analysis(
        self,
        company_data: Dict[str, Any],
        query: str
    ) -> Dict[str, Any]:
        """
        Call existing BUE engine - NO CHANGES to existing code
        
        This keeps all 7,500 LOC of existing BUE completely intact
        """
        # Existing BUE engine call (simplified interface)
        result = await self.bue_engine.analyze(
            company_data=company_data,
            industry=self.industry,
            metrics=self.manifest['metrics'],
            risk_factors=self.manifest['risk_factors']
        )
        
        return result
    
    async def _fetch_external_data(
        self,
        company_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch market/industry data via UDOA
        """
        try:
            data = await self.udoa.discover(
                industries=[f"IND:{self.industry}"],
                software_categories=[self.category] if self.category else [],
                filters={"company_name": company_data.get('name')}
            )
            return data
        except Exception as e:
            print(f"   ⚠️  External data fetch failed: {e}")
            return None
    
    async def _get_strategic_context(
        self,
        company_data: Dict[str, Any],
        query: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get geopolitical/strategic context from URPE
        """
        try:
            context = await self.urpe.analyze(
                query=f"Strategic landscape for {self.industry} in {company_data.get('geography', 'global')}",
                depth=3
            )
            return context
        except Exception as e:
            print(f"   ⚠️  Strategic context fetch failed: {e}")
            return None
    
    async def _validate_governance(
        self,
        analysis_result: Dict[str, Any],
        company_data: Dict[str, Any],
        query: str
    ) -> Dict[str, Any]:
        """
        Constitutional governance validation
        """
        decision = await self.governance.evaluate(
            action="business_analysis_recommendation",
            context={
                "industry": self.industry,
                "risk_score": analysis_result.get('risk_score'),
                "recommendation": analysis_result.get('recommendation'),
                "company": company_data.get('name'),
                "query": query
            }
        )
        return decision
    
    async def _refine_with_governance(
        self,
        analysis_result: Dict[str, Any],
        governance_decision: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Refine analysis based on governance feedback
        """
        # Apply governance constraints
        feedback = governance_decision.get('feedback', {})
        
        # Example refinements
        if 'reduce_risk_score' in feedback:
            analysis_result['risk_score'] *= 0.8
        
        if 'add_stakeholder_considerations' in feedback:
            analysis_result['stakeholder_impact'] = feedback['stakeholder_considerations']
        
        if 'require_human_review' in feedback:
            analysis_result['requires_human_approval'] = True
        
        return analysis_result
    
    async def _synthesize_results(
        self,
        bue_core: Dict[str, Any],
        children: List[Dict[str, Any]],
        external: Optional[Dict[str, Any]],
        strategic: Optional[Dict[str, Any]],
        governance: Dict[str, Any],
        query: str,
        company_data: Dict[str, Any]
    ) -> Any:
        """
        Synthesize all results into coherent final analysis
        
        This is where UIE integration would happen for narrative generation
        """
        # Simple synthesis logic (could be enhanced with UIE)
        @dataclass
        class FinalAnalysis:
            recommendation: str
            risk_score: float
            confidence_score: float
        
        # Weight different sources
        base_confidence = 0.7
        
        if children:
            base_confidence += 0.1  # Child agents increase confidence
        if external:
            base_confidence += 0.1  # External data validation
        if strategic:
            base_confidence += 0.05  # Strategic context
        if governance['approved']:
            base_confidence += 0.05  # Governance approval
        
        confidence = min(base_confidence, 0.95)
        
        # Build recommendation
        recommendation = bue_core['recommendation']
        
        if children:
            child_insights = [c.get('key_insight', '') for c in children]
            recommendation += f"\n\nAdditional insights: {'; '.join(child_insights)}"
        
        if strategic:
            recommendation += f"\n\nStrategic context: {strategic.get('summary', '')}"
        
        if not governance['approved']:
            recommendation += f"\n\n⚠️  Governance requirements: {governance.get('feedback', {}).get('requirements', 'Additional review needed')}"
        
        return FinalAnalysis(
            recommendation=recommendation,
            risk_score=bue_core.get('risk_score', 0.5),
            confidence_score=confidence
        )
    
    async def _record_meta_learning(self, pattern: Dict[str, Any]) -> None:
        """
        Send analysis pattern to ILE for meta-learning
        """
        try:
            await self.ile.record_pattern({
                "agent_type": "bue_parent",
                "agent_id": self.agent_id,
                "industry": self.industry,
                "pattern": pattern,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"   ⚠️  Meta-learning recording failed: {e}")
    
    def _determine_strategy(
        self,
        query: str,
        company_data: Dict[str, Any]
    ) -> AnalysisStrategy:
        """
        Determine optimal analysis strategy based on query and manifest
        """
        default = self.manifest['analysis_strategy'].get('default', 'enhanced')
        
        # Map string to enum
        strategy_map = {
            'simple': AnalysisStrategy.SIMPLE,
            'enhanced': AnalysisStrategy.ENHANCED,
            'strategic': AnalysisStrategy.STRATEGIC,
            'comprehensive': AnalysisStrategy.COMPREHENSIVE,
            'specialized': AnalysisStrategy.SPECIALIZED
        }
        
        return strategy_map.get(default, AnalysisStrategy.ENHANCED)
    
    def _requires_child_agents(
        self,
        strategy: AnalysisStrategy,
        query: str
    ) -> bool:
        """
        Determine if child agents are needed
        """
        if strategy == AnalysisStrategy.SIMPLE:
            return False
        
        child_specs = self.manifest['analysis_strategy'].get('child_agents_needed', [])
        return len(child_specs) > 0
    
    def _determine_needed_children(self, query: str) -> List[ChildAgentSpec]:
        """
        Determine which child agents to spawn based on query
        """
        needed = self.manifest['analysis_strategy'].get('child_agents_needed', [])
        
        specs = []
        for agent_type in needed:
            specs.append(ChildAgentSpec(
                agent_type=agent_type,
                priority=1,
                required_data=[],
                timeout_seconds=30
            ))
        
        return specs
    
    def _classify_query(self, query: str) -> str:
        """
        Classify query type for meta-learning
        """
        query_lower = query.lower()
        
        if 'invest' in query_lower or 'acquisition' in query_lower:
            return 'investment_decision'
        elif 'risk' in query_lower:
            return 'risk_assessment'
        elif 'market' in query_lower:
            return 'market_analysis'
        elif 'compete' in query_lower or 'competitor' in query_lower:
            return 'competitive_analysis'
        else:
            return 'general_analysis'
    
    def _enrich_with_external(
        self,
        bue_result: Dict[str, Any],
        external_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enrich BUE results with external data
        """
        if external_data:
            bue_result['market_data'] = external_data
            bue_result['data_sources'] = ['UDOA', 'market_intelligence']
        return bue_result
    
    def _add_strategic_context(
        self,
        bue_result: Dict[str, Any],
        strategic_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add strategic context from URPE
        """
        if strategic_context:
            bue_result['strategic_context'] = strategic_context
            bue_result['geopolitical_risks'] = strategic_context.get('risks', [])
        return bue_result
    
    def _get_context(self) -> Dict[str, Any]:
        """
        Get current agent context for child agents
        """
        return {
            "parent_id": self.agent_id,
            "industry": self.industry,
            "manifest": self.manifest,
            "analysis_count": self.analysis_count
        }
    
    def _load_manifest(self, manifest_path: str) -> Dict[str, Any]:
        """
        Load industry manifest from YAML file
        """
        try:
            with open(manifest_path, 'r') as f:
                manifest = yaml.safe_load(f)
            return manifest
        except FileNotFoundError:
            print(f"⚠️  Manifest not found: {manifest_path}")
            return self._get_default_manifest()
    
    def _get_default_manifest(self) -> Dict[str, Any]:
        """
        Return default manifest if file not found
        """
        return {
            "industry": "Unknown",
            "category": "",
            "analysis_strategy": {
                "default": "enhanced",
                "requires_external_data": False,
                "requires_strategic_context": False,
                "child_agents_needed": []
            },
            "metrics": {"critical": []},
            "risk_factors": {"high_priority": []}
        }
    
    def _initialize_bue_engine(self):
        """Initialize existing BUE engine - placeholder"""
        # This would connect to actual BUE engine
        class MockBUE:
            async def analyze(self, **kwargs):
                return {
                    "recommendation": "Based on analysis...",
                    "risk_score": 0.45,
                    "confidence": 0.82
                }
        return MockBUE()
    
    def _initialize_udoa(self):
        """Initialize UDOA client - placeholder"""
        class MockUDOA:
            async def discover(self, **kwargs):
                return {"market_data": "sample"}
        return MockUDOA()
    
    def _initialize_urpe(self):
        """Initialize URPE client - placeholder"""
        class MockURPE:
            async def analyze(self, **kwargs):
                return {"summary": "Strategic context"}
        return MockURPE()
    
    def _initialize_uie(self):
        """Initialize UIE client - placeholder"""
        class MockUIE:
            async def synthesize(self, **kwargs):
                return {"narrative": "Synthesis"}
        return MockUIE()
    
    def _initialize_governance(self):
        """Initialize Governance client - placeholder"""
        class MockGovernance:
            async def evaluate(self, **kwargs):
                return {
                    "approved": True,
                    "benefit_score": 75,
                    "harm_score": 20
                }
        return MockGovernance()
    
    def _initialize_ile(self):
        """Initialize ILE client - placeholder"""
        class MockILE:
            async def record_pattern(self, **kwargs):
                pass
        return MockILE()


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def main():
        # Initialize agent with SaaS manifest
        agent = BUEParentAgent(manifest_path="manifests/saas.yaml")
        
        # Sample company data
        company = {
            "name": "Example SaaS Co",
            "arr": "$15M",
            "growth_rate": "120%",
            "nrr": "115%",
            "burn_rate": "$1.5M/month",
            "geography": "US"
        }
        
        # Run analysis
        analysis = await agent.analyze(
            company_data=company,
            query="Should we invest $5M Series A?"
        )
        
        print(f"\n📊 Final Analysis:")
        print(f"   Recommendation: {analysis.recommendation[:200]}...")
        print(f"   Risk Score: {analysis.risk_score:.2f}")
        print(f"   Confidence: {analysis.confidence_score:.1%}")
        print(f"   Governance Approved: {analysis.governance_approved}")
        print(f"   Child Agents Used: {len(analysis.child_agent_results)}")
    
    asyncio.run(main())
