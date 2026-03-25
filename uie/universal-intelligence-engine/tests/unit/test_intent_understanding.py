"""
Unit tests for Intent Understanding Layer
"""

import pytest
from uie.core.intent_understanding import IntentClassifier, IntentEnhancer, TaskType, Domain
from uie.core.schemas import Envelope, Intent, Payload


class TestIntentClassifier:
    """Test intent classification."""
    
    def setup_method(self):
        """Setup for each test."""
        self.classifier = IntentClassifier()
    
    def test_query_classification(self):
        """Test query task classification."""
        envelope = Envelope(
            tenant_id="test",
            actor="test_user",
            intent=Intent(task="unknown"),
            payload=Payload(text="What is the weather today?")
        )
        
        result = self.classifier.classify(envelope)
        
        assert result.task == TaskType.QUERY
        assert result.confidence > 0.5
        assert len(result.keywords_matched) > 0
    
    def test_analysis_classification(self):
        """Test analysis task classification."""
        envelope = Envelope(
            tenant_id="test",
            actor="test_user",
            intent=Intent(task="unknown"),
            payload=Payload(text="Analyze the financial impact of this merger")
        )
        
        result = self.classifier.classify(envelope)
        
        assert result.task == TaskType.ANALYSIS
        assert Domain.FINANCE in result.domains
    
    def test_action_classification(self):
        """Test action task classification."""
        envelope = Envelope(
            tenant_id="test",
            actor="test_user",
            intent=Intent(task="unknown"),
            payload=Payload(text="Create a quarterly report for our stakeholders")
        )
        
        result = self.classifier.classify(envelope)
        
        assert result.task == TaskType.ACTION
        assert result.confidence > 0.5
    
    def test_domain_classification_finance(self):
        """Test financial domain detection."""
        envelope = Envelope(
            tenant_id="test",
            actor="test_user",
            intent=Intent(task="query"),
            payload=Payload(text="What's the current NPV of our investment portfolio?")
        )
        
        result = self.classifier.classify(envelope)
        
        assert Domain.FINANCE in result.domains
    
    def test_domain_classification_healthcare(self):
        """Test healthcare domain detection."""
        envelope = Envelope(
            tenant_id="test",
            actor="test_user",
            intent=Intent(task="query"),
            payload=Payload(text="What are the treatment options for this patient?")
        )
        
        result = self.classifier.classify(envelope)
        
        assert Domain.HEALTHCARE in result.domains
    
    def test_tool_recommendations(self):
        """Test tool recommendation logic."""
        envelope = Envelope(
            tenant_id="test",
            actor="test_user",
            intent=Intent(task="analysis", domains=["finance"]),
            payload=Payload(text="Analyze this investment opportunity")
        )
        
        result = self.classifier.classify(envelope)
        
        assert "analyze_risk" in result.suggested_tools
        assert "enrich" in result.suggested_tools


class TestIntentEnhancer:
    """Test intent enhancement."""
    
    def setup_method(self):
        """Setup for each test."""
        self.enhancer = IntentEnhancer()
    
    def test_enhance_missing_task(self):
        """Test enhancement when task is missing."""
        envelope = Envelope(
            tenant_id="test",
            actor="test_user",
            intent=Intent(task="unknown"),
            payload=Payload(text="What is machine learning?")
        )
        
        enhanced = self.enhancer.enhance(envelope)
        
        assert enhanced.intent.task != "unknown"
        assert enhanced.intent.task == TaskType.QUERY.value
    
    def test_enhance_missing_domains(self):
        """Test enhancement when domains are missing."""
        envelope = Envelope(
            tenant_id="test",
            actor="test_user",
            intent=Intent(task="query", domains=[]),
            payload=Payload(text="How do hospitals manage patient data?")
        )
        
        enhanced = self.enhancer.enhance(envelope)
        
        assert len(enhanced.intent.domains) > 0
        assert "healthcare" in enhanced.intent.domains
    
    def test_preserve_existing_intent(self):
        """Test that existing intent is preserved."""
        envelope = Envelope(
            tenant_id="test",
            actor="test_user",
            intent=Intent(
                task="analysis",
                domains=["finance"],
                sensitivity="confidential"
            ),
            payload=Payload(text="Analyze financial data")
        )
        
        enhanced = self.enhancer.enhance(envelope)
        
        assert enhanced.intent.task == "analysis"
        assert enhanced.intent.domains == ["finance"]
        assert enhanced.intent.sensitivity == "confidential"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
