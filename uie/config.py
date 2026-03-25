"""
Aetherion UIE Configuration
Absorbs Cortex Gateway functionality into UIE
"""
import os
from typing import Optional
from pydantic import BaseModel, Field


class ServiceConfig(BaseModel):
    """Configuration for UIE service"""
    
    # Server settings
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)  # PUBLIC PORT for CustomGPT/Claude
    workers: int = Field(default=4)
    
    # Mode
    mode: str = Field(default="public")  # UIE is now public-facing
    
    # Security
    api_key_header: str = Field(default="X-API-Key")
    require_api_key: bool = Field(default=True)
    allowed_api_keys: list[str] = Field(default_factory=list)
    
    # Rate limiting
    rate_limit_enabled: bool = Field(default=True)
    rate_limit_per_minute: int = Field(default=60)
    rate_limit_per_hour: int = Field(default=1000)
    
    # Function Broker connection (internal)
    function_broker_url: str = Field(default="https://function-broker:8081")
    function_broker_timeout: int = Field(default=300)  # 5 minutes for complex queries
    
    # mTLS settings
    mtls_enabled: bool = Field(default=True, env="AETHERION_MTLS_ENABLED")
    mtls_cert_path: str = Field(default="/certs/uie.crt")
    mtls_key_path: str = Field(default="/certs/uie.key")
    mtls_ca_path: str = Field(default="/certs/ca.crt")
    
    # Conversation settings
    session_timeout_minutes: int = Field(default=60)
    max_conversation_history: int = Field(default=50)
    
    # LLM settings (for intent parsing and synthesis)
    llm_model: str = Field(default="gpt-4")
    llm_temperature: float = Field(default=0.7)
    llm_max_tokens: int = Field(default=2000)
    
    # Governance
    governance_enabled: bool = Field(default=True)
    default_jurisdiction: str = Field(default="US")
    
    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")
    
    # Feature flags
    enable_streaming: bool = Field(default=True)
    enable_multi_step_reasoning: bool = Field(default=True)
    enable_conversation_memory: bool = Field(default=True)

    # http timeout
    http_timeout: float = Field(default=30.0)


def load_config() -> ServiceConfig:
    """Load configuration from environment variables"""
    return ServiceConfig(
        host=os.getenv("UIE_HOST", "0.0.0.0"),
        port=int(os.getenv("UIE_PORT", "8000")),
        workers=int(os.getenv("UIE_WORKERS", "4")),
        mode=os.getenv("UIE_MODE", "public"),
        
        # Security
        require_api_key=os.getenv("UIE_REQUIRE_API_KEY", "true").lower() == "true",
        allowed_api_keys=os.getenv("UIE_ALLOWED_API_KEYS", "").split(",") if os.getenv("UIE_ALLOWED_API_KEYS") else [],
        
        # Rate limiting
        rate_limit_enabled=os.getenv("UIE_RATE_LIMIT_ENABLED", "true").lower() == "true",
        rate_limit_per_minute=int(os.getenv("UIE_RATE_LIMIT_PER_MINUTE", "60")),
        rate_limit_per_hour=int(os.getenv("UIE_RATE_LIMIT_PER_HOUR", "1000")),
        
        # Function Broker
        function_broker_url=os.getenv("FUNCTION_BROKER_URL", "https://function-broker:8081"),
        function_broker_timeout=int(os.getenv("FUNCTION_BROKER_TIMEOUT", "300")),
        
        # mTLS
        mtls_enabled=os.getenv("MTLS_ENABLED", "true").lower() == "true",
        mtls_cert_path=os.getenv("MTLS_CERT_PATH", "/certs/uie.crt"),
        mtls_key_path=os.getenv("MTLS_KEY_PATH", "/certs/uie.key"),
        mtls_ca_path=os.getenv("MTLS_CA_PATH", "/certs/ca.crt"),
        
        # Conversation
        session_timeout_minutes=int(os.getenv("SESSION_TIMEOUT_MINUTES", "60")),
        max_conversation_history=int(os.getenv("MAX_CONVERSATION_HISTORY", "50")),
        
        # LLM
        llm_model=os.getenv("LLM_MODEL", "gpt-4"),
        llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
        llm_max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2000")),
        
        # Governance
        governance_enabled=os.getenv("GOVERNANCE_ENABLED", "true").lower() == "true",
        default_jurisdiction=os.getenv("DEFAULT_JURISDICTION", "US"),
        
        # Logging
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_format=os.getenv("LOG_FORMAT", "json"),
        
        # Feature flags
        enable_streaming=os.getenv("ENABLE_STREAMING", "true").lower() == "true",
        enable_multi_step_reasoning=os.getenv("ENABLE_MULTI_STEP_REASONING", "true").lower() == "true",
        enable_conversation_memory=os.getenv("ENABLE_CONVERSATION_MEMORY", "true").lower() == "true",
    )


# Global config instance
config = load_config()
