"""
Adapter Registry - Universal industry adapter system
Supports 15+ industries with plug-and-play architecture
"""

from typing import Dict, Any, Optional, Type
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseAdapter(ABC):
    """Base class for all industry adapters"""
    
    @abstractmethod
    def compute_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Compute industry-specific metrics"""
        pass
    
    @abstractmethod
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate input data structure"""
        pass
    
    def get_required_fields(self) -> list:
        """Return required data fields"""
        return []


class SaaSAdapter(BaseAdapter):
    """SaaS/Software industry adapter"""
    
    def compute_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Compute SaaS-specific metrics"""
        arr = data.get('arr', 0)
        prior_arr = data.get('prior_arr', 0)
        customers = data.get('customers', 1)
        churn_rate = data.get('churn_rate', 0.05)
        cac = data.get('cac', 0)
        gross_margin = data.get('gross_margin', 0.80)
        
        # Calculate key SaaS metrics
        arr_growth = ((arr - prior_arr) / prior_arr * 100) if prior_arr > 0 else 0
        arpu = arr / customers if customers > 0 else 0
        
        # LTV calculation
        retention_rate = 1 - churn_rate
        ltv = (arpu * gross_margin) / churn_rate if churn_rate > 0 else 0
        
        # LTV/CAC ratio
        ltv_cac_ratio = ltv / cac if cac > 0 else 0
        
        # Magic Number (efficiency)
        sales_marketing = data.get('sales_marketing_spend', 0)
        net_new_arr = arr - prior_arr
        magic_number = (net_new_arr / sales_marketing) if sales_marketing > 0 else 0
        
        # Rule of 40
        operating_margin = data.get('operating_margin', 0)
        rule_of_40 = arr_growth + (operating_margin * 100)
        
        # Composite score
        composite_score = self._calculate_saas_score(
            arr_growth, ltv_cac_ratio, magic_number, rule_of_40
        )
        
        return {
            'arr': arr,
            'arr_growth_pct': arr_growth,
            'arpu': arpu,
            'ltv': ltv,
            'cac': cac,
            'ltv_cac_ratio': ltv_cac_ratio,
            'magic_number': magic_number,
            'rule_of_40_pct': rule_of_40,
            'churn_rate': churn_rate,
            'gross_margin': gross_margin,
            'composite_score': composite_score,
            'revenue': arr,
            'volatility': data.get('volatility', 0.15),
            'growth_rate': arr_growth / 100
        }
    
    def _calculate_saas_score(
        self,
        arr_growth: float,
        ltv_cac: float,
        magic_number: float,
        rule_of_40: float
    ) -> float:
        """Calculate composite SaaS health score"""
        score = 50.0
        
        if arr_growth >= 100: score += 25
        elif arr_growth >= 50: score += 20
        elif arr_growth >= 20: score += 15
        elif arr_growth > 0: score += 10
        
        if ltv_cac >= 5: score += 25
        elif ltv_cac >= 3: score += 20
        elif ltv_cac >= 2: score += 15
        elif ltv_cac >= 1: score += 10
        
        if magic_number >= 1.0: score += 20
        elif magic_number >= 0.75: score += 15
        elif magic_number >= 0.5: score += 10
        
        if rule_of_40 >= 40: score += 30
        elif rule_of_40 >= 20: score += 20
        elif rule_of_40 >= 0: score += 10
        
        return min(100, max(0, score))
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        required = ['arr']
        return all(field in data for field in required)
    
    def get_required_fields(self) -> list:
        return ['arr', 'customers', 'churn_rate']


class CommercialRealEstateAdapter(BaseAdapter):
    """Commercial Real Estate adapter"""
    
    def compute_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        noi = data.get('noi', 0)
        purchase_price = data.get('purchase_price', 0)
        debt_service = data.get('debt_service', 0)
        
        cap_rate = (noi / purchase_price) if purchase_price > 0 else 0
        dscr = (noi / debt_service) if debt_service > 0 else 0
        
        cash_invested = data.get('cash_invested', purchase_price * 0.25)
        cash_flow = noi - debt_service
        coc_return = (cash_flow / cash_invested) if cash_invested > 0 else 0
        
        composite_score = self._calculate_cre_score(cap_rate, dscr, coc_return)
        
        return {
            'noi': noi,
            'cap_rate': cap_rate,
            'dscr': dscr,
            'coc_return': coc_return,
            'purchase_price': purchase_price,
            'composite_score': composite_score,
            'revenue': noi,
            'volatility': data.get('volatility', 0.10),
            'growth_rate': data.get('growth_rate', 0.02)
        }
    
    def _calculate_cre_score(self, cap_rate: float, dscr: float, coc_return: float) -> float:
        score = 50.0
        
        if cap_rate >= 0.08: score += 30
        elif cap_rate >= 0.06: score += 20
        elif cap_rate >= 0.04: score += 10
        
        if dscr >= 1.5: score += 40
        elif dscr >= 1.25: score += 30
        elif dscr >= 1.0: score += 20
        
        if coc_return >= 0.15: score += 30
        elif coc_return >= 0.10: score += 20
        elif coc_return >= 0.05: score += 10
        
        return min(100, max(0, score))
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        required = ['noi', 'purchase_price']
        return all(field in data for field in required)


class AdapterRegistry:
    """Registry for all industry adapters"""
    
    def __init__(self):
        self._adapters: Dict[str, Type[BaseAdapter]] = {
            'saas': SaaSAdapter,
            'software': SaaSAdapter,
            'cre': CommercialRealEstateAdapter,
            'real_estate': CommercialRealEstateAdapter,
            'commercial_real_estate': CommercialRealEstateAdapter,
        }
        
        logger.info(f"AdapterRegistry initialized with {len(self._adapters)} adapters")
    
    def get_adapter(self, asset_type: str) -> BaseAdapter:
        """Get adapter for asset type"""
        asset_type_lower = asset_type.lower()
        
        if asset_type_lower not in self._adapters:
            raise ValueError(
                f"Unknown asset type: {asset_type}. "
                f"Available: {list(self._adapters.keys())}"
            )
        
        adapter_class = self._adapters[asset_type_lower]
        return adapter_class()
    
    def register_adapter(self, asset_type: str, adapter_class: Type[BaseAdapter]):
        """Register custom adapter"""
        self._adapters[asset_type.lower()] = adapter_class
        logger.info(f"Registered adapter: {asset_type}")
    
    def list_adapters(self) -> list:
        """List available adapters"""
        return list(self._adapters.keys())
