import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    # General App Configuration
    APP_ENV: str = "development"
    APP_NAME: str = "Fashion Hub Backend"
    APP_URL: str = "http://localhost:5000"
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = True

    # Database Configuration
    DATABASE_URL: str = "postgresql+psycopg://fashionhub:fashionhub@127.0.0.1:5433/fashionhub"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_ECHO: bool = False

    # Infrastructure Services Caching/Queues
    REDIS_URL: str = "redis://127.0.0.1:6373/0"
    CELERY_BROKER_URL: str = "redis://127.0.0.1:6373/0"
    CELERY_RESULT_BACKEND: str = "redis://127.0.0.1:6373/0"

    # Security & Tokens Configurations
    SECRET_KEY: str = "super-secret-development-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 15
    EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES: int = 1440

    # Cross-Origin Policies & Security Restrictions
    CORS_ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5000", "http://127.0.0.1:5000"]
    RATE_LIMIT_DEFAULT: str = "60 per minute"
    RATE_LIMIT_AUTH: str = "5 per minute"
    RATE_LIMIT_WEBHOOK: str = "100 per minute"

    # External Integrations (Payments/Geo-Maps)
    PAYMENT_PROVIDER: str = "paystack"
    PAYMENT_SECRET_KEY: Optional[str] = ""
    PAYMENT_PUBLIC_KEY: Optional[str] = ""
    PAYMENT_WEBHOOK_SECRET: Optional[str] = ""
    MAP_PROVIDER: str = "google"
    MAPS_API_KEY: Optional[str] = ""

    # Operations Logistics (Fulfillment/Verification Checks)
    DELIVERY_PROVIDER: str = "internal"
    DELIVERY_API_KEY: Optional[str] = ""
    DELIVERY_WEBHOOK_SECRET: Optional[str] = ""
    KYC_PROVIDER: str = "manual"
    KYC_API_KEY: Optional[str] = ""

    # Intelligent Assistant Infrastructure Setup
    AI_PROVIDER: str = "anthropic"
    AI_API_KEY: Optional[str] = ""
    AI_MODEL: str = "claude-3-5-sonnet"

    # Messaging Dispatch Interfaces
    EMAIL_PROVIDER: str = "smtp"
    EMAIL_API_KEY: Optional[str] = ""
    EMAIL_FROM_ADDRESS: str = "noreply@fashionhub.com"
    SMS_PROVIDER: str = "twilio"
    SMS_API_KEY: Optional[str] = ""
    PUSH_PROVIDER: str = "firebase"

    # Object Asset Storage Configuration
    STORAGE_PROVIDER: str = "local"
    STORAGE_BUCKET: str = "fashionhub-media"
    STORAGE_ENDPOINT: Optional[str] = ""
    STORAGE_ACCESS_KEY: Optional[str] = ""
    STORAGE_SECRET_KEY: Optional[str] = ""
    STORAGE_PUBLIC_BASE_URL: str = "http://localhost:5000/static"

    # Pagination Metrics Parameters 
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # Fixed: Computed dynamic property expected by app/main.py
    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"

settings = Settings()
