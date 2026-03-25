"""
Domain Agent Router and Registry
Manages the 30 domain agents and routes queries to appropriate domains
"""

import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path
import importlib
import yaml


class DomainRegistry:
    """Registry of all 30 domain agents"""
    
    def __init__(self):
        self.agents: Dict[str, Any] = {}
        self.manifests: Dict[str, Dict] = {}
        self._load_manifests()
    
    def _load_manifests(self):
        """Load all domain manifests"""
        manifest_dir = Path(__file__).parent.parent / "manifests"
        
        # Load individual manifests
        healthcare_path = manifest_dir / "healthcare.yaml"
        if healthcare_path.exists():
            with open(healthcare_path) as f:
                self.manifests["healthcare"] = yaml.safe_load(f)
        
        # Load batch manifests
        for batch_file in ["industries_batch.yaml", "technologies_batch.yaml"]:
            batch_path = manifest_dir / batch_file
            if batch_path.exists():
                with open(batch_path) as f:
                    content = f.read()
                    # Split by --- separator
                    docs = content.split('\n---\n')
                    for doc in docs:
                        if doc.strip():
                            manifest = yaml.safe_load(doc)
                            if manifest and 'domain_name' in manifest:
                                key = manifest['domain_name'].lower().replace(' ', '_').replace('&', 'and')
                                self.manifests[key] = manifest
    
    def register_agent(self, domain_key: str, agent: Any):
        """Register a domain agent"""
        self.agents[domain_key] = agent
    
    def get_agent(self, domain_key: str) -> Optional[Any]:
        """Get a registered domain agent"""
        return self.agents.get(domain_key)
    
    def get_manifest(self, domain_key: str) -> Optional[Dict]:
        """Get domain manifest"""
        return self.manifests.get(domain_key)
    
    def list_domains(self) -> List[str]:
        """List all available domains"""
        return list(self.manifests.keys())
    
    def list_industry_domains(self) -> List[str]:
        """List industry domains"""
        return [
            key for key, manifest in self.manifests.items()
            if manifest.get('domain_type') == 'industry'
        ]
    
    def list_technology_domains(self) -> List[str]:
        """List technology domains"""
        return [
            key for key, manifest in self.manifests.items()
            if manifest.get('domain_type') == 'technology'
        ]


