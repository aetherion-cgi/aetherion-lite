"""
Function Broker Capability Registry
Loads and manages capability descriptors and adapters
"""

import yaml
from pathlib import Path
from typing import Dict, Type, Optional
import importlib

from .models import CapabilityDescriptor, AdapterConfig
from ..adapters.base import BaseAdapter
from ..observability.logging import get_logger

logger = get_logger(__name__)


class CapabilityRegistry:
    """
    Central registry for all capabilities and their adapters.
    Loads from YAML configuration and provides adapter instances.
    """

    def __init__(self, config_path: Path, adapter_config: AdapterConfig):
        self.config_path = config_path
        self.adapter_config = adapter_config
        self._capabilities: Dict[str, CapabilityDescriptor] = {}
        self._adapter_classes: Dict[str, Type[BaseAdapter]] = {}
        self._adapter_cache: Dict[str, BaseAdapter] = {}
        
        self._load_capabilities()
        self._register_adapter_classes()

    def _load_capabilities(self) -> None:
        """Load capability descriptors from YAML"""
        logger.info(f"Loading capabilities from {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            capabilities_list = yaml.safe_load(f)
        
        for cap_data in capabilities_list:
            descriptor = CapabilityDescriptor(**cap_data)
            self._capabilities[descriptor.id] = descriptor
            logger.info(f"Registered capability: {descriptor.id}")
        
        logger.info(f"Loaded {len(self._capabilities)} capabilities")

    def _register_adapter_classes(self) -> None:
        """
        Dynamically import and register adapter classes.
        Each adapter maps to a capability type.
        """
        # Import base adapters package so it's available on sys.path for submodule imports
        importlib.import_module("broker.adapters")

        # Some adapters don't follow the simple "DomainCortexAdapter" -> "domaincortex_adapter" transform.
        # Provide explicit module-name overrides here to avoid fragile naming mismatches.
        module_name_overrides = {
            "DomainCortexAdapter": "domain_cortex_adapter",
        }
        
        # Import all adapter classes
        adapter_names = [
            "UIEAdapter",
            "BUEAdapter",
            "UDOAAdapter",
            "CEOAAdapter",
            "URPEAdapter",
            "ILEAdapter",
            "DomainCortexAdapter"
        ]
        
        for adapter_name in adapter_names:
            try:
                # Import from specific module (e.g., broker.adapters.uie_adapter)
                module_name = module_name_overrides.get(
                    adapter_name,
                    adapter_name.lower().replace("adapter", "_adapter"),
                )
                adapter_module_path = f"broker.adapters.{module_name}"
                module = importlib.import_module(adapter_module_path)
                adapter_class = getattr(module, adapter_name)
                self._adapter_classes[adapter_name] = adapter_class
                logger.info(f"Registered adapter class: {adapter_name}")
            except (ImportError, AttributeError) as e:
                logger.warning(f"Could not load adapter {adapter_name}: {e}")

    def get(self, capability_id: str) -> CapabilityDescriptor:
        """Get capability descriptor by ID"""
        if capability_id not in self._capabilities:
            raise ValueError(f"Unknown capability: {capability_id}")
        return self._capabilities[capability_id]

    def list_capabilities(
        self,
        domain: Optional[str] = None,
        governance_tier: Optional[str] = None
    ) -> list[CapabilityDescriptor]:
        """
        List all capabilities, optionally filtered.
        
        Args:
            domain: Filter by domain
            governance_tier: Filter by default governance tier
        """
        capabilities = list(self._capabilities.values())
        
        if domain:
            capabilities = [
                cap for cap in capabilities
                if domain in cap.domains
            ]
        
        if governance_tier:
            capabilities = [
                cap for cap in capabilities
                if cap.default_governance_tier == governance_tier
            ]
        
        return capabilities

    def build_adapter(self, descriptor: CapabilityDescriptor) -> BaseAdapter:
        """
        Build or retrieve cached adapter instance for a capability.
        Adapters are cached per capability_id for performance.
        """
        if descriptor.id in self._adapter_cache:
            return self._adapter_cache[descriptor.id]
        
        adapter_class_name = descriptor.adapter
        if adapter_class_name not in self._adapter_classes:
            raise ValueError(f"Unknown adapter class: {adapter_class_name}")
        
        adapter_class = self._adapter_classes[adapter_class_name]
        adapter = adapter_class(descriptor, self.adapter_config)
        
        self._adapter_cache[descriptor.id] = adapter
        logger.info(f"Created adapter for {descriptor.id}: {adapter_class_name}")
        
        return adapter

    def get_capabilities_for_domains(self, domains: list[str]) -> list[CapabilityDescriptor]:
        """Get all capabilities that match any of the specified domains"""
        matching = []
        for cap in self._capabilities.values():
            if any(domain in cap.domains for domain in domains):
                matching.append(cap)
        return matching

    def reload(self) -> None:
        """Reload capabilities from config (useful for hot-reloading)"""
        logger.info("Reloading capability registry")
        self._capabilities.clear()
        self._adapter_cache.clear()
        self._load_capabilities()
