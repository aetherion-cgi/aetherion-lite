"""
Context Optimization

Three-stage optimization:
1. Select: Retrieval/filtering of relevant data
2. Compress: Map-reduce to condense information
3. Budget: Token allocation per model constraints

Goal: 40% token reduction without losing quality.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class OptimizationResult:
    """Result of context optimization."""
    optimized_context: str
    original_tokens: int
    optimized_tokens: int
    reduction_percentage: float
    sections_kept: List[str]
    sections_dropped: List[str]


class ContextOptimizer:
    """
    Optimizes context to fit within token budgets.
    
    Strategies:
    - Relevance-based filtering
    - Summarization of low-priority sections
    - Removal of redundant information
    """
    
    def __init__(self, target_reduction: float = 0.4):
        """
        Args:
            target_reduction: Target reduction (0.4 = 40% reduction)
        """
        self.target_reduction = target_reduction
    
    def optimize(
        self,
        context: Dict[str, Any],
        query: str,
        max_tokens: int
    ) -> OptimizationResult:
        """
        Optimize context to fit within token budget.
        
        Args:
            context: Full context data
            query: User's query (for relevance scoring)
            max_tokens: Maximum allowed tokens
        
        Returns:
            OptimizationResult with optimized context
        """
        # 1. Select relevant sections
        relevant_sections = self._select_relevant(context, query)
        
        # 2. Estimate tokens
        original_tokens = self._estimate_tokens(context)
        current_tokens = self._estimate_tokens(relevant_sections)
        
        # 3. Compress if still over budget
        if current_tokens > max_tokens:
            compressed = self._compress(relevant_sections, max_tokens)
            final_tokens = self._estimate_tokens(compressed)
        else:
            compressed = relevant_sections
            final_tokens = current_tokens
        
        # 4. Format as text
        optimized_text = self._format_as_text(compressed)
        
        reduction = 1 - (final_tokens / original_tokens) if original_tokens > 0 else 0
        
        return OptimizationResult(
            optimized_context=optimized_text,
            original_tokens=original_tokens,
            optimized_tokens=final_tokens,
            reduction_percentage=reduction * 100,
            sections_kept=list(compressed.keys()),
            sections_dropped=[k for k in context.keys() if k not in compressed]
        )
    
    def _select_relevant(
        self,
        context: Dict[str, Any],
        query: str
    ) -> Dict[str, Any]:
        """
        Select relevant sections based on query.
        
        Simple keyword matching for now.
        Could be enhanced with embeddings/semantic search.
        """
        query_lower = query.lower()
        query_keywords = set(query_lower.split())
        
        scored_sections = []
        
        for key, value in context.items():
            # Score based on keyword overlap
            value_text = str(value).lower()
            overlap = len(query_keywords & set(value_text.split()))
            score = overlap / len(query_keywords) if query_keywords else 0
            
            scored_sections.append((key, value, score))
        
        # Keep top 70% by score
        scored_sections.sort(key=lambda x: x[2], reverse=True)
        threshold = int(len(scored_sections) * 0.7)
        
        return {
            key: value
            for key, value, score in scored_sections[:threshold]
        }
    
    def _compress(
        self,
        sections: Dict[str, Any],
        max_tokens: int
    ) -> Dict[str, Any]:
        """
        Compress sections to fit within token budget.
        
        Strategies:
        - Truncate long sections
        - Remove low-priority fields
        - Summarize lists
        """
        compressed = {}
        token_budget = max_tokens
        
        for key, value in sections.items():
            value_tokens = self._estimate_tokens({key: value})
            
            if token_budget <= 0:
                break
            
            if value_tokens <= token_budget:
                compressed[key] = value
                token_budget -= value_tokens
            else:
                # Truncate to fit
                if isinstance(value, str):
                    # Truncate string
                    chars_to_keep = int(len(value) * (token_budget / value_tokens))
                    compressed[key] = value[:chars_to_keep] + "..."
                elif isinstance(value, list):
                    # Keep first few items
                    items_to_keep = max(1, int(len(value) * (token_budget / value_tokens)))
                    compressed[key] = value[:items_to_keep]
                else:
                    compressed[key] = value
                
                token_budget = 0
        
        return compressed
    
    def _estimate_tokens(self, data: Any) -> int:
        """
        Estimate token count.
        
        Simple heuristic: ~4 characters per token.
        """
        text = str(data)
        return len(text) // 4
    
    def _format_as_text(self, data: Dict[str, Any]) -> str:
        """Format optimized context as readable text."""
        parts = []
        
        for key, value in data.items():
            if isinstance(value, (str, int, float)):
                parts.append(f"{key}: {value}")
            elif isinstance(value, list):
                parts.append(f"{key}: {', '.join(str(v) for v in value[:5])}")
            elif isinstance(value, dict):
                nested = ", ".join(f"{k}={v}" for k, v in list(value.items())[:3])
                parts.append(f"{key}: {{{nested}}}")
            else:
                parts.append(f"{key}: {str(value)[:100]}")
        
        return "\n".join(parts)


class TokenBudgetAllocator:
    """
    Allocates token budget across different context sections.
    
    Prioritizes based on:
    - Relevance to query
    - Recency of data
    - Source authority
    """
    
    def __init__(self):
        self.priorities = {
            "query_results": 0.4,  # 40% to direct query results
            "enrichment": 0.3,     # 30% to enrichment data
            "analysis": 0.2,       # 20% to analysis results
            "metadata": 0.1        # 10% to metadata
        }
    
    def allocate(
        self,
        total_budget: int,
        sections: Dict[str, Any]
    ) -> Dict[str, int]:
        """
        Allocate token budget to sections.
        
        Returns:
            Dict of section -> allocated tokens
        """
        allocation = {}
        
        for section, data in sections.items():
            # Determine section type
            section_type = self._classify_section(section)
            priority = self.priorities.get(section_type, 0.1)
            
            allocation[section] = int(total_budget * priority)
        
        return allocation
    
    def _classify_section(self, section_name: str) -> str:
        """Classify section by name."""
        section_lower = section_name.lower()
        
        if "result" in section_lower or "answer" in section_lower:
            return "query_results"
        elif "enrich" in section_lower or "context" in section_lower:
            return "enrichment"
        elif "analysis" in section_lower or "compute" in section_lower:
            return "analysis"
        else:
            return "metadata"
