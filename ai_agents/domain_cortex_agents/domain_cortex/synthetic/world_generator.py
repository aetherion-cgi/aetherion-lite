"""
Synthetic Ecosystem Generator
Creates realistic but fictional scenarios for Domain Cortex agents to train on
"""

import random
from typing import Dict, Any, List
from datetime import datetime, timedelta
import uuid


class SyntheticCompanyGenerator:
    """Generate synthetic companies"""
    
    COMPANY_PREFIXES = [
        "Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Theta", "Omega",
        "Nova", "Stellar", "Quantum", "Nexus", "Apex", "Vertex", "Prime", "Peak"
    ]
    
    COMPANY_SUFFIXES = [
        "Systems", "Technologies", "Solutions", "Industries", "Dynamics", "Innovations",
        "Labs", "Group", "Corp", "Enterprises", "Holdings", "Partners"
    ]
    
    def __init__(self, domain: str):
        self.domain = domain
    
    def generate(self, count: int = 10) -> List[Dict[str, Any]]:
        """Generate synthetic companies for the domain"""
        companies = []
        
        for i in range(count):
            company = {
                "id": str(uuid.uuid4()),
                "name": self._generate_name(),
                "domain": self.domain,
                "revenue": random.randint(1_000_000, 1_000_000_000),
                "employees": random.randint(50, 50_000),
                "founded": random.randint(1990, 2023),
                "stage": random.choice(["startup", "growth", "mature", "declining"]),
                "characteristics": self._generate_characteristics(),
                "risks": self._generate_risks(),
                "opportunities": self._generate_opportunities()
            }
            companies.append(company)
        
        return companies
    
    def _generate_name(self) -> str:
        """Generate company name"""
        prefix = random.choice(self.COMPANY_PREFIXES)
        suffix = random.choice(self.COMPANY_SUFFIXES)
        return f"{prefix} {suffix}"
    
    def _generate_characteristics(self) -> List[str]:
        """Generate company characteristics"""
        all_chars = [
            "high_growth", "profitable", "cash_flow_positive", "debt_heavy",
            "patent_portfolio", "strong_brand", "weak_moat", "network_effects",
            "platform_model", "subscription_revenue", "hardware_intensive",
            "software_focused", "R&D_heavy", "low_margin", "high_margin"
        ]
        return random.sample(all_chars, k=random.randint(3, 6))
    
    def _generate_risks(self) -> List[str]:
        """Generate company risks"""
        all_risks = [
            "market_competition", "regulatory_uncertainty", "technology_disruption",
            "supply_chain_vulnerability", "key_person_dependency", "cybersecurity_exposure",
            "geopolitical_risk", "customer_concentration", "talent_retention"
        ]
        return random.sample(all_risks, k=random.randint(2, 4))
    
    def _generate_opportunities(self) -> List[str]:
        """Generate company opportunities"""
        all_opps = [
            "market_expansion", "product_diversification", "strategic_partnerships",
            "technology_adoption", "international_growth", "M&A_target",
            "cost_reduction", "pricing_power", "platform_expansion"
        ]
        return random.sample(all_opps, k=random.randint(2, 4))


class SyntheticMarketGenerator:
    """Generate synthetic market conditions"""
    
    def generate(self, years: int = 10) -> List[Dict[str, Any]]:
        """Generate market cycles"""
        cycles = []
        
        base_growth = 3.0
        for year in range(years):
            # Add cyclical variation
            cycle_factor = random.uniform(-2.0, 4.0)
            growth = base_growth + cycle_factor
            
            cycle = {
                "year": 2024 + year,
                "gdp_growth": round(growth, 2),
                "inflation": round(random.uniform(1.5, 4.5), 2),
                "interest_rate": round(random.uniform(0.5, 6.0), 2),
                "market_sentiment": random.choice(["bullish", "neutral", "bearish"]),
                "crisis_events": self._generate_crisis_events()
            }
            cycles.append(cycle)
        
        return cycles
    
    def _generate_crisis_events(self) -> List[str]:
        """Generate potential crisis events"""
        if random.random() < 0.3:  # 30% chance of crisis
            possible_crises = [
                "pandemic", "financial_crisis", "trade_war", "tech_bubble_burst",
                "energy_shock", "geopolitical_conflict", "regulatory_crackdown"
            ]
            return [random.choice(possible_crises)]
        return []