class DomainRouter:
    """Routes queries to appropriate domain agents"""
    
    def __init__(self, registry: DomainRegistry):
        self.registry = registry
    
    async def route_query(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Route query to appropriate domain(s)"""
        # Determine which domain(s) to use
        target_domains = self._determine_domains(query, context)
        
        if not target_domains:
            return {
                "status": "error",
                "message": "Could not determine appropriate domain for query"
            }
        
        # Route to single domain
        if len(target_domains) == 1:
            return await self._route_single(query, target_domains[0], context)
        
        # Route to multiple domains (cross-domain query)
        return await self._route_multiple(query, target_domains, context)
    
    def _determine_domains(self, query: str, context: Optional[Dict]) -> List[str]:
        """Determine which domain(s) should handle the query"""
        target_domains = []
        
        # Check if context specifies domains
        if context and 'domains' in context:
            return context['domains']
        
        # Analyze query to determine domains
        query_lower = query.lower()
        
        # Check each domain's keywords
        for domain_key, manifest in self.registry.manifests.items():
            # Check domain name
            domain_name = manifest.get('domain_name', '').lower()
            if domain_name in query_lower:
                target_domains.append(domain_key)
                continue
            
            # Check key concepts
            if 'ontology' in manifest and 'key_concepts' in manifest['ontology']:
                for concept in manifest['ontology']['key_concepts']:
                    if concept.lower() in query_lower:
                        target_domains.append(domain_key)
                        break
        
        # Default to related domain if none found
        if not target_domains:
            # Simple heuristics
            if any(word in query_lower for word in ['hospital', 'patient', 'drug', 'medical']):
                target_domains.append('healthcare_and_life_sciences')
            elif any(word in query_lower for word in ['cloud', 'aws', 'azure', 'compute']):
                target_domains.append('cloud_computing')
            elif any(word in query_lower for word in ['ai', 'machine learning', 'neural']):
                target_domains.append('ai/ml_systems')
        
        return target_domains
    
    async def _route_single(self, query: str, domain_key: str, context: Optional[Dict]) -> Dict[str, Any]:
        """Route to single domain"""
        agent = self.registry.get_agent(domain_key)
        
        if not agent:
            return {
                "status": "error",
                "message": f"Domain agent '{domain_key}' not registered"
            }
        
        return await agent.analyze(query, context)
    
    async def _route_multiple(self, query: str, domain_keys: List[str], context: Optional[Dict]) -> Dict[str, Any]:
        """Route to multiple domains and synthesize"""
        results = {}
        
        # Query each domain in parallel
        tasks = []
        for domain_key in domain_keys:
            agent = self.registry.get_agent(domain_key)
            if agent:
                tasks.append(agent.analyze(query, context))
        
        domain_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect results
        for domain_key, result in zip(domain_keys, domain_results):
            if isinstance(result, Exception):
                results[domain_key] = {"error": str(result)}
            else:
                results[domain_key] = result
        
        # Synthesize cross-domain results
        synthesis = self._synthesize_cross_domain(results)
        
        return {
            "status": "success",
            "type": "cross_domain",
            "domains": domain_keys,
            "individual_results": results,
            "synthesis": synthesis
        }
    
    def _synthesize_cross_domain(self, results: Dict[str, Dict]) -> Dict[str, Any]:
        """Synthesize results from multiple domains"""
        # Extract insights from all domains
        all_insights = []
        for domain, result in results.items():
            if 'insights' in result:
                all_insights.extend(result['insights'])
            elif 'synthesis' in result and 'insights' in result['synthesis']:
                all_insights.extend(result['synthesis']['insights'])
        
        return {
            "method": "cross_domain_synthesis",
            "num_domains": len(results),
            "combined_insights": all_insights,
            "domains_consulted": list(results.keys())
        }
    
    async def route_to_specific_domain(self, query: str, domain_key: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Route directly to specific domain"""
        return await self._route_single(query, domain_key, context)
    
    def get_domain_info(self, domain_key: str) -> Optional[Dict]:
        """Get information about a domain"""
        manifest = self.registry.get_manifest(domain_key)
        if not manifest:
            return None
        
        return {
            "domain_name": manifest.get('domain_name'),
            "domain_type": manifest.get('domain_type'),
            "description": manifest.get('description'),
            "key_concepts": manifest.get('ontology', {}).get('key_concepts', []),
            "related_domains": manifest.get('related_domains', []),
            "kpis": manifest.get('kpis', [])
        }


class DomainOrchestrator:
    """High-level orchestration for domain cortex"""
    
    def __init__(self):
        self.registry = DomainRegistry()
        self.router = DomainRouter(self.registry)
    
    async def initialize_all_agents(self):
        """Initialize all 30 domain agents"""
        from domain_cortex.base.domain_agent import DomainAgent
        from domain_cortex.base.engine_clients import EngineClientFactory
        
        # Create engine clients
        engine_clients = EngineClientFactory.create_all()
        
        # Initialize each domain
        for domain_key in self.registry.list_domains():
            manifest = self.registry.get_manifest(domain_key)
            if manifest:
                # Create agent (using the appropriate wrapper if it exists)
                agent = await self._create_agent(domain_key, manifest, engine_clients)
                if agent:
                    self.registry.register_agent(domain_key, agent)
        
        print(f"Initialized {len(self.registry.agents)} domain agents")
    
    async def _create_agent(self, domain_key: str, manifest: Dict, engine_clients: Dict) -> Any:
        """Create a domain agent"""
        try:
            # Try to import custom agent wrapper
            module_name = f"domain_cortex.agents.{domain_key}_agent"
            try:
                module = importlib.import_module(module_name)
                agent_class = getattr(module, f"{domain_key.title().replace('_', '')}Agent")
            except (ImportError, AttributeError):
                # Fall back to base DomainAgent
                from domain_cortex.base.domain_agent import DomainAgent
                agent_class = DomainAgent
            
            # Create agent
            manifest_path = f"/home/claude/domain_cortex/manifests/{domain_key}.yaml"
            agent = agent_class(domain_key, manifest_path)
            
            # Set engine clients
            agent.bue_client = engine_clients['bue']
            agent.urpe_client = engine_clients['urpe']
            agent.uie_client = engine_clients['uie']
            agent.udoa_client = engine_clients['udoa']
            agent.ceoa_client = engine_clients['ceoa']
            agent.ile_client = engine_clients['ile']
            
            return agent
        except Exception as e:
            print(f"Error creating agent for {domain_key}: {e}")
            return None
    
    async def query(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Main entry point for domain cortex queries"""
        return await self.router.route_query(query, context)
    
    def list_all_domains(self) -> Dict[str, List[str]]:
        """List all domains organized by type"""
        return {
            "industries": self.registry.list_industry_domains(),
            "technologies": self.registry.list_technology_domains(),
            "total_count": len(self.registry.list_domains())
        }
