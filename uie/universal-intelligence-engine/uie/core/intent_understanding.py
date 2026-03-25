"""
Intent Understanding Layer

Analyzes incoming queries to determine:
- Task type (query, analysis, action, etc.)
- Relevant domains
- Sensitivity level
- Required tools

Uses rule-based classification + optional LLM fallback for low-confidence cases.
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import re
from enum import Enum

from uie.core.schemas import Intent, Envelope


class TaskType(str, Enum):
    """Supported task types."""
    QUERY = "query"
    ANALYSIS = "analysis"
    ACTION = "action"
    SYNTHESIS = "synthesis"
    PLANNING = "planning"
    VALIDATION = "validation"
    UNKNOWN = "unknown"


class Domain(str, Enum):
    """Supported domains."""
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    ENGINEERING = "engineering"
    LEGAL = "legal"
    SCIENCE = "science"
    BUSINESS = "business"
    TECHNOLOGY = "technology"
    GENERAL = "general"


@dataclass
class ClassificationResult:
    """Result of intent classification."""
    task: TaskType
    domains: List[Domain]
    confidence: float  # 0.0 to 1.0
    keywords_matched: List[str]
    suggested_tools: List[str]


class IntentClassifier:
    """
    Rule-based + LLM fallback intent classifier.
    
    Design:
    - Fast rule-based matching for common patterns (≥90% accuracy, <50ms)
    - LLM router for ambiguous cases (used when confidence < 0.7)
    """
    
    def __init__(self):
        # Task classification rules
        self.task_patterns = {
            TaskType.QUERY: [
                r'\bwhat\b', r'\bwho\b', r'\bwhere\b', r'\bwhen\b', r'\bhow many\b',
                r'\bshow me\b', r'\bfind\b', r'\btell me\b', r'\bexplain\b',
                r'\bdefine\b', r'\bdescribe\b'
            ],
            TaskType.ANALYSIS: [
                r'\banalyze\b', r'\bassess\b', r'\bevaluate\b', r'\bcompare\b',
                r'\bexamine\b', r'\binvestigate\b', r'\bstudy\b', r'\breview\b',
                r'\bwhat.*impact\b', r'\bhow.*affect\b', r'\btrends?\b'
            ],
            TaskType.ACTION: [
                r'\bcreate\b', r'\bgenerate\b', r'\bbuild\b', r'\bmake\b',
                r'\bwrite\b', r'\bdraft\b', r'\bprepare\b', r'\bdevelop\b',
                r'\bdesign\b', r'\bimplement\b'
            ],
            TaskType.SYNTHESIS: [
                r'\bsynthesize\b', r'\bcombine\b', r'\bmerge\b', r'\bintegrate\b',
                r'\bsummarize\b', r'\baggregate\b', r'\bconsolidate\b'
            ],
            TaskType.PLANNING: [
                r'\bplan\b', r'\bschedule\b', r'\borganize\b', r'\bstrategy\b',
                r'\broadmap\b', r'\bshould (i|we)\b', r'\bhow (can|should|do) (i|we)\b'
            ],
            TaskType.VALIDATION: [
                r'\bvalidate\b', r'\bverify\b', r'\bcheck\b', r'\bconfirm\b',
                r'\bis.*correct\b', r'\bis.*valid\b', r'\bis.*true\b'
            ]
        }
        
        # Domain classification keywords
        self.domain_keywords = {
            Domain.FINANCE: [
                'revenue', 'profit', 'investment', 'stock', 'market', 'financial',
                'valuation', 'npv', 'irr', 'dcf', 'portfolio', 'fund', 'asset',
                'liability', 'equity', 'debt', 'capital', 'dividend', 'earnings'
            ],
            Domain.HEALTHCARE: [
                'patient', 'medical', 'diagnosis', 'treatment', 'clinical', 'hospital',
                'drug', 'medication', 'disease', 'symptom', 'healthcare', 'doctor',
                'nurse', 'therapy', 'surgery', 'lab', 'test'
            ],
            Domain.ENGINEERING: [
                'design', 'system', 'architecture', 'infrastructure', 'technical',
                'engineering', 'build', 'construction', 'structural', 'mechanical',
                'electrical', 'civil', 'software', 'hardware', 'specification'
            ],
            Domain.LEGAL: [
                'legal', 'law', 'regulation', 'compliance', 'contract', 'agreement',
                'litigation', 'court', 'attorney', 'counsel', 'statute', 'policy',
                'terms', 'liability', 'intellectual property', 'patent', 'trademark'
            ],
            Domain.SCIENCE: [
                'research', 'experiment', 'hypothesis', 'data', 'analysis', 'study',
                'scientific', 'laboratory', 'theory', 'evidence', 'methodology',
                'peer review', 'publication', 'discovery'
            ],
            Domain.BUSINESS: [
                'business', 'company', 'enterprise', 'organization', 'strategy',
                'operations', 'management', 'marketing', 'sales', 'customer',
                'product', 'service', 'market share', 'competitive', 'partnership'
            ],
            Domain.TECHNOLOGY: [
                'technology', 'software', 'hardware', 'ai', 'ml', 'algorithm',
                'database', 'cloud', 'api', 'code', 'programming', 'development',
                'deployment', 'security', 'network', 'platform'
            ]
        }
        
        # Tool recommendations based on task + domain
        self.tool_recommendations = {
            (TaskType.QUERY, Domain.FINANCE): ['enrich', 'synthesize'],
            (TaskType.ANALYSIS, Domain.FINANCE): ['enrich', 'analyze_risk', 'compute', 'synthesize'],
            (TaskType.ANALYSIS, Domain.GENERAL): ['enrich', 'compute', 'synthesize'],
            (TaskType.ACTION, Domain.GENERAL): ['plan', 'enrich', 'validate'],
            (TaskType.PLANNING, Domain.GENERAL): ['plan', 'enrich', 'analyze_risk'],
            (TaskType.SYNTHESIS, Domain.GENERAL): ['enrich', 'synthesize'],
            (TaskType.VALIDATION, Domain.GENERAL): ['validate', 'enrich'],
        }
    
    def classify(self, envelope: Envelope) -> ClassificationResult:
        """
        Classify the intent of an envelope.
        
        Args:
            envelope: The request envelope
        
        Returns:
            Classification result with task, domains, confidence
        """
        # Extract text to analyze
        text = self._extract_text(envelope)
        text_lower = text.lower()
        
        # Classify task
        task, task_confidence, task_keywords = self._classify_task(text_lower)
        
        # Classify domains
        domains, domain_confidence = self._classify_domains(text_lower)
        
        # Overall confidence
        confidence = (task_confidence + domain_confidence) / 2
        
        # Recommend tools
        tools = self._recommend_tools(task, domains)
        
        return ClassificationResult(
            task=task,
            domains=domains,
            confidence=confidence,
            keywords_matched=task_keywords,
            suggested_tools=tools
        )
    
    def _extract_text(self, envelope: Envelope) -> str:
        """Extract text from envelope payload."""
        if envelope.payload.text:
            return envelope.payload.text
        elif envelope.payload.json_data:
            # Try to extract text from json
            return str(envelope.payload.json_data)
        return ""
    
    def _classify_task(self, text: str) -> Tuple[TaskType, float, List[str]]:
        """
        Classify task type using pattern matching.
        
        Returns:
            (task_type, confidence, matched_keywords)
        """
        scores = {}
        matched_keywords = {}
        
        for task_type, patterns in self.task_patterns.items():
            score = 0
            keywords = []
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    score += len(matches)
                    keywords.extend(matches)
            scores[task_type] = score
            matched_keywords[task_type] = keywords
        
        # Find best match
        if not any(scores.values()):
            return TaskType.UNKNOWN, 0.0, []
        
        best_task = max(scores, key=scores.get)
        total_score = sum(scores.values())
        confidence = scores[best_task] / total_score if total_score > 0 else 0.0
        
        return best_task, confidence, matched_keywords[best_task]
    
    def _classify_domains(self, text: str) -> Tuple[List[Domain], float]:
        """
        Classify domains using keyword matching.
        
        Returns:
            (domains, confidence)
        """
        scores = {}
        
        for domain, keywords in self.domain_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in text:
                    score += text.count(keyword)
            scores[domain] = score
        
        # Return domains with score > 0
        active_domains = [domain for domain, score in scores.items() if score > 0]
        
        if not active_domains:
            active_domains = [Domain.GENERAL]
            confidence = 0.5
        else:
            # Confidence based on score distribution
            total_score = sum(scores.values())
            top_score = max(scores.values())
            confidence = top_score / total_score if total_score > 0 else 0.0
        
        return active_domains, confidence
    
    def _recommend_tools(self, task: TaskType, domains: List[Domain]) -> List[str]:
        """Recommend tools based on task and domains."""
        tools = set()
        
        # Check specific combinations
        for domain in domains:
            key = (task, domain)
            if key in self.tool_recommendations:
                tools.update(self.tool_recommendations[key])
        
        # Add general recommendations
        general_key = (task, Domain.GENERAL)
        if general_key in self.tool_recommendations:
            tools.update(self.tool_recommendations[general_key])
        
        # Default tools if nothing matched
        if not tools:
            tools = {'enrich', 'synthesize'}
        
        return list(tools)


class IntentEnhancer:
    """
    Enhances the Intent object in an envelope with classification results.
    """
    
    def __init__(self):
        self.classifier = IntentClassifier()
    
    def enhance(self, envelope: Envelope) -> Envelope:
        """
        Enhance envelope with classified intent.
        
        Updates envelope.intent with classified information if not already present.
        """
        # Classify intent
        classification = self.classifier.classify(envelope)
        
        # Update intent if fields are missing or default
        if not envelope.intent.task or envelope.intent.task == "unknown":
            envelope.intent.task = classification.task.value
        
        if not envelope.intent.domains:
            envelope.intent.domains = [d.value for d in classification.domains]
        
        # Add classification metadata to trace
        envelope.trace.baggage['intent_confidence'] = str(classification.confidence)
        envelope.trace.baggage['intent_keywords'] = ','.join(classification.keywords_matched[:5])
        envelope.trace.baggage['suggested_tools'] = ','.join(classification.suggested_tools)
        
        return envelope


# ============================================================================
# LOW-CONFIDENCE FALLBACK (LLM Router)
# ============================================================================

class LLMIntentRouter:
    """
    LLM-based intent classification for ambiguous cases.
    
    Used when rule-based classifier has confidence < 0.7.
    Makes a single LLM call with a specialized routing prompt.
    """
    
    def __init__(self, llm_adapter):
        """
        Args:
            llm_adapter: Adapter for calling LLM (GPT/Claude/Gemini)
        """
        self.llm_adapter = llm_adapter
        self.routing_prompt_template = """
Classify the following query's intent.

Query: {query}

Return JSON in this exact format:
{{
    "task": "query|analysis|action|synthesis|planning|validation",
    "domains": ["finance", "healthcare", etc.],
    "confidence": 0.0-1.0,
    "suggested_tools": ["tool1", "tool2"]
}}

ONLY return valid JSON. No other text.
"""
    
    async def classify(self, text: str) -> Dict:
        """
        Classify intent using LLM.
        
        Returns:
            Dict with task, domains, confidence, suggested_tools
        """
        prompt = self.routing_prompt_template.format(query=text)
        
        # Call LLM (async)
        response = await self.llm_adapter.complete(
            prompt=prompt,
            max_tokens=200,
            temperature=0.0,  # Deterministic
            json_mode=True
        )
        
        # Parse JSON response
        import json
        return json.loads(response)
