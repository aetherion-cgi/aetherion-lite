"""
Response Synthesis Engine

Builds a Claim Graph from tool outputs and synthesizes into coherent response:
- Merges data from multiple sources
- Tracks citations and provenance
- Optional LLM "unify" pass for fluency
- Always includes citations, never exposes chain-of-thought
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from uie.core.schemas import Citation, StepResult


@dataclass
class Claim:
    """A factual claim with provenance."""
    text: str
    sources: List[str]
    confidence: float
    timestamp: Optional[datetime] = None


class ClaimGraph:
    """
    Graph of claims and their relationships.
    
    Tracks:
    - Individual claims
    - Sources for each claim
    - Relationships between claims
    """
    
    def __init__(self):
        self.claims: List[Claim] = []
        self.source_map: Dict[str, List[int]] = {}  # source_id -> claim indices
    
    def add_claim(self, text: str, source: str, confidence: float = 1.0):
        """Add a claim to the graph."""
        claim = Claim(
            text=text,
            sources=[source],
            confidence=confidence,
            timestamp=datetime.utcnow()
        )
        
        claim_idx = len(self.claims)
        self.claims.append(claim)
        
        if source not in self.source_map:
            self.source_map[source] = []
        self.source_map[source].append(claim_idx)
    
    def merge_duplicate_claims(self):
        """Merge claims that say the same thing from different sources."""
        # Simple implementation: exact text match
        merged = {}
        
        for claim in self.claims:
            if claim.text in merged:
                # Merge sources
                merged[claim.text].sources.extend(claim.sources)
                # Average confidence
                merged[claim.text].confidence = (
                    merged[claim.text].confidence + claim.confidence
                ) / 2
            else:
                merged[claim.text] = claim
        
        self.claims = list(merged.values())
    
    def get_citations(self) -> List[Citation]:
        """Convert claims to citations."""
        citations = []
        
        for claim in self.claims:
            for source in claim.sources:
                citations.append(Citation(
                    source=source,
                    excerpt=claim.text[:200],  # Truncate
                    confidence=claim.confidence,
                    timestamp=claim.timestamp
                ))
        
        return citations


class ResponseSynthesizer:
    """
    Synthesizes tool results into a coherent response.
    
    Process:
    1. Extract claims from each tool result
    2. Build claim graph
    3. Merge duplicate claims
    4. Optional: LLM unify pass for fluency
    5. Format with citations
    """
    
    def __init__(self, use_llm_unify: bool = False):
        self.use_llm_unify = use_llm_unify
    
    async def synthesize(
        self,
        envelope,
        step_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Synthesize tool results into final response.
        
        Returns:
            Dict with 'text', 'structured', 'citations'
        """
        # 1. Build claim graph
        claim_graph = ClaimGraph()
        
        for step_id, result in step_results.items():
            if result.status.value == "completed" and result.output:
                self._extract_claims(
                    result.output,
                    step_id,
                    claim_graph
                )
        
        # 2. Merge duplicates
        claim_graph.merge_duplicate_claims()
        
        # 3. Deterministic synthesis
        text = self._deterministic_merge(claim_graph)
        
        # 4. Optional LLM unify pass
        if self.use_llm_unify and len(text) > 500:
            text = await self._llm_unify_pass(text, envelope)
        
        # 5. Get citations
        citations = claim_graph.get_citations()
        
        return {
            "text": text,
            "structured": None,  # TODO: Handle structured output
            "citations": citations
        }
    
    def _extract_claims(
        self,
        output: Dict[str, Any],
        source_id: str,
        claim_graph: ClaimGraph
    ):
        """Extract claims from tool output."""
        # Handle different output formats
        if isinstance(output, dict):
            if "claims" in output:
                # Explicit claims
                for claim_data in output["claims"]:
                    claim_graph.add_claim(
                        text=claim_data["text"],
                        source=source_id,
                        confidence=claim_data.get("confidence", 1.0)
                    )
            elif "result" in output:
                # Generic result
                claim_graph.add_claim(
                    text=str(output["result"]),
                    source=source_id,
                    confidence=1.0
                )
            else:
                # Treat entire output as one claim
                claim_graph.add_claim(
                    text=str(output),
                    source=source_id,
                    confidence=0.8
                )
    
    def _deterministic_merge(self, claim_graph: ClaimGraph) -> str:
        """
        Merge claims deterministically without LLM.
        
        Simple approach: Join claims with proper connectives.
        """
        if not claim_graph.claims:
            return "No results found."
        
        # Sort by confidence
        sorted_claims = sorted(
            claim_graph.claims,
            key=lambda c: c.confidence,
            reverse=True
        )
        
        # Build text
        parts = []
        for claim in sorted_claims:
            # Add claim with source attribution
            source_str = ", ".join(claim.sources[:2])  # Max 2 sources
            if len(claim.sources) > 2:
                source_str += f" and {len(claim.sources) - 2} other(s)"
            
            parts.append(f"{claim.text} (Source: {source_str})")
        
        return "\n\n".join(parts)
    
    async def _llm_unify_pass(
        self,
        text: str,
        envelope
    ) -> str:
        """
        Optional LLM pass to improve fluency.
        
        Makes text more readable while preserving all information.
        """
        # TODO: Implement LLM call for fluency
        # For now, just return original text
        return text
