"""
Integration Clients for Aetherion Core Engines
Provides connectivity from Domain Cortex agents to:
- BUE (Business Underwriting Engine)
- URPE (Universal Risk & Probabilistic Engine)
- UIE (Universal Intelligence Engine)
- UDOA (Universal Data Orchestration API)
- CEOA (Compute & Energy Orchestration API)
- ILE (Internal Learning Engine)
"""

import asyncio
import httpx
from typing import Dict, Any, List, Optional
import json


class BUEClient:
    """Business Underwriting Engine Client"""
    
    def __init__(self, base_url: str = "http://bue-engine:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def analyze(self, query: str, domain: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Request business analysis from BUE"""
        payload = {
            "query": query,
            "domain": domain,
            "context": context or {}
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/analyze",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {
                "error": str(e),
                "status": "failed"
            }
    
    async def close(self):
        await self.client.aclose()


class URPEClient:
    """Universal Risk & Probabilistic Engine Client"""
    
    def __init__(self, base_url: str = "http://urpe-engine:8001"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def analyze(self, query: str, domain: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Request risk/strategic analysis from URPE"""
        payload = {
            "query": query,
            "domain": domain,
            "context": context or {}
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/analyze",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {
                "error": str(e),
                "status": "failed"
            }
    
    async def close(self):
        await self.client.aclose()


class UIEClient:
    """Universal Intelligence Engine Client"""
    
    def __init__(self, base_url: str = "http://uie-engine:8002"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def synthesize(self, domain: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Request synthesis from UIE"""
        payload = {
            "domain": domain,
            "inputs": inputs
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/synthesize",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {
                "error": str(e),
                "status": "failed"
            }
    
    async def synthesize_complex(self, domain: str, **kwargs) -> Dict[str, Any]:
        """Request complex synthesis from UIE"""
        payload = {
            "domain": domain,
            "components": kwargs
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/synthesize/complex",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {
                "error": str(e),
                "status": "failed"
            }
    
    async def close(self):
        await self.client.aclose()


class UDOAClient:
    """Universal Data Orchestration API Client"""
    
    def __init__(self, base_url: str = "http://udoa-api:8003"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def query(self, query: str, domain_filter: Optional[str] = None) -> Dict[str, Any]:
        """Query UDOA for data"""
        params = {"query": query}
        if domain_filter:
            params["domain"] = domain_filter
        
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/query",
                params=params
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {
                "error": str(e),
                "status": "failed"
            }
    
    async def discover(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Discover data contracts"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/discover",
                json=criteria
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return []
    
    async def close(self):
        await self.client.aclose()


class CEOAClient:
    """Compute & Energy Orchestration API Client"""
    
    def __init__(self, base_url: str = "http://ceoa-api:8004"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def optimize_workload(self, workload: Dict[str, Any]) -> Dict[str, Any]:
        """Request workload optimization"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/optimize",
                json=workload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {
                "error": str(e),
                "status": "failed"
            }
    
    async def close(self):
        await self.client.aclose()


class ILEClient:
    """Internal Learning Engine Client"""
    
    def __init__(self, base_url: str = "http://ile-engine:8005"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def record_analysis(self, domain: str, query: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Record analysis for meta-learning"""
        payload = {
            "domain": domain,
            "query": query,
            "result": result,
            "timestamp": result.get("timestamp")
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/record",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {
                "error": str(e),
                "status": "failed"
            }
    
    async def get_patterns(self, domain: str) -> List[Dict[str, Any]]:
        """Retrieve learned patterns for domain"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/patterns/{domain}"
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return []
    
    async def close(self):
        await self.client.aclose()


class EngineClientFactory:
    """Factory for creating and managing engine clients"""
    
    @staticmethod
    def create_all() -> Dict[str, Any]:
        """Create all engine clients"""
        return {
            "bue": BUEClient(),
            "urpe": URPEClient(),
            "uie": UIEClient(),
            "udoa": UDOAClient(),
            "ceoa": CEOAClient(),
            "ile": ILEClient()
        }
    
    @staticmethod
    async def close_all(clients: Dict[str, Any]):
        """Close all engine clients"""
        for client in clients.values():
            if hasattr(client, 'close'):
                await client.close()
