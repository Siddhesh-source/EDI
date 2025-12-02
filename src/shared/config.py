"""Configuration management for the trading system."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False
    )
    
    # Database Configuration
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "trading_db"
    postgres_user: str = "trading_user"
    postgres_password: str = "trading_password"
    
    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    
    # NewsAPI Configuration
    newsapi_key: Optional[str] = None
    
    # Kite Connect Configuration
    kite_api_key: Optional[str] = None
    kite_api_secret: Optional[str] = None
    kite_access_token: Optional[str] = None
    
    # API Configuration
    api_key: str = "default_api_key"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Logging Configuration
    log_level: str = "INFO"
    log_file: Optional[str] = "logs/trading_system.log"
    
    # CMS Weights
    cms_weight_sentiment: float = 0.3
    cms_weight_technical: float = 0.5
    cms_weight_regime: float = 0.2
    
    # Signal Thresholds
    cms_buy_threshold: float = 60.0
    cms_sell_threshold: float = -60.0
    
    # Trading Configuration
    enable_auto_trading: bool = False
    position_size: float = 1000.0
    
    @property
    def database_url(self) -> str:
        """Get PostgreSQL database URL."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    @property
    def redis_url(self) -> str:
        """Get Redis connection URL."""
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


# Global settings instance
settings = Settings()
