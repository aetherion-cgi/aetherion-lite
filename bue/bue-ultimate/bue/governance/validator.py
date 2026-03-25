"""Governance Validator - Constitutional governance enforcement"""

from typing import Dict, Any, Optional
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class AuthorizationTier(Enum):
    FULLY_AUTONOMOUS = "autonomous"
    INTERNATIONAL_REVIEW = "international"
    CRITICAL_REVIEW = "critical"
    IMMEDIATE_HALT = "halt"


class GovernanceValidator:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.opa_enabled = config.get('opa_enabled', False) if config else False
        logger.info(f"GovernanceValidator initialized (OPA: {self.opa_enabled})")
    
    async def validate(self, metrics: Dict[str, Any], risk_analysis: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        benefit_score = self._calculate_benefit_score(metrics, risk_analysis)
        harm_score = self._calculate_harm_score(metrics, risk_analysis)
        tier = self._determine_authorization_tier(benefit_score, harm_score)
        needs_escalation = self._needs_escalation(metrics, risk_analysis, tier)
        approved = self._is_approved(benefit_score, harm_score, tier)
        
        return {
            'benefit_score': benefit_score,
            'harm_score': harm_score,
            'authorization_tier': tier.value,
            'approved': approved,
            'needs_escalation': needs_escalation,
            'reasoning': self._generate_reasoning(benefit_score, harm_score, tier, approved)
        }
    
    def _calculate_benefit_score(self, metrics: Dict[str, Any], risk_analysis: Optional[Dict[str, Any]]) -> float:
        base_benefit = metrics.get('composite_score', 50.0) / 100.0
        growth_rate = metrics.get('growth_rate', 0.0)
        if growth_rate > 0:
            base_benefit = min(1.0, base_benefit * (1 + growth_rate * 0.2))
        if risk_analysis:
            risk_score = risk_analysis.get('risk_score', 0.5)
            base_benefit = base_benefit * (1 - risk_score * 0.3)
        return max(0.0, min(1.0, base_benefit))
    
    def _calculate_harm_score(self, metrics: Dict[str, Any], risk_analysis: Optional[Dict[str, Any]]) -> float:
        if risk_analysis:
            base_harm = risk_analysis.get('risk_score', 0.3)
        else:
            base_harm = 0.3
        volatility = metrics.get('volatility', 0.15)
        if volatility > 0.25:
            base_harm = min(1.0, base_harm * 1.5)
        composite_score = metrics.get('composite_score', 50.0)
        if composite_score > 70:
            base_harm = base_harm * 0.7
        return max(0.0, min(1.0, base_harm))
    
    def _determine_authorization_tier(self, benefit_score: float, harm_score: float) -> AuthorizationTier:
        net_benefit = benefit_score - harm_score
        if net_benefit >= 0.5 and harm_score < 0.1:
            return AuthorizationTier.FULLY_AUTONOMOUS
        elif net_benefit >= 0.3:
            return AuthorizationTier.INTERNATIONAL_REVIEW
        elif net_benefit >= 0.0:
            return AuthorizationTier.CRITICAL_REVIEW
        else:
            return AuthorizationTier.IMMEDIATE_HALT
    
    def _needs_escalation(self, metrics: Dict[str, Any], risk_analysis: Optional[Dict[str, Any]], tier: AuthorizationTier) -> bool:
        if tier in [AuthorizationTier.CRITICAL_REVIEW, AuthorizationTier.IMMEDIATE_HALT]:
            return True
        deal_size = metrics.get('purchase_price', 0) or metrics.get('valuation', 0)
        if deal_size > 100_000_000:
            return True
        if risk_analysis and risk_analysis.get('risk_score', 0) > 0.7:
            return True
        return False
    
    def _is_approved(self, benefit_score: float, harm_score: float, tier: AuthorizationTier) -> bool:
        if tier == AuthorizationTier.IMMEDIATE_HALT:
            return False
        if benefit_score > harm_score and benefit_score >= 0.5:
            return True
        return False
    
    def _generate_reasoning(self, benefit_score: float, harm_score: float, tier: AuthorizationTier, approved: bool) -> str:
        if approved:
            return f"Decision approved (Benefit: {benefit_score:.2f}, Harm: {harm_score:.2f}). Authorization tier: {tier.value}."
        else:
            return f"Decision requires review (Benefit: {benefit_score:.2f}, Harm: {harm_score:.2f}). Authorization tier: {tier.value}. Escalating to URPE."
