"""
Base Domain Agent Template
All 30 Domain Cortex agents inherit from this class
"""

import asyncio
import yaml
from typing import Dict, List, Any, Optional
from datetime import datetime
from abc import ABC, abstractmethod


class DomainAgent(ABC):
    """
    Base class for all Domain Cortex agents
    Provides core functionality for domain specialization, child agent spawning,
    and integration with Aetherion's core engines
    """
    
    def __init__(self, domain_name: str, manifest_path: str):
        self.domain_name = domain_name
        self.manifest = self._load_manifest(manifest_path)
        self.child_agents = []
        self.memory = DomainMemory()
        self.governance_client = GovernanceClient()
        
        # Integration clients
        self.bue_client = None  # Business Underwriting Engine
        self.urpe_client = None  # Universal Risk & Probabilistic Engine
        self.uie_client = None  # Universal Intelligence Engine
        self.udoa_client = None  # Universal Data Orchestration API
        self.ceoa_client = None  # Compute & Energy Orchestration API
        self.ile_client = None  # Internal Learning Engine
        
    def _load_manifest(self, manifest_path: str) -> Dict[str, Any]:
        """Load domain-specific configuration from YAML manifest"""
        with open(manifest_path, 'r') as f:
            return yaml.safe_load(f)
    
    async def analyze(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Main entry point for domain analysis
        """
        # Validate with governance
        governance_check = await self.governance_client.evaluate_query(
            query=query,
            domain=self.domain_name
        )
        
        if not governance_check['approved']:
            return {
                'status': 'blocked',
                'reason': governance_check['reason']
            }
        
        # Determine analysis strategy
        strategy = self._determine_strategy(query, context)
        
        # Execute analysis
        if strategy == 'simple':
            result = await self._simple_analysis(query, context)
        elif strategy == 'multi_engine':
            result = await self._multi_engine_analysis(query, context)
        elif strategy == 'child_agents':
            result = await self._child_agent_analysis(query, context)
        else:
            result = await self._complex_analysis(query, context)
        
        # Record in ILE for meta-learning
        await self.ile_client.record_analysis(
            domain=self.domain_name,
            query=query,
            result=result
        )
        
        return result
    
    def _determine_strategy(self, query: str, context: Optional[Dict]) -> str:
        """Determine optimal analysis strategy based on query complexity"""
        complexity_score = self._assess_complexity(query, context)
        
        if complexity_score < 3:
            return 'simple'
        elif complexity_score < 5:
            return 'multi_engine'
        elif complexity_score < 7:
            return 'child_agents'
        else:
            return 'complex'
    
    def _assess_complexity(self, query: str, context: Optional[Dict]) -> int:
        """Score query complexity from 1-10"""
        score = 1
        
        # Check query length
        if len(query) > 200:
            score += 1
        
        # Check for multi-domain aspects
        if context and 'domains' in context and len(context['domains']) > 1:
            score += 2
        
        # Check manifest for complexity indicators
        if 'high_complexity_keywords' in self.manifest:
            for keyword in self.manifest['high_complexity_keywords']:
                if keyword.lower() in query.lower():
                    score += 1
        
        return min(score, 10)
    
    async def _simple_analysis(self, query: str, context: Optional[Dict]) -> Dict[str, Any]:
        """Direct analysis without spawning child agents"""
        domain_rules = self.manifest.get('rules', {})
        domain_ontology = self.manifest.get('ontology', {})
        
        # Apply domain-specific logic
        analysis = {
            'type': 'simple',
            'domain': self.domain_name,
            'query': query,
            'timestamp': datetime.utcnow().isoformat(),
            'insights': []
        }
        
        # Domain-specific analysis logic goes here
        # This is where manifest-driven intelligence operates
        
        return analysis
    
    async def _multi_engine_analysis(self, query: str, context: Optional[Dict]) -> Dict[str, Any]:
        """Analysis leveraging multiple Aetherion engines"""
        results = {}
        
        # Determine which engines to consult based on manifest
        engine_config = self.manifest.get('engine_preferences', {})
        
        if engine_config.get('use_bue', False):
            results['bue'] = await self.bue_client.analyze(query, self.domain_name)
        
        if engine_config.get('use_urpe', False):
            results['urpe'] = await self.urpe_client.analyze(query, self.domain_name)
        
        if engine_config.get('use_udoa', False):
            results['udoa'] = await self.udoa_client.query(
                query=query,
                domain_filter=self.domain_name
            )
        
        # Synthesize results
        synthesis = await self._synthesize_multi_engine(results)
        
        return {
            'type': 'multi_engine',
            'domain': self.domain_name,
            'engine_results': results,
            'synthesis': synthesis,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def _child_agent_analysis(self, query: str, context: Optional[Dict]) -> Dict[str, Any]:
        """Analysis using spawned child agents"""
        # Decompose query into sub-tasks
        sub_tasks = self._decompose_query(query)
        
        # Spawn child agents
        child_results = []
        for task in sub_tasks:
            child = await self.spawn_child_agent(task)
            result = await child.execute()
            child_results.append(result)
            await self.prune_child_agent(child)
        
        # Synthesize child results
        synthesis = await self._synthesize_child_results(child_results)
        
        return {
            'type': 'child_agent',
            'domain': self.domain_name,
            'num_children': len(child_results),
            'child_results': child_results,
            'synthesis': synthesis,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def _complex_analysis(self, query: str, context: Optional[Dict]) -> Dict[str, Any]:
        """Complex analysis combining all approaches"""
        # Use multi-engine analysis
        engine_results = await self._multi_engine_analysis(query, context)
        
        # Use child agents for specialized tasks
        child_results = await self._child_agent_analysis(query, context)
        
        # Cross-domain consultation if needed
        related_domains = self.manifest.get('related_domains', [])
        domain_results = []
        
        for domain in related_domains:
            domain_agent = await self._get_domain_agent(domain)
            result = await domain_agent.consult(query, self.domain_name)
            domain_results.append(result)
        
        # Final synthesis
        final_synthesis = await self._synthesize_complex(
            engine_results=engine_results,
            child_results=child_results,
            domain_results=domain_results
        )
        
        return {
            'type': 'complex',
            'domain': self.domain_name,
            'synthesis': final_synthesis,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _decompose_query(self, query: str) -> List[str]:
        """Break query into sub-tasks for child agents"""
        # Domain-specific decomposition logic
        sub_tasks = []
        
        decomposition_rules = self.manifest.get('decomposition_rules', [])
        
        # Apply manifest-driven decomposition
        for rule in decomposition_rules:
            if rule['trigger'] in query.lower():
                sub_tasks.extend(rule['sub_tasks'])
        
        # If no rules matched, create generic decomposition
        if not sub_tasks:
            sub_tasks = [
                f"Analyze {query} from {aspect} perspective"
                for aspect in ['technical', 'business', 'risk', 'opportunity']
            ]
        
        return sub_tasks
    
    async def spawn_child_agent(self, task: str) -> 'ChildDomainAgent':
        """Create a child agent for specific task"""
        child = ChildDomainAgent(
            parent=self,
            task=task,
            domain_name=self.domain_name
        )
        self.child_agents.append(child)
        return child
    
    async def prune_child_agent(self, child: 'ChildDomainAgent'):
        """Remove completed child agent"""
        if child in self.child_agents:
            self.child_agents.remove(child)
    
    async def _synthesize_multi_engine(self, results: Dict) -> Dict[str, Any]:
        """Synthesize results from multiple engines"""
        # Use UIE for synthesis
        if self.uie_client:
            return await self.uie_client.synthesize(
                domain=self.domain_name,
                inputs=results
            )
        
        # Fallback: simple aggregation
        return {
            'method': 'aggregation',
            'summary': 'Combined insights from multiple engines',
            'results': results
        }
    
    async def _synthesize_child_results(self, results: List[Dict]) -> Dict[str, Any]:
        """Synthesize results from child agents"""
        return {
            'method': 'child_synthesis',
            'num_children': len(results),
            'combined_insights': self._combine_insights(results)
        }
    
    async def _synthesize_complex(self, **kwargs) -> Dict[str, Any]:
        """Final synthesis for complex analysis"""
        # Use UIE for comprehensive synthesis
        if self.uie_client:
            return await self.uie_client.synthesize_complex(
                domain=self.domain_name,
                **kwargs
            )
        
        return {
            'method': 'complex_synthesis',
            'inputs': kwargs
        }
    
    def _combine_insights(self, results: List[Dict]) -> List[str]:
        """Extract and combine insights from results"""
        insights = []
        for result in results:
            if 'insights' in result:
                insights.extend(result['insights'])
        return insights
    
    async def consult(self, query: str, requesting_domain: str) -> Dict[str, Any]:
        """Handle consultation request from another domain agent"""
        # Lightweight analysis for cross-domain consultation
        return {
            'domain': self.domain_name,
            'requesting_domain': requesting_domain,
            'consultation': await self._simple_analysis(query, None)
        }
    
    async def _get_domain_agent(self, domain_name: str) -> 'DomainAgent':
        """Get another domain agent for consultation"""
        # This would connect to the domain registry
        pass
    
    def get_ontology(self) -> Dict[str, Any]:
        """Return domain ontology from manifest"""
        return self.manifest.get('ontology', {})
    
    def get_rules(self) -> Dict[str, Any]:
        """Return domain rules from manifest"""
        return self.manifest.get('rules', {})
    
    def get_kpis(self) -> List[str]:
        """Return domain KPIs from manifest"""
        return self.manifest.get('kpis', [])


class ChildDomainAgent:
    """
    Lightweight child agent for specific sub-tasks
    Acts as a synaptic connection in the neural fabric
    """
    
    def __init__(self, parent: DomainAgent, task: str, domain_name: str):
        self.parent = parent
        self.task = task
        self.domain_name = domain_name
        self.result = None
    
    async def execute(self) -> Dict[str, Any]:
        """Execute the assigned task"""
        # Validate with governance (inherited from parent)
        governance_check = await self.parent.governance_client.evaluate_child_task(
            task=self.task,
            parent_domain=self.domain_name
        )
        
        if not governance_check['approved']:
            return {
                'status': 'blocked',
                'reason': governance_check['reason']
            }
        
        # Execute task
        self.result = {
            'task': self.task,
            'domain': self.domain_name,
            'insights': await self._execute_task(),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return self.result
    
    async def _execute_task(self) -> List[str]:
        """Actual task execution logic"""
        # This is where the specialized child agent logic goes
        # Child agents are micro-reasoners focused on specific aspects
        
        insights = []
        
        # Example: Risk assessment child
        if 'risk' in self.task.lower():
            insights.append(f"Risk analysis for {self.domain_name}")
        
        # Example: Opportunity identification child
        if 'opportunity' in self.task.lower():
            insights.append(f"Opportunity identification for {self.domain_name}")
        
        return insights


class DomainMemory:
    """Memory system for domain agents"""
    
    def __init__(self):
        self.short_term = []
        self.long_term = {}
        self.patterns = []
    
    def store(self, key: str, value: Any):
        """Store in memory"""
        self.long_term[key] = value
    
    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve from memory"""
        return self.long_term.get(key)
    
    def add_pattern(self, pattern: Dict):
        """Store learned pattern"""
        self.patterns.append(pattern)


class GovernanceClient:
    """Client for Constitutional Governance integration"""
    
    async def evaluate_query(self, query: str, domain: str) -> Dict[str, Any]:
        """Evaluate query against constitutional governance"""
        # This would connect to Aetherion's Constitutional Governance
        return {
            'approved': True,
            'benefit_score': 85,
            'harm_score': 10,
            'reason': 'Query approved'
        }
    
    async def evaluate_child_task(self, task: str, parent_domain: str) -> Dict[str, Any]:
        """Evaluate child agent task"""
        return {
            'approved': True,
            'reason': 'Task approved'
        }
