"""
Internal Learning Engine - Constitutional Validator

Safety validation layer that ensures all learning aligns with Aetherion's
constitutional governance framework. Every learning event is evaluated for:
- Human benefit scoring
- Harm assessment
- Privacy preservation
- Bias detection
- Sovereignty compliance

Author: Aetherion Development Team
Date: November 15, 2025
"""

import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Set
from uuid import uuid4

from .models import (
    LearningEvent, ConstitutionalValidation, ConstitutionalDecision,
    DomainType, APIType, AuditLogEntry
)
from .database import db_manager, create_audit_hash, get_last_audit_hash

logger = logging.getLogger(__name__)


# ============================================================================
# CONSTITUTIONAL VALIDATOR
# ============================================================================

class ConstitutionalValidator:
    """
    Validates all learning against constitutional governance principles.
    
    Core Constitutional Principles:
    1. Human Primacy: All learning must benefit humanity
    2. Privacy Preservation: No learning from private data without consent
    3. Bias Prevention: Detect and reject biased learning
    4. Sovereignty Compliance: Respect jurisdictional boundaries
    5. Transparency: Full audit trail of all decisions
    """
    
    # Protected attributes for bias detection
    PROTECTED_ATTRIBUTES = {
        "race", "ethnicity", "gender", "religion", "nationality",
        "sexual_orientation", "disability", "age", "political_affiliation"
    }
    
    # Sensitive keywords for privacy check
    SENSITIVE_KEYWORDS = {
        "ssn", "social_security", "credit_card", "password", "private_key",
        "api_key", "secret", "confidential", "classified"
    }
    
    def __init__(self):
        # Constitutional scoring weights
        self.benefit_weights = {
            "accuracy_improvement": 30.0,
            "efficiency_gain": 25.0,
            "human_productivity": 20.0,
            "safety_enhancement": 15.0,
            "knowledge_advancement": 10.0
        }
        
        self.harm_weights = {
            "privacy_violation": 40.0,
            "bias_risk": 30.0,
            "sovereignty_violation": 20.0,
            "security_risk": 10.0
        }
        
        # Decision thresholds
        self.auto_approval_threshold = 70.0  # Net benefit >= 70% = approved
        self.review_threshold = 50.0  # 50% <= net benefit < 70% = review
        # Net benefit < 50% = rejected
        
        logger.info("Constitutional Validator initialized")
    
    async def validate_learning(self, event: LearningEvent) -> ConstitutionalValidation:
        """
        Validate learning event against constitutional principles.
        
        Args:
            event: Learning event to validate
        
        Returns:
            ConstitutionalValidation with decision and scoring
        """
        try:
            # Step 1: Calculate benefit score
            benefit_score = self._calculate_benefit_score(event)
            
            # Step 2: Calculate harm score
            harm_score = await self._calculate_harm_score(event)
            
            # Step 3: Perform specific checks
            human_primacy = self._check_human_primacy(event)
            privacy = self._check_privacy(event)
            bias = self._check_bias(event)
            sovereignty = self._check_sovereignty(event)
            
            # Step 4: Determine decision
            net_benefit = benefit_score - harm_score
            decision, reason, violations = self._make_decision(
                net_benefit=net_benefit,
                human_primacy=human_primacy,
                privacy=privacy,
                bias=bias,
                sovereignty=sovereignty
            )
            
            # Step 5: Create validation record
            validation = ConstitutionalValidation(
                event_id=event.event_id,
                benefit_score=benefit_score,
                harm_score=harm_score,
                net_benefit=net_benefit,
                decision=decision,
                decision_reason=reason,
                human_primacy_check=human_primacy,
                privacy_check=privacy,
                bias_check=bias,
                sovereignty_check=sovereignty,
                violations=violations
            )
            
            # Step 6: Store validation and create audit trail
            await self._store_validation(event, validation)
            
            logger.info(
                f"Validation complete: {decision.value} "
                f"(benefit={benefit_score:.1f}, harm={harm_score:.1f}, "
                f"net={net_benefit:.1f})"
            )
            
            return validation
        
        except Exception as e:
            logger.error(f"Error in constitutional validation: {e}", exc_info=True)
            # Fail closed: reject on validation error
            return ConstitutionalValidation(
                event_id=event.event_id,
                benefit_score=0.0,
                harm_score=100.0,
                net_benefit=-100.0,
                decision=ConstitutionalDecision.REJECTED,
                decision_reason=f"Validation error: {str(e)}",
                human_primacy_check=False,
                privacy_check=False,
                bias_check=False,
                sovereignty_check=False,
                violations=["validation_error"]
            )
    
    # ========================================================================
    # BENEFIT SCORING
    # ========================================================================
    
    def _calculate_benefit_score(self, event: LearningEvent) -> float:
        """
        Calculate human benefit score (0-100).
        
        Factors:
        - Accuracy improvement from learning
        - Efficiency gains
        - Human productivity enhancement
        - Safety improvements
        - Knowledge advancement
        """
        score = 0.0
        
        # Accuracy improvement (from learning signal)
        if event.learning_signal is not None:
            # Map [-1, 1] to [0, 1]
            normalized_signal = (event.learning_signal + 1) / 2
            score += normalized_signal * self.benefit_weights["accuracy_improvement"]
        else:
            # Default moderate benefit if no signal
            score += 0.5 * self.benefit_weights["accuracy_improvement"]
        
        # Efficiency gains (domain-specific)
        if event.domain in [DomainType.TASK_BASED, DomainType.CROSS_DOMAIN]:
            score += 0.8 * self.benefit_weights["efficiency_gain"]
        elif event.domain == DomainType.USER_INTERACTION:
            score += 0.7 * self.benefit_weights["efficiency_gain"]
        else:
            score += 0.6 * self.benefit_weights["efficiency_gain"]
        
        # Human productivity (API-specific)
        if event.api in [APIType.BUE, APIType.UDOA, APIType.UIE]:
            score += 0.8 * self.benefit_weights["human_productivity"]
        else:
            score += 0.6 * self.benefit_weights["human_productivity"]
        
        # Safety enhancement (higher for URPE and security domain)
        if event.api == APIType.URPE or event.domain == DomainType.SECURITY:
            score += 0.9 * self.benefit_weights["safety_enhancement"]
        else:
            score += 0.7 * self.benefit_weights["safety_enhancement"]
        
        # Knowledge advancement (higher for internet and cross-domain)
        if event.domain in [DomainType.INTERNET, DomainType.CROSS_DOMAIN, DomainType.DOMAIN_CORTEX]:
            score += 0.9 * self.benefit_weights["knowledge_advancement"]
        else:
            score += 0.6 * self.benefit_weights["knowledge_advancement"]
        
        # Ensure score is in [0, 100]
        return max(0.0, min(100.0, score))
    
    # ========================================================================
    # HARM ASSESSMENT
    # ========================================================================
    
    async def _calculate_harm_score(self, event: LearningEvent) -> float:
        """
        Calculate potential harm score (0-100).
        
        Factors:
        - Privacy violations
        - Bias risks
        - Sovereignty violations
        - Security risks
        """
        score = 0.0
        
        # Privacy violation risk
        if not self._check_privacy(event):
            score += self.harm_weights["privacy_violation"]
        
        # Bias risk
        if not self._check_bias(event):
            score += self.harm_weights["bias_risk"]
        
        # Sovereignty violation
        if not self._check_sovereignty(event):
            score += self.harm_weights["sovereignty_violation"]
        
        # Security risk (from event metadata)
        security_risk = event.metadata.get("security_risk", 0.0)
        score += security_risk * self.harm_weights["security_risk"]
        
        # Ensure score is in [0, 100]
        return max(0.0, min(100.0, score))
    
    # ========================================================================
    # SPECIFIC CONSTITUTIONAL CHECKS
    # ========================================================================
    
    def _check_human_primacy(self, event: LearningEvent) -> bool:
        """
        Check: Does this learning serve human benefit?
        
        All learning MUST be in service of humanity. Learning that:
        - Reduces human agency
        - Replaces human decision-making in critical areas
        - Optimizes AI goals independent of human benefit
        
        ...violates human primacy.
        """
        # Check metadata for human primacy flags
        if event.metadata.get("reduces_human_agency", False):
            logger.warning("Human primacy violation: reduces human agency")
            return False
        
        if event.metadata.get("replaces_human_decision", False):
            logger.warning("Human primacy violation: replaces human decision")
            return False
        
        # Default: passes unless explicitly flagged
        return True
    
    def _check_privacy(self, event: LearningEvent) -> bool:
        """
        Check: Does this learning violate privacy?
        
        Learning MUST NOT:
        - Learn from private data without consent
        - Store sensitive personal information
        - Enable identification of individuals
        """
        # Check for sensitive keywords in inputs/outputs
        all_data = str(event.inputs) + str(event.predicted) + str(event.actual)
        all_data_lower = all_data.lower()
        
        for keyword in self.SENSITIVE_KEYWORDS:
            if keyword in all_data_lower:
                logger.warning(f"Privacy violation: sensitive keyword '{keyword}' detected")
                return False
        
        # Check for PII patterns (SSN, credit card, etc.)
        if self._contains_pii(all_data):
            logger.warning("Privacy violation: PII pattern detected")
            return False
        
        # Check consent flag in metadata
        if event.metadata.get("requires_consent", False):
            if not event.metadata.get("consent_granted", False):
                logger.warning("Privacy violation: consent required but not granted")
                return False
        
        return True
    
    def _check_bias(self, event: LearningEvent) -> bool:
        """
        Check: Does this learning introduce or amplify bias?
        
        Learning MUST NOT:
        - Use protected attributes as features
        - Learn patterns that discriminate
        - Amplify existing societal biases
        """
        # Check for protected attributes in inputs
        all_data = str(event.inputs).lower()
        
        for attribute in self.PROTECTED_ATTRIBUTES:
            if attribute in all_data:
                logger.warning(f"Bias risk: protected attribute '{attribute}' in inputs")
                return False
        
        # Check bias flag in metadata
        if event.metadata.get("bias_risk", 0.0) > 0.5:
            logger.warning("Bias risk: high bias risk score in metadata")
            return False
        
        return True
    
    def _check_sovereignty(self, event: LearningEvent) -> bool:
        """
        Check: Does this learning respect jurisdictional boundaries?
        
        Learning MUST:
        - Respect data sovereignty laws
        - Honor jurisdiction-specific restrictions
        - Comply with local regulations
        """
        from .models import Jurisdiction
        
        # Check jurisdiction compatibility
        if event.jurisdiction == Jurisdiction.SANDBOX:
            # Sandbox always allowed
            return True
        
        # Check for cross-border data transfer
        if event.metadata.get("cross_border_transfer", False):
            # Require explicit approval for cross-border
            if not event.metadata.get("transfer_approved", False):
                logger.warning("Sovereignty violation: cross-border transfer not approved")
                return False
        
        # Check jurisdiction-specific restrictions
        restricted_domains = event.metadata.get("jurisdiction_restrictions", [])
        if event.domain.value in restricted_domains:
            logger.warning(f"Sovereignty violation: {event.domain} restricted in {event.jurisdiction}")
            return False
        
        return True
    
    # ========================================================================
    # DECISION LOGIC
    # ========================================================================
    
    def _make_decision(
        self,
        net_benefit: float,
        human_primacy: bool,
        privacy: bool,
        bias: bool,
        sovereignty: bool
    ) -> tuple[ConstitutionalDecision, str, List[str]]:
        """
        Make final constitutional decision.
        
        Returns:
            (decision, reason, violations)
        """
        violations = []
        
        # Collect violations
        if not human_primacy:
            violations.append("human_primacy")
        if not privacy:
            violations.append("privacy")
        if not bias:
            violations.append("bias")
        if not sovereignty:
            violations.append("sovereignty")
        
        # Hard failures: any absolute violation = reject
        if violations:
            return (
                ConstitutionalDecision.REJECTED,
                f"Constitutional violations: {', '.join(violations)}",
                violations
            )
        
        # Net benefit thresholds
        if net_benefit >= self.auto_approval_threshold:
            return (
                ConstitutionalDecision.APPROVED,
                f"High net benefit ({net_benefit:.1f}%), all checks passed",
                []
            )
        elif net_benefit >= self.review_threshold:
            return (
                ConstitutionalDecision.REVIEW_REQUIRED,
                f"Moderate net benefit ({net_benefit:.1f}%), human review required",
                []
            )
        else:
            return (
                ConstitutionalDecision.REJECTED,
                f"Low net benefit ({net_benefit:.1f}%), below review threshold",
                ["low_benefit"]
            )
    
    # ========================================================================
    # UTILITY FUNCTIONS
    # ========================================================================
    
    def _contains_pii(self, text: str) -> bool:
        """Check if text contains PII patterns"""
        # SSN pattern: XXX-XX-XXXX
        ssn_pattern = r'\b\d{3}-\d{2}-\d{4}\b'
        if re.search(ssn_pattern, text):
            return True
        
        # Credit card pattern: XXXX-XXXX-XXXX-XXXX
        cc_pattern = r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
        if re.search(cc_pattern, text):
            return True
        
        # Email pattern (potential PII)
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if re.search(email_pattern, text):
            # Only flag if not in whitelist
            if not text.endswith("@aetherion.ai"):
                return True
        
        return False
    
    async def _store_validation(
        self,
        event: LearningEvent,
        validation: ConstitutionalValidation
    ):
        """Store validation result and create audit trail"""
        if not db_manager:
            return
        
        try:
            async with db_manager.postgres_session() as session:
                # Store validation
                from .database import ConstitutionalValidationTable
                from sqlalchemy import insert
                
                await session.execute(
                    insert(ConstitutionalValidationTable).values(
                        validation_id=str(validation.validation_id),
                        event_id=str(validation.event_id),
                        timestamp=validation.timestamp,
                        benefit_score=validation.benefit_score,
                        harm_score=validation.harm_score,
                        net_benefit=validation.net_benefit,
                        decision=validation.decision.value,
                        decision_reason=validation.decision_reason,
                        human_primacy_check=validation.human_primacy_check,
                        privacy_check=validation.privacy_check,
                        bias_check=validation.bias_check,
                        sovereignty_check=validation.sovereignty_check,
                        violations=validation.violations
                    )
                )
                
                # Create audit log entry
                previous_hash = await get_last_audit_hash(session)
                current_hash = create_audit_hash(
                    event_id=str(event.event_id),
                    validation_id=str(validation.validation_id),
                    decision=validation.decision.value,
                    timestamp=validation.timestamp,
                    previous_hash=previous_hash
                )
                
                from .database import AuditLogTable
                
                await session.execute(
                    insert(AuditLogTable).values(
                        log_id=str(uuid4()),
                        timestamp=validation.timestamp,
                        event_id=str(event.event_id),
                        validation_id=str(validation.validation_id),
                        action_type=event.event_type.value,
                        decision=validation.decision.value,
                        benefit_score=validation.benefit_score,
                        harm_score=validation.harm_score,
                        api=event.api.value,
                        domain=event.domain.value,
                        jurisdiction=event.jurisdiction.value,
                        previous_hash=previous_hash,
                        current_hash=current_hash
                    )
                )
        
        except Exception as e:
            logger.error(f"Error storing validation: {e}", exc_info=True)


