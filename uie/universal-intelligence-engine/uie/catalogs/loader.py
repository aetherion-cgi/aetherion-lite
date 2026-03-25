"""
Catalog system for UIE.

Hot-reloadable catalogs for:
1. Tools (Cortex Gateway tools only)
2. Prompts (templates per intent × domain × model)
3. Model Capabilities (what each model can do)
"""

from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field, validator
import yaml
import json
from pathlib import Path
from datetime import datetime
import hashlib


# ============================================================================
# TOOL CATALOG
# ============================================================================

class ToolParameter(BaseModel):
    """Parameter definition for a tool."""
    
    name: str
    type: str  # string, number, boolean, object, array
    description: str
    required: bool = False
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None


class ToolMetadata(BaseModel):
    """Metadata about a tool."""
    
    category: str = Field(..., description="Category: data, compute, analysis, etc.")
    latency_estimate_ms: float = Field(..., description="Typical latency")
    cost_per_call: Optional[float] = Field(None, description="Cost in USD")
    requires_auth: bool = Field(default=True)
    rate_limit_per_minute: Optional[int] = None


class ToolDefinition(BaseModel):
    """
    Definition of a Cortex Gateway tool.
    
    UIE only knows about Cortex tools - never calls engines directly.
    """
    
    name: str = Field(..., description="Unique tool identifier")
    description: str = Field(..., description="What this tool does")
    parameters: List[ToolParameter]
    returns: str = Field(..., description="Description of return value")
    metadata: ToolMetadata
    
    # Version tracking
    version: str = "1.0.0"
    deprecated: bool = False
    replacement: Optional[str] = Field(
        None,
        description="If deprecated, what tool replaces this"
    )


