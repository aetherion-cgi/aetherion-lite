"""
Carbon Intelligence Engine - Carbon-aware scheduling with caching & forecasting.

Strategy: Start simple, upgrade later. Use EMA + seasonal adjustment for forecasting.
Can swap in Prophet/LSTM later without changing interface.

~300 LOC vs. ~1,200 LOC for full ML implementation.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import asyncio
import json

import httpx
from redis import Redis


# ============================================================================
# DATA STRUCTURES
# ============================================================================
@dataclass
class CarbonIntensity:
    """Carbon intensity data point"""
    region: str
    timestamp: datetime
    intensity_gco2_kwh: float
    source: str
    is_forecast: bool = False
    confidence: float = 1.0


@dataclass
class CarbonForecast:
    """Carbon intensity forecast for next N hours"""
    region: str
    forecast: List[CarbonIntensity]
    generated_at: datetime


# ============================================================================
# CARBON INTELLIGENCE ENGINE
# ============================================================================
class CarbonIntelligenceEngine:
    """
    Carbon-aware scheduling intelligence.
    
    Architecture:
    1. Multi-source fetcher (ElectricityMaps, WattTime, etc.)
    2. Write-through cache (Redis)
    3. Simple EMA forecaster (can upgrade to ML later)
    
    Interface stays stable so we can swap forecasting models later.
    """
    
    # Data sources
    ELECTRICITY_MAPS_API = "https://api.electricitymap.org/v3"
    WATT_TIME_API = "https://api2.watttime.org/v2"
    
    # Cache TTLs
    CURRENT_TTL_SECONDS = 300      # 5 minutes
    FORECAST_TTL_SECONDS = 3600    # 1 hour
    
    def __init__(self, api_keys: Dict[str, str], redis_client: Redis):
        """
        Initialize carbon intelligence engine.
        
        Args:
            api_keys: Dict with keys for data sources (electricity_maps, watt_time)
            redis_client: Redis client for caching
        """
        self.api_keys = api_keys
        self.redis = redis_client
        self.http_client = httpx.AsyncClient(timeout=10.0)
    
    async def get_current_intensity(self, region: str) -> CarbonIntensity:
        """
        Get current carbon intensity for region.
        
        Flow:
        1. Check cache
        2. If miss, fetch from source
        3. Write to cache
        4. Return
        """
        # Try cache first
        cache_key = f"carbon:current:{region}"
        cached = self.redis.get(cache_key)
        
        if cached:
            data = json.loads(cached)
            return CarbonIntensity(**data)
        
        # Cache miss - fetch from source
        intensity = await self._fetch_current_intensity(region)
        
        # Write to cache
        self.redis.setex(
            cache_key,
            self.CURRENT_TTL_SECONDS,
            json.dumps({
                "region": intensity.region,
                "timestamp": intensity.timestamp.isoformat(),
                "intensity_gco2_kwh": intensity.intensity_gco2_kwh,
                "source": intensity.source,
                "is_forecast": False,
                "confidence": 1.0,
            })
        )
        
        return intensity
    
    async def get_forecast(self, region: str, hours: int = 24) -> CarbonForecast:
        """
        Get carbon intensity forecast for next N hours.
        
        Uses simple EMA + seasonal adjustment. Can upgrade to Prophet/LSTM later
        without changing this interface.
        """
        # Try cache first
        cache_key = f"carbon:forecast:{region}:{hours}"
        cached = self.redis.get(cache_key)
        
        if cached:
            data = json.loads(cached)
            return CarbonForecast(
                region=region,
                forecast=[CarbonIntensity(**point) for point in data["forecast"]],
                generated_at=datetime.fromisoformat(data["generated_at"]),
            )
        
        # Cache miss - generate forecast
        forecast = await self._generate_forecast(region, hours)
        
        # Write to cache
        self.redis.setex(
            cache_key,
            self.FORECAST_TTL_SECONDS,
            json.dumps({
                "region": region,
                "forecast": [
                    {
                        "region": point.region,
                        "timestamp": point.timestamp.isoformat(),
                        "intensity_gco2_kwh": point.intensity_gco2_kwh,
                        "source": point.source,
                        "is_forecast": True,
                        "confidence": point.confidence,
                    }
                    for point in forecast.forecast
                ],
                "generated_at": forecast.generated_at.isoformat(),
            })
        )
        
        return forecast
    
    async def find_green_windows(
        self,
        region: str,
        hours: int = 24,
        threshold_gco2_kwh: float = 100.0,
    ) -> List[Tuple[datetime, datetime]]:
        """
        Find "green windows" - periods when carbon intensity is below threshold.
        
        Returns list of (start_time, end_time) tuples.
        """
        forecast = await self.get_forecast(region, hours)
        
        green_windows = []
        window_start = None
        
        for point in forecast.forecast:
            if point.intensity_gco2_kwh < threshold_gco2_kwh:
                # Start or continue green window
                if window_start is None:
                    window_start = point.timestamp
            else:
                # End green window
                if window_start is not None:
                    green_windows.append((window_start, point.timestamp))
                    window_start = None
        
        # Close final window if still open
        if window_start is not None:
            green_windows.append((window_start, forecast.forecast[-1].timestamp))
        
        return green_windows
    
    async def estimate_workload_carbon(
        self,
        region: str,
        start_time: datetime,
        duration_hours: float,
        power_draw_watts: float,
    ) -> float:
        """
        Estimate carbon footprint for workload.
        
        Args:
            region: Compute region
            start_time: Expected start time
            duration_hours: Expected duration
            power_draw_watts: Average power consumption
        
        Returns: Estimated carbon in kg CO2
        """
        # Get carbon intensity at start time
        if start_time > datetime.utcnow():
            # Future execution - use forecast
            hours_ahead = int((start_time - datetime.utcnow()).total_seconds() / 3600)
            forecast = await self.get_forecast(region, hours_ahead + int(duration_hours) + 1)
            
            # Find intensity at start time
            intensity = next(
                (p.intensity_gco2_kwh for p in forecast.forecast 
                 if abs((p.timestamp - start_time).total_seconds()) < 1800),
                300.0  # Default if not found
            )
        else:
            # Current execution - use current intensity
            current = await self.get_current_intensity(region)
            intensity = current.intensity_gco2_kwh
        
        # Calculate carbon
        energy_kwh = (power_draw_watts * duration_hours) / 1000
        carbon_kg = (energy_kwh * intensity) / 1000
        
        return carbon_kg
    
    # -------------------------------------------------------------------------
    # INTERNAL METHODS
    # -------------------------------------------------------------------------
    
    async def _fetch_current_intensity(self, region: str) -> CarbonIntensity:
        """
        Fetch current carbon intensity from data sources.
        
        Tries multiple sources with fallback.
        """
        # Try ElectricityMaps first
        if "electricity_maps" in self.api_keys:
            try:
                intensity = await self._fetch_from_electricity_maps(region)
                if intensity:
                    return intensity
            except Exception as e:
                print(f"ElectricityMaps fetch failed: {e}")
        
        # Try WattTime as fallback
        if "watt_time" in self.api_keys:
            try:
                intensity = await self._fetch_from_watt_time(region)
                if intensity:
                    return intensity
            except Exception as e:
                print(f"WattTime fetch failed: {e}")
        
        # All sources failed - return conservative estimate
        return CarbonIntensity(
            region=region,
            timestamp=datetime.utcnow(),
            intensity_gco2_kwh=300.0,  # Global average
            source="default",
            confidence=0.5,
        )
    
    async def _fetch_from_electricity_maps(self, region: str) -> Optional[CarbonIntensity]:
        """Fetch from ElectricityMaps API"""
        # Map region to ElectricityMaps zone
        zone = self._region_to_em_zone(region)
        
        headers = {"auth-token": self.api_keys["electricity_maps"]}
        url = f"{self.ELECTRICITY_MAPS_API}/carbon-intensity/latest?zone={zone}"
        
        response = await self.http_client.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        
        return CarbonIntensity(
            region=region,
            timestamp=datetime.fromisoformat(data["datetime"].replace("Z", "+00:00")),
            intensity_gco2_kwh=data["carbonIntensity"],
            source="electricity_maps",
        )
    
    async def _fetch_from_watt_time(self, region: str) -> Optional[CarbonIntensity]:
        """Fetch from WattTime API"""
        # Map region to WattTime BA (Balancing Authority)
        ba = self._region_to_watt_time_ba(region)
        
        # WattTime requires OAuth token
        token = await self._get_watt_time_token()
        
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.WATT_TIME_API}/index?ba={ba}"
        
        response = await self.http_client.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        
        # WattTime returns MOER (Marginal Operating Emissions Rate) in lbs/MWh
        # Convert to gCO2/kWh: (lbs/MWh) * 453.592 (g/lb) / 1000 (kWh/MWh)
        intensity_gco2_kwh = data["moer"] * 0.453592
        
        return CarbonIntensity(
            region=region,
            timestamp=datetime.fromisoformat(data["point_time"]),
            intensity_gco2_kwh=intensity_gco2_kwh,
            source="watt_time",
        )
    
    async def _generate_forecast(self, region: str, hours: int) -> CarbonForecast:
        """
        Generate carbon intensity forecast using EMA + seasonal adjustment.
        
        Simple but effective for v1. Can upgrade to Prophet/LSTM later.
        """
        # Get historical data (last 7 days)
        historical = await self._get_historical_data(region, days=7)
        
        if not historical:
            # No historical data - use current intensity as flat forecast
            current = await self.get_current_intensity(region)
            forecast_points = [
                CarbonIntensity(
                    region=region,
                    timestamp=datetime.utcnow() + timedelta(hours=h),
                    intensity_gco2_kwh=current.intensity_gco2_kwh,
                    source="ema_forecast",
                    is_forecast=True,
                    confidence=0.6,
                )
                for h in range(1, hours + 1)
            ]
            return CarbonForecast(
                region=region,
                forecast=forecast_points,
                generated_at=datetime.utcnow(),
            )
        
        # Calculate EMA (Exponential Moving Average)
        alpha = 0.3  # Smoothing factor
        ema = historical[-1].intensity_gco2_kwh
        
        # Calculate seasonal pattern (hourly)
        seasonal_pattern = self._calculate_seasonal_pattern(historical)
        
        # Generate forecast
        forecast_points = []
        current_time = datetime.utcnow()
        
        for h in range(1, hours + 1):
            target_time = current_time + timedelta(hours=h)
            hour_of_day = target_time.hour
            
            # EMA forecast
            ema = alpha * ema + (1 - alpha) * historical[-1].intensity_gco2_kwh
            
            # Apply seasonal adjustment
            seasonal_factor = seasonal_pattern.get(hour_of_day, 1.0)
            forecasted_intensity = ema * seasonal_factor
            
            # Confidence decreases with distance
            confidence = max(0.3, 1.0 - (h / hours) * 0.5)
            
            forecast_points.append(
                CarbonIntensity(
                    region=region,
                    timestamp=target_time,
                    intensity_gco2_kwh=forecasted_intensity,
                    source="ema_forecast",
                    is_forecast=True,
                    confidence=confidence,
                )
            )
        
        return CarbonForecast(
            region=region,
            forecast=forecast_points,
            generated_at=datetime.utcnow(),
        )
    
    async def _get_historical_data(self, region: str, days: int = 7) -> List[CarbonIntensity]:
        """
        Get historical carbon intensity data.
        
        Would query database in production. For now, returns empty list.
        """
        # Placeholder - would query from database
        return []
    
    def _calculate_seasonal_pattern(self, historical: List[CarbonIntensity]) -> Dict[int, float]:
        """
        Calculate hourly seasonal pattern from historical data.
        
        Returns: Dict[hour_of_day, multiplier]
        """
        if not historical:
            return {h: 1.0 for h in range(24)}
        
        # Group by hour of day
        hourly_intensities = {h: [] for h in range(24)}
        for point in historical:
            hour = point.timestamp.hour
            hourly_intensities[hour].append(point.intensity_gco2_kwh)
        
        # Calculate average for each hour
        overall_avg = sum(p.intensity_gco2_kwh for p in historical) / len(historical)
        
        seasonal_pattern = {}
        for hour, intensities in hourly_intensities.items():
            if intensities:
                hour_avg = sum(intensities) / len(intensities)
                seasonal_pattern[hour] = hour_avg / overall_avg
            else:
                seasonal_pattern[hour] = 1.0
        
        return seasonal_pattern
    
    def _region_to_em_zone(self, region: str) -> str:
        """Map cloud region to ElectricityMaps zone"""
        mapping = {
            "us-west-2": "US-NW-PACW",  # Pacific Northwest
            "us-east-1": "US-MIDA-PJM",  # Mid-Atlantic
            "eu-west-1": "IE",           # Ireland
            # Add more mappings as needed
        }
        return mapping.get(region, "US")
    
    def _region_to_watt_time_ba(self, region: str) -> str:
        """Map cloud region to WattTime balancing authority"""
        mapping = {
            "us-west-2": "BPAT",   # Bonneville Power Administration
            "us-east-1": "PJM",    # PJM Interconnection
            "eu-west-1": "EIRGRID",  # Ireland grid
        }
        return mapping.get(region, "CAISO")
    
    async def _get_watt_time_token(self) -> str:
        """Get OAuth token for WattTime API"""
        # Simplified - would cache token and refresh when expired
        username = self.api_keys.get("watt_time_username")
        password = self.api_keys.get("watt_time_password")
        
        response = await self.http_client.post(
            f"{self.WATT_TIME_API}/login",
            auth=(username, password)
        )
        response.raise_for_status()
        
        return response.json()["token"]


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================
async def get_cheapest_green_region(
    regions: List[str],
    carbon_engine: CarbonIntelligenceEngine,
    threshold_gco2_kwh: float = 100.0,
) -> Optional[str]:
    """
    Find cheapest region currently in green window.
    
    Helper function for scheduler.
    """
    green_regions = []
    
    for region in regions:
        intensity = await carbon_engine.get_current_intensity(region)
        if intensity.intensity_gco2_kwh < threshold_gco2_kwh:
            green_regions.append((region, intensity.intensity_gco2_kwh))
    
    if not green_regions:
        return None
    
    # Return greenest region (lowest intensity)
    green_regions.sort(key=lambda x: x[1])
    return green_regions[0][0]
