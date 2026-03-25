"""
BUE Child Agent - Specialized Micro-Reasoner

Child agents are ephemeral, purpose-built processes that handle
specific aspects of analysis:
- Market sizing
- Competitive positioning  
- Regulatory risk
- Financial forecasting
- Technology assessment

Total: ~300 LOC per child type
"""

import uuid
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ChildAgentType(Enum):
    """Types of specialized child agents"""
    MARKET_SIZING = "market_sizing"
    COMPETITIVE_ANALYSIS = "competitive_positioning"
    REGULATORY_RISK = "regulatory_risk"
    FINANCIAL_FORECASTING = "financial_forecasting"
    TECHNOLOGY_ASSESSMENT = "technology_assessment"
    CUSTOMER_ANALYSIS = "customer_analysis"
    TEAM_ASSESSMENT = "team_assessment"


@dataclass
class ChildAnalysis:
    """Result from child agent analysis"""
    agent_id: str
    agent_type: str
    result: Dict[str, Any]
    key_insight: str
    confidence_score: float
    processing_time: float
    summary: str
    created_at: datetime


class BUEChildAgent:
    """
    BUE Child Agent - Focused micro-reasoner
    
    These are temporary agents spawned by the parent to handle
    specialized analysis tasks. They:
    - Focus on ONE specific aspect
    - Use subset of manifest rules
    - Can call existing BUE functions
    - Return compact, focused results
    - Are pruned after completion
    
    This mimics synaptic processes in neural networks.
    """
    
    def __init__(
        self,
        agent_type: str,
        manifest_subset: Dict[str, Any],
        parent_context: Dict[str, Any],
        bue_engine=None
    ):
        """
        Initialize child agent
        
        Args:
            agent_type: Type of specialized analysis
            manifest_subset: Relevant portion of industry manifest
            parent_context: Context from parent agent
            bue_engine: Access to existing BUE functions
        """
        self.agent_id = str(uuid.uuid4())
        self.agent_type = agent_type
        self.rules = manifest_subset
        self.parent_context = parent_context
        self.bue_engine = bue_engine
        self.created_at = datetime.now()
        
        print(f"   → Child agent spawned: {agent_type} ({self.agent_id[:8]}...)")
    
    async def analyze(self, company_data: Dict[str, Any]) -> ChildAnalysis:
        """
        Execute specialized analysis based on agent type
        
        Routes to appropriate analysis method
        """
        start_time = datetime.now()
        
        # Route to appropriate handler
        if self.agent_type == ChildAgentType.MARKET_SIZING.value:
            result = await self._analyze_market_size(company_data)
        elif self.agent_type == ChildAgentType.COMPETITIVE_ANALYSIS.value:
            result = await self._analyze_competitive_position(company_data)
        elif self.agent_type == ChildAgentType.REGULATORY_RISK.value:
            result = await self._analyze_regulatory_landscape(company_data)
        elif self.agent_type == ChildAgentType.FINANCIAL_FORECASTING.value:
            result = await self._forecast_financials(company_data)
        elif self.agent_type == ChildAgentType.TECHNOLOGY_ASSESSMENT.value:
            result = await self._assess_technology_moat(company_data)
        elif self.agent_type == ChildAgentType.CUSTOMER_ANALYSIS.value:
            result = await self._analyze_customer_base(company_data)
        elif self.agent_type == ChildAgentType.TEAM_ASSESSMENT.value:
            result = await self._assess_team(company_data)
        else:
            raise ValueError(f"Unknown child agent type: {self.agent_type}")
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Build analysis object
        analysis = ChildAnalysis(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            result=result['details'],
            key_insight=result['key_insight'],
            confidence_score=result['confidence'],
            processing_time=processing_time,
            summary=result['summary'],
            created_at=self.created_at
        )
        
        print(f"   ← Child complete: {self.agent_type} (confidence: {result['confidence']:.1%})")
        
        return analysis
    
    async def _analyze_market_size(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Specialized analysis: Market sizing (TAM/SAM/SOM)
        
        Uses manifest rules + BUE Monte Carlo + external data
        """
        # Get TAM/SAM/SOM calculation method from manifest
        market_config = self.rules.get('tam_calculation', 'top_down')
        growth_model = self.rules.get('growth_rate_model', 'compound')
        penetration = self.rules.get('penetration_assumptions', {})
        
        # Simple market sizing logic (would be more sophisticated in production)
        industry = self.parent_context.get('industry', 'Unknown')
        
        # Mock calculation (would use actual market data + BUE Monte Carlo)
        if market_config == 'top_down':
            tam_base = self._estimate_tam_top_down(industry, company_data)
        else:
            tam_base = self._estimate_tam_bottom_up(industry, company_data)
        
        # Apply penetration assumptions
        tam = tam_base
        sam = tam * penetration.get('sam_multiplier', 0.15)
        som = sam * penetration.get('som_multiplier', 0.20)
        
        # Growth projections
        year_1_revenue = som * penetration.get('year_1', 0.001)
        year_3_revenue = som * penetration.get('year_3', 0.01)
        year_5_revenue = som * penetration.get('year_5', 0.05)
        
        result = {
            'details': {
                'tam': tam,
                'sam': sam,
                'som': som,
                'methodology': market_config,
                'revenue_projections': {
                    'year_1': year_1_revenue,
                    'year_3': year_3_revenue,
                    'year_5': year_5_revenue
                },
                'assumptions': penetration
            },
            'key_insight': f"TAM ${tam/1e9:.1f}B, realistic 5-year target: ${year_5_revenue/1e6:.0f}M",
            'confidence': 0.78,
            'summary': f"Market sizing: ${tam/1e9:.1f}B TAM, ${sam/1e9:.1f}B SAM, ${som/1e9:.1f}B SOM"
        }
        
        return result
    
    async def _analyze_competitive_position(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Specialized analysis: Competitive positioning
        
        Evaluates moat, differentiation, competitive dynamics
        """
        key_factors = self.rules.get('key_factors', [])
        moat_indicators = self.rules.get('moat_indicators', {})
        
        # Analyze competitive factors
        strengths = []
        weaknesses = []
        moat_strength = 0.0
        
        # Mock analysis (would be more sophisticated)
        if 'product_differentiation' in key_factors:
            strengths.append("Strong product differentiation")
            moat_strength += 0.2
        
        if 'network_effects' in key_factors:
            strengths.append("Network effects present")
            moat_strength += 0.3
        
        # Check moat indicators from company data
        nrr = company_data.get('nrr', '0%')
        if 'nrr' in moat_indicators:
            if float(nrr.strip('%')) > 120:
                strengths.append("Exceptional net revenue retention (>120%)")
                moat_strength += 0.25
        
        # Calculate competitive position score
        competitive_score = min(moat_strength, 1.0)
        
        # Determine positioning
        if competitive_score > 0.7:
            position = "Strong competitive moat"
        elif competitive_score > 0.4:
            position = "Moderate competitive advantage"
        else:
            position = "Limited competitive moat"
        
        result = {
            'details': {
                'competitive_score': competitive_score,
                'strengths': strengths,
                'weaknesses': weaknesses,
                'moat_factors': list(moat_indicators.keys()),
                'positioning': position
            },
            'key_insight': f"{position}, score: {competitive_score:.1%}",
            'confidence': 0.81,
            'summary': f"Competitive: {position} with {len(strengths)} key strengths"
        }
        
        return result
    
    async def _analyze_regulatory_landscape(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Specialized analysis: Regulatory risk assessment
        
        Evaluates compliance requirements, regulatory risks, jurisdictional issues
        """
        regulatory_config = self.rules
        geography = company_data.get('geography', 'US')
        
        # Identify applicable regulations
        applicable_regs = []
        compliance_requirements = []
        risk_level = 0.0
        
        # Check GDPR (if EU operations)
        if geography in ['EU', 'Europe'] and regulatory_config.get('gdpr') == 'required':
            applicable_regs.append('GDPR')
            compliance_requirements.append('Data sovereignty + GDPR Article 5')
            risk_level += 0.2
        
        # Check HIPAA (if health data)
        if regulatory_config.get('hipaa') in ['required', 'conditional']:
            if 'health' in company_data.get('name', '').lower():
                applicable_regs.append('HIPAA')
                compliance_requirements.append('PHI encryption + BAA')
                risk_level += 0.25
        
        # Check SOC 2
        if regulatory_config.get('soc2') in ['required', 'highly_recommended']:
            applicable_regs.append('SOC 2')
            compliance_requirements.append('SOC 2 Type II certification')
            risk_level += 0.1
        
        # Check industry-specific
        if regulatory_config.get('ccpa') == 'required':
            applicable_regs.append('CCPA')
            risk_level += 0.15
        
        # Determine risk assessment
        if risk_level < 0.3:
            risk_assessment = "Low regulatory risk"
        elif risk_level < 0.6:
            risk_assessment = "Moderate regulatory risk"
        else:
            risk_assessment = "High regulatory risk"
        
        result = {
            'details': {
                'applicable_regulations': applicable_regs,
                'compliance_requirements': compliance_requirements,
                'risk_level': risk_level,
                'geography': geography,
                'assessment': risk_assessment
            },
            'key_insight': f"{risk_assessment}: {len(applicable_regs)} major regulations applicable",
            'confidence': 0.85,
            'summary': f"Regulatory: {risk_assessment}, {len(applicable_regs)} frameworks required"
        }
        
        return result
    
    async def _forecast_financials(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Specialized analysis: Financial forecasting
        
        Projects revenue, burn, runway based on current metrics
        """
        model_type = self.rules.get('model_type', 'cohort_based')
        horizon_months = self.rules.get('forecast_horizon', 36)
        key_drivers = self.rules.get('key_drivers', [])
        
        # Extract current financials
        arr = self._parse_currency(company_data.get('arr', '$0'))
        growth_rate = self._parse_percentage(company_data.get('growth_rate', '0%'))
        burn_rate = self._parse_currency(company_data.get('burn_rate', '$0'))
        
        # Calculate runway
        # Simplified - would use more sophisticated model in production
        if burn_rate > 0:
            runway_months = arr / (burn_rate * 12)
        else:
            runway_months = 999  # Profitable
        
        # Project forward
        projections = []
        current_arr = arr
        for month in range(0, horizon_months + 1, 6):
            projected_arr = current_arr * ((1 + growth_rate) ** (month / 12))
            projections.append({
                'month': month,
                'arr': projected_arr,
                'mrr': projected_arr / 12
            })
        
        # Assess financial health
        if runway_months > 18:
            health = "Strong financial position"
        elif runway_months > 12:
            health = "Adequate runway"
        else:
            health = "Concerning burn rate"
        
        result = {
            'details': {
                'current_arr': arr,
                'growth_rate': growth_rate,
                'burn_rate': burn_rate,
                'runway_months': runway_months,
                'projections': projections,
                'model_type': model_type,
                'health_assessment': health
            },
            'key_insight': f"{health}: {runway_months:.0f} months runway at current burn",
            'confidence': 0.73,
            'summary': f"Financial: {runway_months:.0f}mo runway, {growth_rate:.0%} growth"
        }
        
        return result
    
    async def _assess_technology_moat(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Specialized analysis: Technology assessment
        
        Evaluates technical differentiation, IP, defensibility
        """
        # Mock technology assessment
        # In production, would analyze patents, technical architecture, etc.
        
        tech_factors = []
        moat_score = 0.5  # Baseline
        
        # Check for AI/ML (often a moat in 2025)
        if 'ai' in company_data.get('name', '').lower():
            tech_factors.append("AI/ML capabilities")
            moat_score += 0.2
        
        # Check for proprietary data
        if 'data' in company_data.get('description', '').lower():
            tech_factors.append("Proprietary dataset")
            moat_score += 0.15
        
        # Assess overall tech moat
        if moat_score > 0.75:
            assessment = "Strong technology moat"
        elif moat_score > 0.5:
            assessment = "Moderate technology differentiation"
        else:
            assessment = "Limited technical moat"
        
        result = {
            'details': {
                'moat_score': moat_score,
                'tech_factors': tech_factors,
                'assessment': assessment
            },
            'key_insight': f"{assessment} with score {moat_score:.1%}",
            'confidence': 0.68,
            'summary': f"Technology: {assessment}"
        }
        
        return result
    
    async def _analyze_customer_base(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Specialized analysis: Customer analysis
        
        Evaluates customer concentration, churn, expansion
        """
        # Mock customer analysis
        customer_count = company_data.get('customer_count', 100)
        top_customer_pct = company_data.get('top_customer_revenue_pct', 15)
        
        # Assess concentration risk
        if top_customer_pct > 25:
            concentration = "High concentration risk"
            risk_score = 0.7
        elif top_customer_pct > 15:
            concentration = "Moderate concentration"
            risk_score = 0.4
        else:
            concentration = "Well-diversified"
            risk_score = 0.2
        
        result = {
            'details': {
                'customer_count': customer_count,
                'top_customer_pct': top_customer_pct,
                'concentration_risk': risk_score,
                'assessment': concentration
            },
            'key_insight': f"{concentration}: top customer {top_customer_pct}% of revenue",
            'confidence': 0.80,
            'summary': f"Customers: {concentration}"
        }
        
        return result
    
    async def _assess_team(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Specialized analysis: Team assessment
        
        Evaluates founder experience, team composition, execution capability
        """
        # Mock team assessment
        # In production, would analyze LinkedIn, past exits, domain expertise
        
        team_score = 0.7  # Baseline
        strengths = []
        
        # Mock factors
        if 'experienced' in company_data.get('team_description', ''):
            strengths.append("Experienced founding team")
            team_score += 0.15
        
        assessment = "Strong team" if team_score > 0.75 else "Capable team"
        
        result = {
            'details': {
                'team_score': team_score,
                'strengths': strengths,
                'assessment': assessment
            },
            'key_insight': f"{assessment} with score {team_score:.1%}",
            'confidence': 0.65,
            'summary': f"Team: {assessment}"
        }
        
        return result
    
    # Helper methods
    
    def _estimate_tam_top_down(self, industry: str, company_data: Dict[str, Any]) -> float:
        """Estimate TAM using top-down approach"""
        # Mock - would use actual market data
        industry_tam_map = {
            'SaaS': 200e9,  # $200B
            'AI/ML': 150e9,
            'FinTech': 300e9,
            'HealthTech': 250e9,
            'CyberSecurity': 180e9
        }
        return industry_tam_map.get(industry, 100e9)
    
    def _estimate_tam_bottom_up(self, industry: str, company_data: Dict[str, Any]) -> float:
        """Estimate TAM using bottom-up approach"""
        # Mock - would calculate from unit economics
        return self._estimate_tam_top_down(industry, company_data) * 0.8
    
    def _parse_currency(self, value: str) -> float:
        """Parse currency string to float"""
        if isinstance(value, (int, float)):
            return float(value)
        
        # Remove $ and convert K/M/B
        value = value.strip().replace('$', '').replace(',', '')
        
        multiplier = 1
        if value.endswith('K'):
            multiplier = 1e3
            value = value[:-1]
        elif value.endswith('M'):
            multiplier = 1e6
            value = value[:-1]
        elif value.endswith('B'):
            multiplier = 1e9
            value = value[:-1]
        
        try:
            return float(value) * multiplier
        except:
            return 0.0
    
    def _parse_percentage(self, value: str) -> float:
        """Parse percentage string to float"""
        if isinstance(value, (int, float)):
            return float(value)
        
        value = value.strip().replace('%', '')
        try:
            return float(value) / 100.0
        except:
            return 0.0