# ============================================================================
# MAIN - For standalone testing
# ============================================================================

if __name__ == "__main__":
    import asyncio
    from .models import LearningEventType
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    async def test():
        """Test constitutional validator"""
        validator = ConstitutionalValidator()
        
        # Test 1: Good learning event (should approve)
        good_event = LearningEvent(
            event_type=LearningEventType.OUTCOME,
            domain=DomainType.TASK_BASED,
            api=APIType.BUE,
            inputs={"company": "Test Corp", "industry": "technology"},
            predicted={"risk_score": 0.25},
            actual={"default": False},
            learning_signal=0.8
        )
        
        validation = await validator.validate_learning(good_event)
        print(f"\nTest 1 - Good event:")
        print(f"  Decision: {validation.decision}")
        print(f"  Benefit: {validation.benefit_score:.1f}")
        print(f"  Harm: {validation.harm_score:.1f}")
        print(f"  Net Benefit: {validation.net_benefit:.1f}")
        
        # Test 2: Privacy violation (should reject)
        bad_event = LearningEvent(
            event_type=LearningEventType.OUTCOME,
            domain=DomainType.TASK_BASED,
            api=APIType.BUE,
            inputs={"ssn": "123-45-6789", "name": "John Doe"},
            predicted={"risk_score": 0.5},
            learning_signal=0.5
        )
        
        validation = await validator.validate_learning(bad_event)
        print(f"\nTest 2 - Privacy violation:")
        print(f"  Decision: {validation.decision}")
        print(f"  Violations: {validation.violations}")
        print(f"  Reason: {validation.decision_reason}")
        
        # Test 3: Bias risk (should reject)
        bias_event = LearningEvent(
            event_type=LearningEventType.OUTCOME,
            domain=DomainType.TASK_BASED,
            api=APIType.BUE,
            inputs={"race": "white", "gender": "male"},
            predicted={"approval": True},
            learning_signal=0.5
        )
        
        validation = await validator.validate_learning(bias_event)
        print(f"\nTest 3 - Bias risk:")
        print(f"  Decision: {validation.decision}")
        print(f"  Violations: {validation.violations}")
        
        print("\n✅ Constitutional validator tests completed!")
    
    asyncio.run(test())
