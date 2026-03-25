"""
BUE-Domain Cortex Integration Bridge
Enhances traditional underwriting with cross-domain civilization intelligence

Adds 4 new fields to BUE underwriting:
1. cross_domain_insights: Insights from related domains
2. hidden_correlations: Non-obvious dependencies
3. systemic_risks: Cascade failure scenarios
4. civilization_risk_score: Overall risk from civilization-level view
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from domain_cortex_v1.0.0_complete.domain_cortex.knowledge_graph.civilization_substrate import (
    CivilizationGraph
)
from domain_cortex_v1.0.0_complete.domain_cortex.synthesis.cross_domain_synthesizer import (
    CrossDomainSynthesizer, CrossDomainQuery, DomainSynthesis
)
from ILE_Complete_Implementation.ile_system.credibility.source_credibility import (
    CredibilityEngine
)


class BUEDomainCortexBridge:
    """
    Bridge between BUE underwriting engine and Domain Cortex
    
    Enhances traditional financial underwriting with cross-domain intelligence
    """
    
    # Mapping of asset types to primary domains
    ASSET_DOMAIN_MAPPING = {
        # Mining & Resources
        "mining_project": "mining_resources",
        "mining": "mining_resources",
        "copper_mine": "mining_resources",
        "lithium_mine": "mining_resources",
        "rare_earth": "mining_resources",
        
        # Energy
        "power_plant": "energy_production",
        "solar_farm": "renewable_energy_tech",
        "wind_farm": "renewable_energy_tech",
        "nuclear_plant": "energy_production",
        "oil_field": "energy_production",
        "gas_field": "energy_production",
        
        # Manufacturing
        "factory": "manufacturing",
        "manufacturing_plant": "manufacturing",
        "production_facility": "manufacturing",
        "semiconductor_fab": "semiconductors_computing",
        
        # Real Estate
        "commercial_real_estate": "real_estate_property",
        "office_building": "real_estate_property",
        "warehouse": "transportation_logistics",
        "data_center": "semiconductors_computing",
        
        # Infrastructure
        "infrastructure_project": "construction_infrastructure",
        "bridge": "construction_infrastructure",
        "highway": "construction_infrastructure",
        "port": "transportation_logistics",
        
        # Technology
        "tech_company": "ai_ml",
        "software_company": "ai_ml",
        "biotech_company": "biotechnology_genomics",
        "pharma_company": "healthcare_lifesciences",
        
        # Agriculture
        "farm": "food_agriculture_water",
        "agricultural_project": "food_agriculture_water",
        "vertical_farm": "food_agriculture_water",
        
        # Default
        "default": "finance_banking"
    }
    
    def __init__(self, synthesizer: CrossDomainSynthesizer):
        """
        Initialize bridge with cross-domain synthesizer
        
        Args:
            synthesizer: CrossDomainSynthesizer instance
        """
        self.synthesizer = synthesizer
    
    def underwrite_with_civilization_context(
        self,
        deal: Dict[str, Any],
        asset_type: str,
        traditional_underwriting_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Enhanced underwriting with civilization intelligence
        
        Args:
            deal: Deal/project details
            asset_type: Type of asset being underwritten
            traditional_underwriting_result: Results from traditional BUE analysis
            
        Returns:
            Enhanced underwriting with 4 new civilization-level fields
        """
        
        # Step 1: Map asset to primary domain
        primary_domain = self._map_asset_to_domain(asset_type)
        
        # Step 2: Identify related domains from deal description
        related_domains = self._identify_related_domains_from_deal(deal)
        
        # Step 3: Build cross-domain query
        query = CrossDomainQuery(
            query_text=self._build_query_text(deal, asset_type),
            primary_domain=primary_domain,
            related_domains=related_domains,
            user_context={
                "stakes": "high",  # Underwriting is always high stakes
                "expertise": "financial",
                "deal_size": deal.get("deal_size", "unknown")
            }
        )
        
        # Step 4: Get cross-domain synthesis
        synthesis = self.synthesizer.analyze_query(query)
        
        # Step 5: Calculate civilization risk score
        civilization_risk_score = self._compute_civilization_risk_score(synthesis)
        
        # Step 6: Merge traditional + civilization results
        if traditional_underwriting_result is None:
            # If no traditional result provided, create minimal structure
            traditional_underwriting_result = {
                "asset_type": asset_type,
                "deal_id": deal.get("deal_id", "unknown"),
                "analysis_timestamp": "simulation_mode"
            }
        
        # Add civilization intelligence fields
        enhanced_result = {
            **traditional_underwriting_result,
            
            # New field 1: Cross-domain insights
            "cross_domain_insights": [
                {
                    "domain": insight.domain_name,
                    "insight_type": insight.insight_type.value,
                    "description": insight.description,
                    "confidence": insight.confidence,
                    "lag_months": insight.lag_months
                }
                for insight in synthesis.cross_domain_insights
            ],
            
            # New field 2: Hidden correlations
            "hidden_correlations": [
                {
                    "from_domain": corr.domain_a,
                    "to_domain": corr.domain_b,
                    "through_domains": corr.intermediaries,
                    "strength": corr.correlation_strength,
                    "description": corr.description,
                    "lag_months": corr.lag_months
                }
                for corr in synthesis.hidden_correlations
            ],
            
            # New field 3: Systemic risks
            "systemic_risks": [
                {
                    "source": risk.source_domain,
                    "affected_domains": risk.affected_domains,
                    "severity": risk.severity,
                    "description": risk.description,
                    "cascade_path": risk.cascade_path
                }
                for risk in synthesis.systemic_risks
            ],
            
            # New field 4: Civilization risk score
            "civilization_risk_score": civilization_risk_score,
            
            # Metadata
            "civilization_analysis": {
                "domains_analyzed": len(synthesis.domains_analyzed),
                "insights_count": len(synthesis.cross_domain_insights),
                "correlations_count": len(synthesis.hidden_correlations),
                "systemic_risks_count": len(synthesis.systemic_risks),
                "credibility_tier": synthesis.credibility_metadata.overall_tier if synthesis.credibility_metadata else None,
                "confidence_score": synthesis.credibility_metadata.confidence_score if synthesis.credibility_metadata else None
            }
        }
        
        return enhanced_result
    
    def _map_asset_to_domain(self, asset_type: str) -> str:
        """Map asset type to primary domain"""
        
        # Normalize asset type
        asset_key = asset_type.lower().replace(" ", "_")
        
        # Check direct mapping
        if asset_key in self.ASSET_DOMAIN_MAPPING:
            return self.ASSET_DOMAIN_MAPPING[asset_key]
        
        # Check partial matches
        for key, domain in self.ASSET_DOMAIN_MAPPING.items():
            if key in asset_key or asset_key in key:
                return domain
        
        # Default to finance
        return self.ASSET_DOMAIN_MAPPING["default"]
    
    def _identify_related_domains_from_deal(self, deal: Dict[str, Any]) -> List[str]:
        """Extract related domains from deal description/details"""
        
        related = []
        
        # Extract from description if present
        description = deal.get("description", "").lower()
        
        # Keyword matching for common domains
        domain_keywords = {
            "energy_production": ["energy", "power", "electricity", "renewable"],
            "mining_resources": ["mining", "copper", "lithium", "minerals"],
            "semiconductors_computing": ["semiconductor", "chip", "computing", "data center"],
            "ai_ml": ["ai", "machine learning", "artificial intelligence"],
            "robotics_automation": ["robot", "automation", "autonomous"],
            "telecommunications": ["telecom", "5g", "network", "wireless"],
            "healthcare_lifesciences": ["healthcare", "medical", "hospital", "pharma"],
            "food_agriculture_water": ["agriculture", "farm", "food", "water"],
            "transportation_logistics": ["transport", "logistics", "shipping", "freight"],
            "construction_infrastructure": ["construction", "infrastructure", "building"],
        }
        
        for domain, keywords in domain_keywords.items():
            if any(keyword in description for keyword in keywords):
                related.append(domain)
        
        # Extract from location (geopolitical considerations)
        location = deal.get("location", "").lower()
        jurisdiction = deal.get("jurisdiction", "").lower()
        
        # If international project, consider geopolitics
        if any(indicator in location + jurisdiction for indicator in ["international", "cross-border", "overseas"]):
            # Geopolitics matters - but we don't have that domain yet
            pass
        
        return related[:3]  # Limit to top 3 to avoid noise
    
    def _build_query_text(self, deal: Dict[str, Any], asset_type: str) -> str:
        """Build natural language query text"""
        
        query = f"Analyze {asset_type} project"
        
        if "description" in deal:
            query += f": {deal['description'][:200]}"  # First 200 chars
        
        if "location" in deal:
            query += f" in {deal['location']}"
        
        return query
    
    def _compute_civilization_risk_score(self, synthesis: DomainSynthesis) -> float:
        """
        Compute overall civilization risk score (0-1, higher = more risk)
        
        Factors:
        - Number of systemic risks
        - Severity of systemic risks
        - Number of high-confidence hidden correlations
        - Credibility of analysis
        """
        
        risk_score = 0.0
        
        # Factor 1: Systemic risk contribution (0-0.5)
        if synthesis.systemic_risks:
            avg_severity = sum(r.severity for r in synthesis.systemic_risks) / len(synthesis.systemic_risks)
            risk_count_factor = min(1.0, len(synthesis.systemic_risks) / 5.0)
            systemic_contribution = avg_severity * risk_count_factor * 0.5
            risk_score += systemic_contribution
        
        # Factor 2: Hidden correlation contribution (0-0.3)
        # More hidden dependencies = more risk of surprises
        if synthesis.hidden_correlations:
            strong_correlations = [c for c in synthesis.hidden_correlations if c.correlation_strength > 0.6]
            correlation_contribution = min(0.3, len(strong_correlations) * 0.1)
            risk_score += correlation_contribution
        
        # Factor 3: Credibility discount (multiply by credibility factor)
        if synthesis.credibility_metadata:
            # Lower tier = less reliable = higher risk adjustment
            tier_risk_multipliers = {1: 0.9, 2: 1.0, 3: 1.2, 4: 1.5}
            tier = synthesis.credibility_metadata.overall_tier
            risk_score *= tier_risk_multipliers.get(tier, 1.0)
        
        # Clamp to 0-1
        return min(1.0, max(0.0, risk_score))
    
    def get_domain_for_asset(self, asset_type: str) -> str:
        """Public method to get primary domain for asset type"""
        return self._map_asset_to_domain(asset_type)
    
    def get_supported_asset_types(self) -> List[str]:
        """Get list of supported asset types"""
        return list(self.ASSET_DOMAIN_MAPPING.keys())
