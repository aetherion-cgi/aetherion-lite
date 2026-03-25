"""
UIE Credibility Translator
Translates credibility metadata into natural language guidance for users

CRITICAL: Never expose internal metadata (tiers, scores) to users.
Instead, provide contextual guidance appropriate to credibility level.
"""

from typing import Dict, Optional
from enum import Enum

from ILE_Complete_Implementation.ile_system.credibility.source_credibility import (
    CredibilityMetadata, CredibilityTier, RecommendationAction
)


class GuidanceStyle(str, Enum):
    """Style of guidance to provide"""
    CLEAN = "clean"  # No indicator, tier 1 only
    CONTEXTUAL = "contextual"  # Gentle context for tier 2
    WARNING = "warning"  # Clear warning for tier 3
    BLOCK = "block"  # Strong block for tier 4


class UIECredibilityTranslator:
    """
    Translates credibility assessment into user-friendly responses
    
    Tier mapping (INTERNAL ONLY - never expose to users):
    - Tier 1 → Clean response (authoritative sources)
    - Tier 2 → Add contextual guidance (emerging analysis)
    - Tier 3 → Add validation warning (requires verification)
    - Tier 4 → Block or heavily disclaim (unverified)
    """
    
    @staticmethod
    def format_response(
        content: str,
        credibility_metadata: CredibilityMetadata,
        user_context: Optional[Dict] = None
    ) -> Dict[str, any]:
        """
        Format response based on credibility level
        
        Args:
            content: Base response content
            credibility_metadata: Credibility assessment
            user_context: Optional user context (stakes, expertise)
            
        Returns:
            Dict with:
            - text: Formatted response text
            - indicator: Optional visual indicator (emoji/icon)
            - recommendation: Suggested action (for UI only)
        """
        
        if user_context is None:
            user_context = {}
        
        tier = credibility_metadata.overall_tier
        stakes = user_context.get("stakes", "medium")
        
        # Tier 1: Authoritative - clean response
        if tier == CredibilityTier.TIER_1:
            return {
                "text": content,
                "indicator": None,  # No indicator needed
                "recommendation": "accept",
                "guidance_style": GuidanceStyle.CLEAN.value
            }
        
        # Tier 2: Established - add gentle context
        elif tier == CredibilityTier.TIER_2:
            guidance = UIECredibilityTranslator._tier2_guidance(content, stakes)
            return {
                "text": content + "\n\n" + guidance,
                "indicator": "ℹ️ Emerging analysis",
                "recommendation": "caution",
                "guidance_style": GuidanceStyle.CONTEXTUAL.value
            }
        
        # Tier 3: Emerging - add validation warning
        elif tier == CredibilityTier.TIER_3:
            warning = UIECredibilityTranslator._tier3_warning(content, stakes)
            return {
                "text": warning,
                "indicator": "⚠️ Validation recommended",
                "recommendation": "verify",
                "guidance_style": GuidanceStyle.WARNING.value
            }
        
        # Tier 4: Unverified - block or strong disclaimer
        else:
            block_message = UIECredibilityTranslator._tier4_block(stakes)
            return {
                "text": block_message,
                "indicator": "🚫 Cannot verify",
                "recommendation": "reject",
                "guidance_style": GuidanceStyle.BLOCK.value
            }
    
    @staticmethod
    def _tier2_guidance(content: str, stakes: str) -> str:
        """Generate tier 2 contextual guidance"""
        
        if stakes == "high":
            return (
                "**Note on analysis scope:** This analysis draws from established "
                "but not yet fully validated sources. For high-stakes decisions, "
                "consider seeking additional validation from domain experts or "
                "peer-reviewed sources."
            )
        elif stakes == "medium":
            return (
                "**Context:** This analysis incorporates emerging information "
                "from reputable sources. The conclusions are well-supported but "
                "represent a developing understanding rather than settled consensus."
            )
        else:  # low stakes
            return (
                "**FYI:** Based on current information from established sources. "
                "As with any analysis, new developments may shift conclusions."
            )
    
    @staticmethod
    def _tier3_warning(content: str, stakes: str) -> str:
        """Generate tier 3 validation warning"""
        
        if stakes == "high":
            # For high stakes, don't show content at all
            return (
                "⚠️ **Validation Required**\n\n"
                "The requested analysis relies on sources that require validation "
                "before use in high-stakes decisions.\n\n"
                "**Recommended actions:**\n"
                "- Consult with domain experts\n"
                "- Review peer-reviewed literature\n"
                "- Obtain authoritative sources (government agencies, standards bodies)\n\n"
                "Would you like assistance finding validated sources on this topic?"
            )
        elif stakes == "medium":
            # Show content but with strong framing
            return (
                "⚠️ **Please Read Before Using This Analysis**\n\n"
                "The analysis below draws from sources that are not yet fully validated. "
                "While the information may be useful for exploration, it should not be "
                "the sole basis for significant decisions.\n\n"
                f"{content}\n\n"
                "**Before acting on this analysis:**\n"
                "- Cross-reference with authoritative sources\n"
                "- Consult subject matter experts\n"
                "- Verify key claims independently\n\n"
                "This is exploratory analysis, not definitive guidance."
            )
        else:  # low stakes
            # Show content with lighter framing
            return (
                f"{content}\n\n"
                "ℹ️ **Note:** This analysis uses sources that haven't been fully "
                "validated. Good for getting started, but verify before relying on "
                "it for anything important."
            )
    
    @staticmethod
    def _tier4_block(stakes: str) -> str:
        """Generate tier 4 block message"""
        
        return (
            "🚫 **Unable to Provide Verified Analysis**\n\n"
            "I don't have access to sufficiently verified sources to answer this "
            "query reliably.\n\n"
            "**What you can do:**\n"
            "- Rephrase your query to focus on well-documented topics\n"
            "- Specify particular authoritative sources you'd like me to reference\n"
            "- For critical decisions, consult with domain experts directly\n\n"
            "I'm designed to provide only information I can verify through "
            "credible sources. Would you like suggestions for where to find "
            "authoritative information on this topic?"
        )
    
    @staticmethod
    def generate_source_suggestions(
        domain_id: str,
        credibility_metadata: CredibilityMetadata
    ) -> str:
        """
        Generate suggestions for authoritative sources
        
        Args:
            domain_id: Domain being queried
            credibility_metadata: Credibility assessment
            
        Returns:
            Natural language source suggestions
        """
        
        # Domain-specific authoritative sources
        domain_sources = {
            "healthcare_lifesciences": [
                "CDC (Centers for Disease Control)",
                "FDA (Food and Drug Administration)",
                "WHO (World Health Organization)",
                "Peer-reviewed journals (Nature, Cell, The Lancet)"
            ],
            "energy_production": [
                "Department of Energy (DOE)",
                "International Energy Agency (IEA)",
                "IAEA (for nuclear energy)",
                "IEEE journals and standards"
            ],
            "finance_banking": [
                "Federal Reserve",
                "IMF (International Monetary Fund)",
                "World Bank",
                "SEC filings and reports"
            ],
            "semiconductors_computing": [
                "IEEE (Institute of Electrical and Electronics Engineers)",
                "NIST (National Institute of Standards and Technology)",
                "Major fab company technical reports (TSMC, Intel, Samsung)"
            ],
            "ai_ml": [
                "NeurIPS, ICML, ICLR conference proceedings",
                "arXiv preprints (with caution)",
                "Major research labs (OpenAI, DeepMind, Anthropic)",
                "IEEE and ACM journals"
            ],
            "space_technology": [
                "NASA",
                "ESA (European Space Agency)",
                "SpaceX and other major aerospace companies",
                "AIAA journals"
            ],
        }
        
        sources = domain_sources.get(domain_id, [
            "Government agencies relevant to the field",
            "Peer-reviewed academic journals",
            "Standards bodies (IEEE, ISO, etc.)",
            "Major research institutions"
        ])
        
        suggestions = "**Suggested authoritative sources:**\n"
        for source in sources:
            suggestions += f"- {source}\n"
        
        return suggestions.strip()
    
    @staticmethod
    def explain_credibility_without_exposing_tiers(
        credibility_metadata: CredibilityMetadata
    ) -> str:
        """
        Explain credibility in user-friendly terms without exposing tier system
        
        Args:
            credibility_metadata: Credibility assessment
            
        Returns:
            Natural language explanation
        """
        
        tier = credibility_metadata.overall_tier
        confidence = credibility_metadata.confidence_score
        
        if tier == CredibilityTier.TIER_1:
            return (
                "This analysis is based on well-established, authoritative sources "
                "including peer-reviewed research and government agencies."
            )
        elif tier == CredibilityTier.TIER_2:
            return (
                "This analysis draws from reputable sources, though some aspects "
                "represent emerging understanding rather than settled consensus."
            )
        elif tier == CredibilityTier.TIER_3:
            return (
                "This analysis is exploratory and based on sources that haven't "
                "been fully validated through peer review or official channels."
            )
        else:  # Tier 4
            return (
                "I don't have access to verified sources for this query. "
                "I recommend consulting domain experts or authoritative references."
            )
    
    @staticmethod
    def should_show_content(
        credibility_metadata: CredibilityMetadata,
        user_context: Optional[Dict] = None
    ) -> bool:
        """
        Determine if content should be shown to user
        
        High stakes + Tier 3/4 = Don't show content
        Medium stakes + Tier 4 = Don't show content
        Low stakes + any tier = Show content (with appropriate framing)
        
        Args:
            credibility_metadata: Credibility assessment
            user_context: Optional user context
            
        Returns:
            Boolean indicating whether to show content
        """
        
        if user_context is None:
            user_context = {}
        
        stakes = user_context.get("stakes", "medium")
        tier = credibility_metadata.overall_tier
        
        # Always show Tier 1-2
        if tier <= CredibilityTier.TIER_2:
            return True
        
        # High stakes: only show Tier 1-2
        if stakes == "high":
            return False
        
        # Medium stakes: show up to Tier 3
        if stakes == "medium":
            return tier <= CredibilityTier.TIER_3
        
        # Low stakes: show all tiers (with appropriate warnings)
        return True