class SyntheticGeopoliticalGenerator:
    """Generate synthetic geopolitical scenarios"""
    
    ACTORS = ["US", "China", "EU", "India", "Russia", "Japan", "UK", "Brazil"]
    
    TENSIONS = [
        "technology_sovereignty", "trade_disputes", "territorial_disputes",
        "cyber_warfare", "space_competition", "rare_earth_minerals",
        "AI_dominance", "energy_independence", "currency_wars"
    ]
    
    def generate(self, complexity: int = 5) -> Dict[str, Any]:
        """Generate geopolitical landscape"""
        actors = random.sample(self.ACTORS, k=random.randint(3, 6))
        tensions = random.sample(self.TENSIONS, k=min(complexity, len(self.TENSIONS)))
        
        return {
            "actors": actors,
            "tensions": tensions,
            "alliances": self._generate_alliances(actors),
            "conflicts": self._generate_conflicts(actors, tensions),
            "stability_score": random.randint(40, 90)
        }
    
    def _generate_alliances(self, actors: List[str]) -> List[Dict[str, Any]]:
        """Generate alliances between actors"""
        alliances = []
        for i in range(random.randint(1, 3)):
            alliance_members = random.sample(actors, k=random.randint(2, 4))
            alliances.append({
                "members": alliance_members,
                "type": random.choice(["trade", "military", "technology"]),
                "strength": random.randint(50, 95)
            })
        return alliances
    
    def _generate_conflicts(self, actors: List[str], tensions: List[str]) -> List[Dict[str, Any]]:
        """Generate conflicts"""
        conflicts = []
        for tension in tensions[:2]:  # Focus on top 2 tensions
            parties = random.sample(actors, k=2)
            conflicts.append({
                "parties": parties,
                "issue": tension,
                "severity": random.randint(30, 85),
                "probability_escalation": random.randint(10, 60)
            })
        return conflicts


class SyntheticSupplyChainGenerator:
    """Generate synthetic supply chain networks"""
    
    def generate(self, companies: List[Dict], complexity: int = 5) -> Dict[str, Any]:
        """Generate supply chain dependencies"""
        # Create dependency graph
        dependencies = []
        
        for _ in range(complexity * 2):
            supplier = random.choice(companies)
            customer = random.choice([c for c in companies if c['id'] != supplier['id']])
            
            dependencies.append({
                "supplier": supplier['name'],
                "customer": customer['name'],
                "dependency_level": random.choice(["low", "medium", "high", "critical"]),
                "geographic_risk": random.choice(["low", "medium", "high"]),
                "alternative_sources": random.randint(0, 5)
            })
        
        return {
            "dependencies": dependencies,
            "chokepoints": self._identify_chokepoints(dependencies),
            "resilience_score": random.randint(50, 90)
        }
    
    def _identify_chokepoints(self, dependencies: List[Dict]) -> List[str]:
        """Identify supply chain chokepoints"""
        # Companies that appear frequently as suppliers
        suppliers = [d['supplier'] for d in dependencies]
        chokepoints = []
        
        for supplier in set(suppliers):
            if suppliers.count(supplier) >= 3:
                chokepoints.append(supplier)
        
        return chokepoints


class SyntheticEcosystemGenerator:
    """Main synthetic ecosystem generator"""
    
    def __init__(self):
        self.company_gen = None
        self.market_gen = SyntheticMarketGenerator()
        self.geo_gen = SyntheticGeopoliticalGenerator()
        self.supply_gen = SyntheticSupplyChainGenerator()
    
    def generate_complete_ecosystem(
        self, 
        domain: str, 
        complexity_level: int = 5
    ) -> Dict[str, Any]:
        """Generate complete synthetic ecosystem for training"""
        
        # Generate companies
        self.company_gen = SyntheticCompanyGenerator(domain)
        company_count = 10 * complexity_level
        companies = self.company_gen.generate(company_count)
        
        # Generate market conditions
        market_cycles = self.market_gen.generate(years=10)
        
        # Generate geopolitical landscape
        geopolitics = self.geo_gen.generate(complexity_level)
        
        # Generate supply chains
        supply_chains = self.supply_gen.generate(companies, complexity_level)
        
        # Generate crisis scenarios
        crisis_events = self._generate_crisis_scenarios(complexity_level)
        
        ecosystem = {
            "domain": domain,
            "complexity_level": complexity_level,
            "generated_at": datetime.utcnow().isoformat(),
            "companies": companies,
            "market_cycles": market_cycles,
            "geopolitics": geopolitics,
            "supply_chains": supply_chains,
            "crisis_scenarios": crisis_events,
            "statistics": {
                "total_companies": len(companies),
                "years_simulated": len(market_cycles),
                "geopolitical_actors": len(geopolitics['actors']),
                "supply_dependencies": len(supply_chains['dependencies'])
            }
        }
        
        return ecosystem
    
    def _generate_crisis_scenarios(self, complexity: int) -> List[Dict[str, Any]]:
        """Generate black swan events"""
        scenarios = []
        
        crisis_types = [
            "pandemic", "financial_crisis", "technology_disruption",
            "climate_event", "cyber_attack", "geopolitical_conflict",
            "supply_shock", "regulatory_change"
        ]
        
        for i in range(complexity):
            scenario = {
                "type": random.choice(crisis_types),
                "severity": random.randint(50, 95),
                "probability": random.uniform(0.01, 0.15),
                "impact_sectors": random.sample(
                    ["finance", "healthcare", "energy", "technology", "manufacturing"],
                    k=random.randint(2, 4)
                ),
                "duration_months": random.randint(3, 24)
            }
            scenarios.append(scenario)
        
        return scenarios
    
    def generate_training_batch(
        self, 
        domain: str, 
        num_ecosystems: int = 10,
        complexity_range: tuple = (3, 7)
    ) -> List[Dict[str, Any]]:
        """Generate batch of training ecosystems with progressive difficulty"""
        
        ecosystems = []
        
        for i in range(num_ecosystems):
            # Progressive difficulty
            complexity = random.randint(*complexity_range)
            ecosystem = self.generate_complete_ecosystem(domain, complexity)
            ecosystems.append(ecosystem)
        
        return ecosystems
