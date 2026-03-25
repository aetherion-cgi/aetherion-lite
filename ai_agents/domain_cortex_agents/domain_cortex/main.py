"""
Domain Cortex - Main Entry Point
Launch all 30 AI agents for Aetherion's Domain Cortex
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from domain_cortex.base.router import DomainOrchestrator
import json


async def main():
    """Main entry point"""
    print("=" * 70)
    print("AETHERION DOMAIN CORTEX")
    print("30 AI Agents Across 15 Industries + 15 Technologies")
    print("=" * 70)
    print()
    
    # Initialize orchestrator
    print("Initializing Domain Orchestrator...")
    orchestrator = DomainOrchestrator()
    
    # Initialize all 30 agents
    print("Loading 30 domain agents...")
    await orchestrator.initialize_all_agents()
    print()
    
    # List all domains
    domains = orchestrator.list_all_domains()
    print(f"✓ Loaded {domains['total_count']} domain agents")
    print(f"  - {len(domains['industries'])} Industry domains")
    print(f"  - {len(domains['technologies'])} Technology domains")
    print()
    
    # Example queries
    print("=" * 70)
    print("EXAMPLE QUERIES")
    print("=" * 70)
    print()
    
    queries = [
        "Analyze the drug development pipeline for oncology treatments",
        "Evaluate cloud computing cost optimization strategies",
        "Assess cybersecurity risks in healthcare EMR systems"
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n[Query {i}] {query}")
        print("-" * 70)
        
        result = await orchestrator.query(query)
        
        if result.get('status') == 'success':
            print(f"Status: {result['status']}")
            if 'type' in result:
                print(f"Analysis Type: {result['type']}")
            if 'domain' in result:
                print(f"Domain: {result['domain']}")
            if 'domains' in result:
                print(f"Domains Consulted: {', '.join(result['domains'])}")
            
            # Print key insights
            if 'insights' in result:
                print("\nKey Insights:")
                for insight in result['insights'][:3]:
                    print(f"  • {insight}")
            elif 'synthesis' in result and 'combined_insights' in result['synthesis']:
                print("\nSynthesized Insights:")
                for insight in result['synthesis']['combined_insights'][:3]:
                    print(f"  • {insight}")
        else:
            print(f"Status: {result.get('status', 'unknown')}")
            print(f"Message: {result.get('message', 'No message')}")
    
    print()
    print("=" * 70)
    print("DOMAIN CORTEX OPERATIONAL")
    print("=" * 70)
    print()
    print("All 30 domain agents are ready to process queries.")
    print("Integration with Aetherion's core engines (BUE, URPE, UIE, UDOA, CEOA, ILE)")
    print("Constitutional Governance active for all agent operations.")
    print()


async def interactive_mode():
    """Interactive query mode"""
    orchestrator = DomainOrchestrator()
    await orchestrator.initialize_all_agents()
    
    print("\n" + "=" * 70)
    print("DOMAIN CORTEX - INTERACTIVE MODE")
    print("=" * 70)
    print("\nCommands:")
    print("  query: <your question>  - Query the domain cortex")
    print("  list                    - List all domains")
    print("  info: <domain_key>      - Get domain information")
    print("  quit                    - Exit")
    print()
    
    while True:
        try:
            command = input("\n> ").strip()
            
            if not command:
                continue
            
            if command.lower() == 'quit':
                print("Goodbye!")
                break
            
            if command.lower() == 'list':
                domains = orchestrator.list_all_domains()
                print(f"\nIndustry Domains ({len(domains['industries'])}):")
                for domain in sorted(domains['industries']):
                    print(f"  • {domain}")
                print(f"\nTechnology Domains ({len(domains['technologies'])}):")
                for domain in sorted(domains['technologies']):
                    print(f"  • {domain}")
                continue
            
            if command.lower().startswith('info:'):
                domain_key = command[5:].strip()
                info = orchestrator.router.get_domain_info(domain_key)
                if info:
                    print(f"\nDomain: {info['domain_name']}")
                    print(f"Type: {info['domain_type']}")
                    print(f"Description: {info['description']}")
                    print(f"\nKey Concepts: {', '.join(info['key_concepts'][:5])}")
                    if info['related_domains']:
                        print(f"Related Domains: {', '.join(info['related_domains'][:3])}")
                else:
                    print(f"Domain '{domain_key}' not found")
                continue
            
            if command.lower().startswith('query:'):
                query = command[6:].strip()
                if query:
                    print("\nProcessing query...")
                    result = await orchestrator.query(query)
                    print(json.dumps(result, indent=2))
                continue
            
            print("Unknown command. Type 'quit' to exit or 'query: <question>' to ask a question.")
        
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        asyncio.run(interactive_mode())
    else:
        asyncio.run(main())