class ToolCatalog(BaseModel):
    """
    Complete catalog of available tools.
    
    This is loaded from YAML and hot-reloadable.
    """
    
    tools: Dict[str, ToolDefinition] = Field(
        default_factory=dict,
        description="Tool name -> definition mapping"
    )
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0.0"
    
    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool by name."""
        return self.tools.get(name)
    
    def get_tools_by_category(self, category: str) -> List[ToolDefinition]:
        """Get all tools in a category."""
        return [
            tool for tool in self.tools.values()
            if tool.metadata.category == category
        ]
    
    def is_tool_available(self, name: str) -> bool:
        """Check if a tool is available and not deprecated."""
        tool = self.get_tool(name)
        return tool is not None and not tool.deprecated


# ============================================================================
# PROMPT CATALOG
# ============================================================================

class PromptVariable(BaseModel):
    """A variable that can be substituted in a prompt."""
    
    name: str
    description: str
    required: bool = True
    default: Optional[str] = None


class PromptTemplate(BaseModel):
    """
    A prompt template for a specific intent × domain × model combination.
    """
    
    # Identity
    template_id: str = Field(..., description="Unique identifier")
    name: str
    description: str
    
    # Targeting
    intent_task: str = Field(..., description="Task from Intent.task")
    domains: List[str] = Field(
        default_factory=list,
        description="Applicable domains. Empty = all domains"
    )
    model_tags: List[str] = Field(
        ...,
        description="Which models this is for: gpt, claude, gemini, etc."
    )
    
    # Template content
    system_prompt: Optional[str] = None
    user_prompt_template: str = Field(
        ...,
        description="Template with {{variables}} for substitution"
    )
    
    # Tool integration
    tool_instructions: Optional[str] = Field(
        None,
        description="How to use tools in this context"
    )
    
    # Variables
    variables: List[PromptVariable] = Field(
        default_factory=list,
        description="Variables that can be substituted"
    )
    
    # Metadata
    version: str = "1.0.0"
    priority: int = Field(
        default=100,
        description="Priority for template selection (higher = preferred)"
    )


class PromptCatalog(BaseModel):
    """
    Complete catalog of prompt templates.
    
    This is loaded from YAML and hot-reloadable.
    """
    
    templates: Dict[str, PromptTemplate] = Field(
        default_factory=dict,
        description="Template ID -> template mapping"
    )
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0.0"
    
    def get_template(
        self,
        intent_task: str,
        domains: List[str],
        model_tag: str
    ) -> Optional[PromptTemplate]:
        """
        Get the best matching template for given criteria.
        
        Matching rules:
        1. Exact match on intent_task
        2. Model tag must match
        3. Domain overlap (or template domains empty = match all)
        4. Highest priority wins
        """
        candidates = []
        
        for template in self.templates.values():
            # Must match intent
            if template.intent_task != intent_task:
                continue
            
            # Must match model
            if model_tag not in template.model_tags:
                continue
            
            # Domain matching
            if template.domains:  # If template specifies domains
                if not any(d in template.domains for d in domains):
                    continue
            
            candidates.append(template)
        
        if not candidates:
            return None
        
        # Return highest priority
        return max(candidates, key=lambda t: t.priority)
    
    def substitute_variables(
        self,
        template: PromptTemplate,
        variables: Dict[str, str]
    ) -> str:
        """
        Substitute variables in a template.
        
        Raises:
            ValueError: If required variables are missing
        """
        prompt = template.user_prompt_template
        
        # Check required variables
        required = {v.name for v in template.variables if v.required}
        missing = required - set(variables.keys())
        if missing:
            raise ValueError(f"Missing required variables: {missing}")
        
        # Add defaults for optional variables
        all_vars = {}
        for var in template.variables:
            if var.name in variables:
                all_vars[var.name] = variables[var.name]
            elif var.default is not None:
                all_vars[var.name] = var.default
        
        # Substitute
        for var_name, var_value in all_vars.items():
            prompt = prompt.replace(f"{{{{{var_name}}}}}", var_value)
        
        return prompt


# ============================================================================
# MODEL CAPABILITY MATRIX
# ============================================================================

class ModelCapabilities(BaseModel):
    """
    Capabilities of a specific model.
    """
    
    # Identity
    model_id: str = Field(..., description="Model identifier: gpt-4, claude-3-opus, etc.")
    provider: Literal["openai", "anthropic", "google"]
    model_family: str = Field(..., description="Model family: gpt, claude, gemini")
    
    # Capabilities
    supports_tools: bool = Field(default=False)
    supports_json_mode: bool = Field(default=False)
    supports_xml: bool = Field(default=False)
    supports_multimodal: bool = Field(default=False)
    supports_streaming: bool = Field(default=True)
    
    # Context windows
    max_input_tokens: int
    max_output_tokens: int
    
    # Performance characteristics
    typical_latency_ms: float = Field(
        ...,
        description="Typical p50 latency for 1000 tokens"
    )
    typical_throughput_tps: float = Field(
        ...,
        description="Tokens per second throughput"
    )
    
    # Cost (per 1M tokens)
    cost_per_1m_input_tokens: float
    cost_per_1m_output_tokens: float
    
    # Quality ratings (0-10 scale)
    reasoning_quality: float = Field(..., ge=0, le=10)
    instruction_following: float = Field(..., ge=0, le=10)
    factual_accuracy: float = Field(..., ge=0, le=10)
    
    # Metadata
    release_date: Optional[str] = None
    deprecation_date: Optional[str] = None
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost in USD for given token counts."""
        input_cost = (input_tokens / 1_000_000) * self.cost_per_1m_input_tokens
        output_cost = (output_tokens / 1_000_000) * self.cost_per_1m_output_tokens
        return input_cost + output_cost


