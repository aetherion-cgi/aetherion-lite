"""
Domain Cortex - Example Usage
Demonstrates key features and capabilities
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from domain_cortex.base.router import DomainOrchestrator
from domain_cortex.synthetic.world_generator import SyntheticEcosystemGenerator


async def example_single_domain_query():
    """Example: Query a single domain"""
    print("\n" + "="*70)
    print("EXAMPLE 1: Single Domain Query")
    print("="*70)
    
    orchestrator = DomainOrchestrator()
    await orchestrator.initialize_all_agents()
    
    query = "Analyze the impact of 5G deployment on hospital operations"
    print(f"\nQuery: {query}")
    print("\nRouting to Healthcare domain...")
    
    result = await orchestrator.query(query)
    
    print(f"\nResult Type: {result.get('type')}")
    print(f"Domain: {result.get('domain')}")
    print(f"Status: {result.get('status')}")
    

async def example_cross_domain_query():
    """Example: Query multiple domains"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Cross-Domain Query")
    print("="*70)
    
    orchestrator = DomainOrchestrator()
    await orchestrator.initialize_all_agents()
    
    query = "How do advances in quantum computing affect cryptography in financial services?"
    print(f"\nQuery: {query}")
    print("\nThis query touches multiple domains:")
    print("  - Advanced Computing & Chips (quantum)")
    print("  - Cybersecurity (cryptography)")
    print("  - Financial Services")
    
    result = await orchestrator.query(query)
    
    if 'domains' in result:
        print(f"\nDomains Consulted: {', '.join(result['domains'])}")
    print(f"Analysis Type: {result.get('type')}")


async def example_synthetic_training():
    """Example: Generate synthetic training ecosystem"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Synthetic Training Ecosystem")
    print("="*70)
    
    generator = SyntheticEcosystemGenerator()
    
    print("\nGenerating synthetic healthcare ecosystem...")
    ecosystem = generator.generate_complete_ecosystem(
        domain="healthcare",
        complexity_level=5
    )
    
    print(f"\nGenerated Ecosystem Statistics:")
    print(f"  Companies: {ecosystem['statistics']['total_companies']}")
    print(f"  Market Years: {ecosystem['statistics']['years_simulated']}")
    print(f"  Geopolitical Actors: {ecosystem['statistics']['geopolitical_actors']}")
    print(f"  Supply Dependencies: {ecosystem['statistics']['supply_dependencies']}")
    
    print(f"\nSample Company:")
    if ecosystem['companies']:
        company = ecosystem['companies'][0]
        print(f"  Name: {company['name']}")
        print(f"  Revenue: ${company['revenue']:,}")
        print(f"  Employees: {company['employees']:,}")
        print(f"  Stage: {company['stage']}")


async def example_list_all_domains():
    """Example: List all available domains"""
    print("\n" + "="*70)
    print("EXAMPLE 4: List All Domains")
    print("="*70)
    
    orchestrator = DomainOrchestrator()
    await orchestrator.initialize_all_agents()
    
    domains = orchestrator.list_all_domains()
    
    print(f"\nTotal Domains: {domains['total_count']}")
    print(f"\nIndustry Domains ({len(domains['industries'])}):")
    for i, domain in enumerate(sorted(domains['industries']), 1):
        manifest = orchestrator.registry.get_manifest(domain)
        name = manifest.get('domain_name', domain) if manifest else domain
        print(f"  {i:2d}. {name}")
    
    print(f"\nTechnology Domains ({len(domains['technologies'])}):")
    for i, domain in enumerate(sorted(domains['technologies']), 1):
        manifest = orchestrator.registry.get_manifest(domain)
        name = manifest.get('domain_name', domain) if manifest else domain
        print(f"  {i:2d}. {name}")


async def run_all_examples():
    """Run all examples"""
    print("\n" + "="*70)
    print("AETHERION DOMAIN CORTEX - EXAMPLES")
    print("="*70)
    
    await example_list_all_domains()
    await example_single_domain_query()
    await example_cross_domain_query()
    await example_synthetic_training()
    
    print("\n" + "="*70)
    print("ALL EXAMPLES COMPLETE")
    print("="*70)
    print("\nFor interactive mode, run: python main.py interactive")
    print()


if __name__ == "__main__":
    asyncio.run(run_all_examples())
