"""
Source Credibility Engine
Evaluates information quality based on source reputation and domain expertise

Implements 4-tier credibility system:
- Tier 1: Authoritative (Nature, CDC, Federal Reserve, IEEE)
- Tier 2: Established (reputable journals, major institutions)
- Tier 3: Emerging (preprints, new sources, requires verification)
- Tier 4: Unverified (insufficient evidence)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import IntEnum
from datetime import datetime


class CredibilityTier(IntEnum):
    """Source credibility tiers (lower is better)"""
    TIER_1 = 1  # Authoritative: peer-reviewed, government agencies, standards bodies
    TIER_2 = 2  # Established: reputable institutions, industry bodies
    TIER_3 = 3  # Emerging: preprints, new sources, requires verification
    TIER_4 = 4  # Unverified: insufficient evidence to assess
    

class ValidationStatus(str, Enum):
    """Status of information validation"""
    VALIDATED = "validated"  # Confirmed by multiple Tier 1 sources
    PROBABLE = "probable"  # Supported by Tier 2+ sources
    UNVERIFIED = "unverified"  # Only Tier 3-4 sources
    CONFLICTING = "conflicting"  # Sources disagree
    

class RecommendationAction(str, Enum):
    """Recommended action based on credibility"""
    ACCEPT = "accept"  # Tier 1, use directly
    CAUTION = "caution"  # Tier 2, provide context
    VERIFY = "verify"  # Tier 3, recommend human review
    REJECT = "reject"  # Tier 4, block or heavily disclaim
    

@dataclass
class Source:
    """
    Information source with reputation tracking
    
    Attributes:
        source_id: Unique identifier
        name: Source name
        reputation_score: 0-1 score based on historical accuracy
        tier: Credibility tier
        domain_specialties: Domain expertise scores {domain_id: expertise_score}
        claims_made: Total claims from this source
        claims_validated: Claims confirmed correct
        claims_refuted: Claims proven false
        last_updated: When source data was last updated
    """
    source_id: str
    name: str
    reputation_score: float  # 0-1
    tier: CredibilityTier
    domain_specialties: Dict[str, float] = field(default_factory=dict)
    claims_made: int = 0
    claims_validated: int = 0
    claims_refuted: int = 0
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def validation_rate(self) -> float:
        """Percentage of claims validated"""
        if self.claims_made == 0:
            return 0.0
        return self.claims_validated / self.claims_made
    
    @property
    def refutation_rate(self) -> float:
        """Percentage of claims refuted"""
        if self.claims_made == 0:
            return 0.0
        return self.claims_refuted / self.claims_made
    
    def get_domain_expertise(self, domain_id: str) -> float:
        """Get expertise score for specific domain (0-1)"""
        return self.domain_specialties.get(domain_id, 0.0)
    
    def update_reputation(self, validated: bool) -> None:
        """Update reputation based on claim validation"""
        self.claims_made += 1
        if validated:
            self.claims_validated += 1
            # Increase reputation slightly (max 1.0)
            self.reputation_score = min(1.0, self.reputation_score + 0.01)
        else:
            self.claims_refuted += 1
            # Decrease reputation more aggressively
            self.reputation_score = max(0.0, self.reputation_score - 0.05)
        
        self.last_updated = datetime.utcnow()
    
    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "name": self.name,
            "reputation_score": self.reputation_score,
            "tier": self.tier.value,
            "domain_specialties": self.domain_specialties,
            "claims_made": self.claims_made,
            "validation_rate": self.validation_rate,
            "refutation_rate": self.refutation_rate
        }


@dataclass
class CredibilityMetadata:
    """
    Credibility assessment for a piece of information
    
    Attributes:
        overall_tier: Highest tier of sources (lowest number = best)
        confidence_score: 0-100 confidence in information
        source_count: Number of sources supporting
        validation_status: Validation state
        recommendation: Recommended action
        sources_used: List of source IDs
        domain_expertise_avg: Average domain expertise of sources
    """
    overall_tier: CredibilityTier
    confidence_score: int  # 0-100
    source_count: int
    validation_status: ValidationStatus
    recommendation: RecommendationAction
    sources_used: List[str] = field(default_factory=list)
    domain_expertise_avg: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "overall_tier": self.overall_tier.value,
            "confidence_score": self.confidence_score,
            "source_count": self.source_count,
            "validation_status": self.validation_status.value,
            "recommendation": self.recommendation.value,
            "sources_used": self.sources_used,
            "domain_expertise_avg": self.domain_expertise_avg
        }


class CredibilityEngine:
    """
    Evaluates information credibility based on source reputation and domain expertise
    """
    
    def __init__(self):
        self.sources: Dict[str, Source] = {}
        self._initialize_tier1_sources()
    
    def _initialize_tier1_sources(self) -> None:
        """Initialize Tier 1 authoritative sources"""
        
        # Scientific Journals (Tier 1)
        tier1_journals = [
            Source(
                source_id="nature",
                name="Nature",
                reputation_score=0.98,
                tier=CredibilityTier.TIER_1,
                domain_specialties={
                    "biotechnology_genomics": 0.98,
                    "healthcare_lifesciences": 0.95,
                    "nanotechnology": 0.92,
                    "quantum_computing": 0.90,
                    "ai_ml": 0.88
                }
            ),
            Source(
                source_id="science",
                name="Science",
                reputation_score=0.98,
                tier=CredibilityTier.TIER_1,
                domain_specialties={
                    "biotechnology_genomics": 0.97,
                    "healthcare_lifesciences": 0.94,
                    "synthetic_biology": 0.92,
                    "advanced_materials": 0.90
                }
            ),
            Source(
                source_id="cell",
                name="Cell",
                reputation_score=0.96,
                tier=CredibilityTier.TIER_1,
                domain_specialties={
                    "biotechnology_genomics": 0.98,
                    "healthcare_lifesciences": 0.96,
                    "synthetic_biology": 0.94
                }
            ),
        ]
        
        # Government Agencies (Tier 1)
        tier1_government = [
            Source(
                source_id="cdc",
                name="Centers for Disease Control",
                reputation_score=0.95,
                tier=CredibilityTier.TIER_1,
                domain_specialties={
                    "healthcare_lifesciences": 0.98,
                    "food_agriculture_water": 0.85
                }
            ),
            Source(
                source_id="fda",
                name="FDA",
                reputation_score=0.94,
                tier=CredibilityTier.TIER_1,
                domain_specialties={
                    "healthcare_lifesciences": 0.97,
                    "biotechnology_genomics": 0.90,
                    "food_agriculture_water": 0.88
                }
            ),
            Source(
                source_id="federal_reserve",
                name="Federal Reserve",
                reputation_score=0.96,
                tier=CredibilityTier.TIER_1,
                domain_specialties={
                    "finance_banking": 0.98,
                    "real_estate_property": 0.88
                }
            ),
            Source(
                source_id="nasa",
                name="NASA",
                reputation_score=0.97,
                tier=CredibilityTier.TIER_1,
                domain_specialties={
                    "space_technology": 0.99,
                    "defense_aerospace": 0.92,
                    "advanced_materials": 0.85
                }
            ),
            Source(
                source_id="nist",
                name="NIST",
                reputation_score=0.96,
                tier=CredibilityTier.TIER_1,
                domain_specialties={
                    "semiconductors_computing": 0.94,
                    "quantum_computing": 0.95,
                    "advanced_materials": 0.90,
                    "nanotechnology": 0.92
                }
            ),
            Source(
                source_id="doe",
                name="Department of Energy",
                reputation_score=0.94,
                tier=CredibilityTier.TIER_1,
                domain_specialties={
                    "energy_production": 0.97,
                    "renewable_energy_tech": 0.95,
                    "fusion_energy": 0.98,
                    "mining_resources": 0.85
                }
            ),
        ]
        
        # Standards Bodies & Professional Organizations (Tier 1)
        tier1_standards = [
            Source(
                source_id="ieee",
                name="IEEE",
                reputation_score=0.93,
                tier=CredibilityTier.TIER_1,
                domain_specialties={
                    "semiconductors_computing": 0.95,
                    "ai_ml": 0.90,
                    "telecommunications": 0.94,
                    "5g_6g_networks": 0.92,
                    "robotics_automation": 0.88
                }
            ),
            Source(
                source_id="aaas",
                name="American Association for the Advancement of Science",
                reputation_score=0.94,
                tier=CredibilityTier.TIER_1,
                domain_specialties={
                    "education_research": 0.96,
                    "biotechnology_genomics": 0.90,
                    "ai_ml": 0.85
                }
            ),
        ]
        
        # International Organizations (Tier 1)
        tier1_international = [
            Source(
                source_id="who",
                name="World Health Organization",
                reputation_score=0.92,
                tier=CredibilityTier.TIER_1,
                domain_specialties={
                    "healthcare_lifesciences": 0.96,
                    "food_agriculture_water": 0.82
                }
            ),
            Source(
                source_id="iaea",
                name="International Atomic Energy Agency",
                reputation_score=0.93,
                tier=CredibilityTier.TIER_1,
                domain_specialties={
                    "energy_production": 0.96,
                    "fusion_energy": 0.94
                }
            ),
        ]
        
        # Finance & Economics (Tier 1)
        tier1_finance = [
            Source(
                source_id="imf",
                name="International Monetary Fund",
                reputation_score=0.91,
                tier=CredibilityTier.TIER_1,
                domain_specialties={
                    "finance_banking": 0.94,
                    "education_research": 0.80
                }
            ),
            Source(
                source_id="world_bank",
                name="World Bank",
                reputation_score=0.90,
                tier=CredibilityTier.TIER_1,
                domain_specialties={
                    "finance_banking": 0.92,
                    "construction_infrastructure": 0.88,
                    "food_agriculture_water": 0.85
                }
            ),
        ]
        
        # Add all Tier 1 sources
        all_tier1 = (
            tier1_journals + tier1_government + tier1_standards + 
            tier1_international + tier1_finance
        )
        
        for source in all_tier1:
            self.sources[source.source_id] = source
    
    def add_source(self, source: Source) -> None:
        """Add new source to engine"""
        self.sources[source.source_id] = source
    
    def evaluate_information(
        self,
        source_ids: List[str],
        domain_id: Optional[str] = None,
        user_stakes: str = "medium"  # low, medium, high
    ) -> CredibilityMetadata:
        """
        Evaluate credibility of information based on sources
        
        Args:
            source_ids: List of source IDs making the claim
            domain_id: Optional domain context
            user_stakes: Importance level (affects recommendation)
            
        Returns:
            CredibilityMetadata with assessment
        """
        if not source_ids:
            return CredibilityMetadata(
                overall_tier=CredibilityTier.TIER_4,
                confidence_score=0,
                source_count=0,
                validation_status=ValidationStatus.UNVERIFIED,
                recommendation=RecommendationAction.REJECT
            )
        
        # Get all valid sources
        valid_sources = [
            self.sources[sid] for sid in source_ids 
            if sid in self.sources
        ]
        
        if not valid_sources:
            return CredibilityMetadata(
                overall_tier=CredibilityTier.TIER_4,
                confidence_score=0,
                source_count=0,
                validation_status=ValidationStatus.UNVERIFIED,
                recommendation=RecommendationAction.REJECT
            )
        
        # Determine overall tier (best tier from all sources)
        overall_tier = min(s.tier for s in valid_sources)
        
        # Calculate domain expertise average if domain specified
        domain_expertise_avg = 0.0
        if domain_id:
            expertise_scores = [s.get_domain_expertise(domain_id) for s in valid_sources]
            domain_expertise_avg = sum(expertise_scores) / len(expertise_scores) if expertise_scores else 0.0
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence(
            valid_sources, 
            overall_tier, 
            domain_expertise_avg
        )
        
        # Determine validation status
        validation_status = self._determine_validation_status(valid_sources, overall_tier)
        
        # Determine recommendation based on tier and stakes
        recommendation = self._determine_recommendation(
            overall_tier, 
            confidence_score, 
            user_stakes
        )
        
        return CredibilityMetadata(
            overall_tier=overall_tier,
            confidence_score=confidence_score,
            source_count=len(valid_sources),
            validation_status=validation_status,
            recommendation=recommendation,
            sources_used=source_ids,
            domain_expertise_avg=domain_expertise_avg
        )
    
    def _calculate_confidence(
        self, 
        sources: List[Source], 
        overall_tier: CredibilityTier,
        domain_expertise: float
    ) -> int:
        """Calculate confidence score 0-100"""
        
        # Base score from tier
        tier_scores = {
            CredibilityTier.TIER_1: 90,
            CredibilityTier.TIER_2: 70,
            CredibilityTier.TIER_3: 40,
            CredibilityTier.TIER_4: 10
        }
        base_score = tier_scores[overall_tier]
        
        # Boost for multiple sources (max +10)
        source_boost = min(10, len(sources) * 2)
        
        # Boost for domain expertise (max +10)
        expertise_boost = int(domain_expertise * 10)
        
        # Average reputation boost (max +10)
        avg_reputation = sum(s.reputation_score for s in sources) / len(sources)
        reputation_boost = int(avg_reputation * 10)
        
        total = min(100, base_score + source_boost + expertise_boost + reputation_boost)
        return total
    
    def _determine_validation_status(
        self, 
        sources: List[Source], 
        overall_tier: CredibilityTier
    ) -> ValidationStatus:
        """Determine validation status"""
        
        tier1_count = sum(1 for s in sources if s.tier == CredibilityTier.TIER_1)
        
        if tier1_count >= 2:
            return ValidationStatus.VALIDATED
        elif tier1_count >= 1 or overall_tier == CredibilityTier.TIER_2:
            return ValidationStatus.PROBABLE
        else:
            return ValidationStatus.UNVERIFIED
    
    def _determine_recommendation(
        self, 
        overall_tier: CredibilityTier,
        confidence_score: int,
        user_stakes: str
    ) -> RecommendationAction:
        """Determine recommended action"""
        
        # High stakes requires higher standards
        if user_stakes == "high":
            if overall_tier == CredibilityTier.TIER_1 and confidence_score >= 85:
                return RecommendationAction.ACCEPT
            elif overall_tier <= CredibilityTier.TIER_2 and confidence_score >= 70:
                return RecommendationAction.CAUTION
            elif overall_tier <= CredibilityTier.TIER_3:
                return RecommendationAction.VERIFY
            else:
                return RecommendationAction.REJECT
        
        # Medium stakes (default)
        elif user_stakes == "medium":
            if overall_tier == CredibilityTier.TIER_1:
                return RecommendationAction.ACCEPT
            elif overall_tier == CredibilityTier.TIER_2:
                return RecommendationAction.CAUTION
            elif overall_tier == CredibilityTier.TIER_3:
                return RecommendationAction.VERIFY
            else:
                return RecommendationAction.REJECT
        
        # Low stakes (permissive)
        else:  # user_stakes == "low"
            if overall_tier <= CredibilityTier.TIER_2:
                return RecommendationAction.ACCEPT
            elif overall_tier == CredibilityTier.TIER_3:
                return RecommendationAction.CAUTION
            else:
                return RecommendationAction.VERIFY
    
    def update_source_reputation(self, source_id: str, validated: bool) -> None:
        """Update source reputation based on claim validation"""
        if source_id in self.sources:
            self.sources[source_id].update_reputation(validated)
    
    def get_source(self, source_id: str) -> Optional[Source]:
        """Get source by ID"""
        return self.sources.get(source_id)
    
    def get_sources_by_tier(self, tier: CredibilityTier) -> List[Source]:
        """Get all sources in a specific tier"""
        return [s for s in self.sources.values() if s.tier == tier]
    
    def to_dict(self) -> dict:
        """Serialize engine to dictionary"""
        return {
            "sources": {k: v.to_dict() for k, v in self.sources.items()},
            "source_count": len(self.sources),
            "tier_distribution": {
                f"tier_{i}": len(self.get_sources_by_tier(CredibilityTier(i)))
                for i in range(1, 5)
            }
        }
    
    def __repr__(self) -> str:
        tier1_count = len(self.get_sources_by_tier(CredibilityTier.TIER_1))
        return f"<CredibilityEngine: {len(self.sources)} sources ({tier1_count} Tier 1)>"
