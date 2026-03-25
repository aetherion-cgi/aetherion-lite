"""
Multi-LLM Formatters

Adapters for different LLM providers:
- OpenAI GPT (JSON tool calls)
- Anthropic Claude (XML + tools)
- Google Gemini (multimodal)

Each adapter implements common interface:
- format_prompt(): Convert to provider format
- parse_response(): Parse provider response to NormalizedResult
"""

from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
from enum import Enum


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


class BaseLLMAdapter(ABC):
    """
    Base adapter interface for LLM providers.
    
    All adapters must implement:
    - format_prompt(): Convert UIE request to provider format
    - parse_response(): Parse provider response to UIE format
    """
    
    @abstractmethod
    def format_prompt(
        self,
        query: str,
        context: str,
        tools: List[Dict[str, Any]],
        model_id: str
    ) -> Dict[str, Any]:
        """
        Format prompt for this provider.
        
        Args:
            query: User's query
            context: Optimized context
            tools: Available tools
            model_id: Specific model to use
        
        Returns:
            Provider-specific payload
        """
        pass
    
    @abstractmethod
    def parse_response(
        self,
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Parse provider response to UIE format.
        
        Returns:
            Dict with 'text', 'tool_calls', 'citations', etc.
        """
        pass


class GPTAdapter(BaseLLMAdapter):
    """
    Adapter for OpenAI GPT models.
    
    Features:
    - JSON tool calls
    - Function calling
    - JSON mode for structured output
    """
    
    def format_prompt(
        self,
        query: str,
        context: str,
        tools: List[Dict[str, Any]],
        model_id: str
    ) -> Dict[str, Any]:
        """Format prompt for GPT."""
        messages = [
            {
                "role": "system",
                "content": "You are an AI assistant powered by Collective General Intelligence."
            },
            {
                "role": "user",
                "content": f"Query: {query}\n\nContext:\n{context}\n\nProvide a comprehensive answer with citations."
            }
        ]
        
        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        # Add tools if available
        if tools:
            payload["tools"] = self._format_tools(tools)
            payload["tool_choice"] = "auto"
        
        return payload
    
    def _format_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format tools for GPT function calling."""
        formatted = []
        
        for tool in tools:
            formatted.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool.get("parameters", {})
                }
            })
        
        return formatted
    
    def parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse GPT response."""
        choice = response["choices"][0]
        message = choice["message"]
        
        result = {
            "text": message.get("content", ""),
            "tool_calls": [],
            "citations": [],  # Would extract from text
            "finish_reason": choice["finish_reason"]
        }
        
        # Parse tool calls if present
        if "tool_calls" in message:
            for tool_call in message["tool_calls"]:
                result["tool_calls"].append({
                    "id": tool_call["id"],
                    "name": tool_call["function"]["name"],
                    "arguments": tool_call["function"]["arguments"]
                })
        
        return result


class ClaudeAdapter(BaseLLMAdapter):
    """
    Adapter for Anthropic Claude models.
    
    Features:
    - XML formatting for structured data
    - Tool use
    - Long context windows
    """
    
    def format_prompt(
        self,
        query: str,
        context: str,
        tools: List[Dict[str, Any]],
        model_id: str
    ) -> Dict[str, Any]:
        """Format prompt for Claude."""
        # Claude prefers XML for structured data
        formatted_context = f"<context>\n{context}\n</context>"
        
        messages = [
            {
                "role": "user",
                "content": f"<query>{query}</query>\n\n{formatted_context}\n\nProvide a comprehensive answer with citations."
            }
        ]
        
        payload = {
            "model": model_id,
            "messages": messages,
            "max_tokens": 4096,
            "temperature": 0.7,
            "system": "You are an AI assistant powered by Collective General Intelligence. Provide accurate, well-cited responses."
        }
        
        # Add tools if available
        if tools:
            payload["tools"] = self._format_tools(tools)
        
        return payload
    
    def _format_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format tools for Claude."""
        formatted = []
        
        for tool in tools:
            formatted.append({
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool.get("parameters", {})
            })
        
        return formatted
    
    def parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Claude response."""
        content = response["content"]
        
        result = {
            "text": "",
            "tool_calls": [],
            "citations": [],
            "stop_reason": response.get("stop_reason")
        }
        
        # Parse content blocks
        for block in content:
            if block["type"] == "text":
                result["text"] += block["text"]
            elif block["type"] == "tool_use":
                result["tool_calls"].append({
                    "id": block["id"],
                    "name": block["name"],
                    "input": block["input"]
                })
        
        return result


class GeminiAdapter(BaseLLMAdapter):
    """
    Adapter for Google Gemini models.
    
    Features:
    - Multimodal input (text, images, video)
    - Very long context windows
    - JSON mode
    """
    
    def format_prompt(
        self,
        query: str,
        context: str,
        tools: List[Dict[str, Any]],
        model_id: str
    ) -> Dict[str, Any]:
        """Format prompt for Gemini."""
        contents = [
            {
                "role": "user",
                "parts": [
                    {
                        "text": f"Query: {query}\n\nContext:\n{context}\n\nProvide a comprehensive answer with citations."
                    }
                ]
            }
        ]
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 8192,
                "topP": 0.95
            }
        }
        
        # Add tools if available
        if tools:
            payload["tools"] = [{"functionDeclarations": self._format_tools(tools)}]
        
        return payload
    
    def _format_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format tools for Gemini."""
        formatted = []
        
        for tool in tools:
            formatted.append({
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool.get("parameters", {})
            })
        
        return formatted
    
    def parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Gemini response."""
        candidate = response["candidates"][0]
        content = candidate["content"]
        
        result = {
            "text": "",
            "tool_calls": [],
            "citations": [],
            "finish_reason": candidate.get("finishReason")
        }
        
        # Parse parts
        for part in content["parts"]:
            if "text" in part:
                result["text"] += part["text"]
            elif "functionCall" in part:
                result["tool_calls"].append({
                    "name": part["functionCall"]["name"],
                    "args": part["functionCall"]["args"]
                })
        
        return result


class AdapterFactory:
    """Factory for creating LLM adapters."""
    
    @staticmethod
    def create(provider: LLMProvider) -> BaseLLMAdapter:
        """
        Create adapter for provider.
        
        Args:
            provider: LLM provider
        
        Returns:
            Appropriate adapter instance
        """
        if provider == LLMProvider.OPENAI:
            return GPTAdapter()
        elif provider == LLMProvider.ANTHROPIC:
            return ClaudeAdapter()
        elif provider == LLMProvider.GOOGLE:
            return GeminiAdapter()
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    @staticmethod
    def from_model_id(model_id: str) -> BaseLLMAdapter:
        """
        Create adapter from model ID.
        
        Args:
            model_id: Model identifier (e.g., "gpt-4", "claude-3-opus")
        
        Returns:
            Appropriate adapter instance
        """
        model_lower = model_id.lower()
        
        if "gpt" in model_lower or "openai" in model_lower:
            return GPTAdapter()
        elif "claude" in model_lower or "anthropic" in model_lower:
            return ClaudeAdapter()
        elif "gemini" in model_lower or "google" in model_lower:
            return GeminiAdapter()
        else:
            raise ValueError(f"Cannot determine provider from model_id: {model_id}")
