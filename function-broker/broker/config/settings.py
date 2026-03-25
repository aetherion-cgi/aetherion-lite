"""
Function Broker Settings
Configuration management for the broker service
"""

from pydantic import BaseSettings
from pathlib import Path
from typing import List, Optional

# Resolve the function-broker repo root: settings.py -> config -> broker -> function-broker
ROOT_DIR = Path(__file__).resolve().parents[2]


class BrokerSettings(BaseSettings):
    """Configuration settings for the Function Broker"""
    
    # Service identification
    service_name: str = "function-broker"
    service_version: str = "1.0.0"
    environment: str = "production"
    
    # API configuration
    host: str = "0.0.0.0"
    port: int = 8100
    log_level: str = "INFO"
    
    # Capability registry
    capabilities_file: Path = ROOT_DIR / "broker" / "config" / "capabilities.yaml"
    
    # Security settings
    strict_security: bool = True
    internal_network_cidrs: List[str] = ["10.0.0.0/8", "172.16.0.0/12"]
    require_mtls: bool = False
    
    # mTLS certificates
    ca_bundle: Optional[str] = None 
    #"""/etc/ssl/certs/aetherion-ca.crt"""
    server_cert: Optional[str] = None  # /etc/ssl/certs/function-broker.crt
    server_key: Optional[str] = None  # /etc/ssl/private/function-broker.key
    client_cert: Optional[str] = None # /etc/ssl/certs/function-broker-client.crt
    client_key: Optional[str] = None # /etc/ssl/private/function-broker-client.key
    
    # Adapter timeouts
    default_timeout: int = 30
    urpe_timeout: int = 120
    bue_timeout: int = 60
    
    # Retry configuration
    max_retries: int = 3
    retry_backoff_multiplier: int = 2
    initial_retry_delay_ms: int = 100
    
    # Observability
    enable_metrics: bool = True
    metrics_port: int = 9100
    enable_tracing: bool = True
    jaeger_endpoint: str = "http://jaeger:14268/api/traces"
    
    # Database (for audit records)
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "aetherion"
    postgres_user: str = "aetherion"
    postgres_password: str = ""  # Set via environment variable
    
    # Redis (for caching)
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    
    # Performance tuning
    max_concurrent_requests: int = 100
    request_timeout: int = 300
    keep_alive_timeout: int = 65
    
    # Feature flags
    enable_capability_caching: bool = True
    enable_hot_reload: bool = False  # Set to True in dev
    enable_audit_logging: bool = True
    
    class Config:
        env_prefix = "BROKER_"
        case_sensitive = False
        env_file = ".env"


# Global settings instance
settings = BrokerSettings()