class ModelCapabilityMatrix(BaseModel):
    """
    Complete matrix of model capabilities.
    
    This is loaded from YAML and hot-reloadable.
    """
    
    models: Dict[str, ModelCapabilities] = Field(
        default_factory=dict,
        description="Model ID -> capabilities mapping"
    )
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0.0"
    
    def get_model(self, model_id: str) -> Optional[ModelCapabilities]:
        """Get model capabilities by ID."""
        return self.models.get(model_id)
    
    def get_models_by_family(self, family: str) -> List[ModelCapabilities]:
        """Get all models in a family."""
        return [
            model for model in self.models.values()
            if model.model_family == family
        ]
    
    def select_best_model(
        self,
        required_capabilities: Dict[str, bool],
        max_latency_ms: Optional[float] = None,
        max_cost_per_1m_tokens: Optional[float] = None,
        prefer_quality: bool = True
    ) -> Optional[ModelCapabilities]:
        """
        Select the best model based on requirements.
        
        Args:
            required_capabilities: Dict of capability -> required value
            max_latency_ms: Maximum acceptable latency
            max_cost_per_1m_tokens: Maximum cost
            prefer_quality: Prefer quality over cost
        
        Returns:
            Best matching model or None
        """
        candidates = []
        
        for model in self.models.values():
            # Check required capabilities
            meets_requirements = True
            for cap, required in required_capabilities.items():
                if getattr(model, cap, False) != required:
                    meets_requirements = False
                    break
            
            if not meets_requirements:
                continue
            
            # Check latency
            if max_latency_ms and model.typical_latency_ms > max_latency_ms:
                continue
            
            # Check cost
            if max_cost_per_1m_tokens:
                avg_cost = (model.cost_per_1m_input_tokens + model.cost_per_1m_output_tokens) / 2
                if avg_cost > max_cost_per_1m_tokens:
                    continue
            
            candidates.append(model)
        
        if not candidates:
            return None
        
        # Sort by quality or cost
        if prefer_quality:
            return max(
                candidates,
                key=lambda m: (m.reasoning_quality + m.instruction_following + m.factual_accuracy) / 3
            )
        else:
            return min(
                candidates,
                key=lambda m: (m.cost_per_1m_input_tokens + m.cost_per_1m_output_tokens) / 2
            )


# ============================================================================
# CATALOG LOADER
# ============================================================================

class CatalogLoader:
    """
    Loads and manages all catalogs.
    
    Supports hot-reloading from filesystem.
    """
    
    def __init__(self, config_dir: Path):
        self.config_dir = Path(config_dir)
        self.tool_catalog: Optional[ToolCatalog] = None
        self.prompt_catalog: Optional[PromptCatalog] = None
        self.model_matrix: Optional[ModelCapabilityMatrix] = None
        self._checksums: Dict[str, str] = {}
    
    def load_all(self):
        """Load all catalogs."""
        self.tool_catalog = self._load_tool_catalog()
        self.prompt_catalog = self._load_prompt_catalog()
        self.model_matrix = self._load_model_matrix()
    
    def reload_if_changed(self):
        """Reload catalogs if files have changed."""
        if self._has_changed("tools.yaml"):
            self.tool_catalog = self._load_tool_catalog()
        
        if self._has_changed("prompts.yaml"):
            self.prompt_catalog = self._load_prompt_catalog()
        
        if self._has_changed("models.yaml"):
            self.model_matrix = self._load_model_matrix()
    
    def _load_tool_catalog(self) -> ToolCatalog:
        """Load tool catalog from YAML."""
        path = self.config_dir / "tools" / "cortex_tools.yaml"
        with open(path) as f:
            data = yaml.safe_load(f)
        return ToolCatalog(**data)
    
    def _load_prompt_catalog(self) -> PromptCatalog:
        """Load prompt catalog from YAML."""
        path = self.config_dir / "prompts" / "templates.yaml"
        with open(path) as f:
            data = yaml.safe_load(f)
        return PromptCatalog(**data)
    
    def _load_model_matrix(self) -> ModelCapabilityMatrix:
        """Load model capability matrix from YAML."""
        path = self.config_dir / "models" / "capabilities.yaml"
        with open(path) as f:
            data = yaml.safe_load(f)
        return ModelCapabilityMatrix(**data)
    
    def _has_changed(self, filename: str) -> bool:
        """Check if a file has changed since last load."""
        # Find file in config directory
        for catalog_type in ["tools", "prompts", "models"]:
            path = self.config_dir / catalog_type / filename
            if not path.exists():
                continue
            
            # Calculate checksum
            with open(path, 'rb') as f:
                checksum = hashlib.md5(f.read()).hexdigest()
            
            # Compare with stored checksum
            key = str(path)
            if key not in self._checksums:
                self._checksums[key] = checksum
                return False
            
            if self._checksums[key] != checksum:
                self._checksums[key] = checksum
                return True
            
            return False
        
        return False
