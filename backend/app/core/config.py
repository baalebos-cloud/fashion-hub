"""
Central application configuration.

All configuration is sourced from environment variables (see .env.example).
Never hard-code secrets here. This module is imported everywhere via the
`settings` singleton, so keep it free of side effects other than reading env.
"""
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.database_url import normalize_database_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", hide_input_in_errors=True,
    )

    # --- Application ---
    APP_ENV: str = "development"  # development | staging | production
    APP_NAME: str = "Fashion Hub"
    APP_URL: str = "http://localhost:8005"
    FRONTEND_URL: str = "http://localhost:5173"
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = True

    # --- Database ---
    DATABASE_URL: str = Field(
        "postgresql+psycopg://fashionhub:fashionhub@localhost:5435/fashionhub", repr=False,
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_ECHO: bool = False

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Celery ---
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # --- Authentication / JWT ---
    SECRET_KEY: str = "change-me-in-env"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
    EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # --- CORS ---
    CORS_ALLOWED_ORIGINS: List[str] = ["http://localhost:5173"]

    # --- Rate limiting ---
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_AUTH: str = "10/minute"
    RATE_LIMIT_WEBHOOK: str = "60/minute"
    RATE_LIMIT_STORAGE_URI: str = "memory://"

    # --- Payments ---
    VENDOR_RESERVATION_TTL_MINUTES: int = Field(15, ge=1, le=120)
    PAYMENT_PROVIDER: str = "paystack"  # paystack | flutterwave
    PAYMENTS_ENABLED: bool = False  # existing production release gate
    ENABLE_PRODUCTION_PAYMENTS: bool = False  # additional hard-disabled Saga release gate
    PAYMENT_SECRET_KEY: Optional[str] = None
    PAYMENT_PUBLIC_KEY: Optional[str] = None
    PAYMENT_WEBHOOK_SECRET: Optional[str] = None
    # Isolated Interswitch test-environment gate. Never enabled in production.
    INTERSWITCH_SANDBOX_ENABLED: bool = False
    INTERSWITCH_MERCHANT_CODE: Optional[str] = None
    INTERSWITCH_PAY_ITEM_ID: Optional[str] = None
    # Isolated, opt-in hackathon live Web Checkout (never activate in staging).
    INTERSWITCH_LIVE_ENABLED: bool = False
    INTERSWITCH_LIVE_MERCHANT_CODE: Optional[str] = None
    INTERSWITCH_LIVE_PAY_ITEM_ID: Optional[str] = None
    # Financial operations require explicit provider onboarding and sandbox verification.
    REFUND_EXECUTION_ENABLED: bool = False

    # --- Maps / Geocoding ---
    MAP_PROVIDER: str = "google_maps"  # google_maps | mapbox
    MAPS_API_KEY: Optional[str] = None

    # --- Delivery ---
    DELIVERY_PROVIDER: str = "internal"
    DELIVERY_API_KEY: Optional[str] = None
    DELIVERY_WEBHOOK_SECRET: Optional[str] = None

    # --- KYC / KYB ---
    KYC_PROVIDER: str = "manual"
    KYC_API_KEY: Optional[str] = None
    IDENTITY_ENCRYPTION_KEY: Optional[str] = Field(None, repr=False)

    # --- AI Assistant ---
    AI_PROVIDER: str = "anthropic"
    AI_API_KEY: Optional[str] = None
    AI_MODEL: str = "claude-sonnet-4-6"
    VERTEX_AI_API_KEY: Optional[str] = Field(None, repr=False)
    VERTEX_AI_ENABLED: bool = False
    GCP_PROJECT_ID: Optional[str] = None
    GCP_SERVICE_ACCOUNT_JSON: Optional[str] = Field(None, repr=False)
    GCP_REGION: str = "us-central1"
    VERTEX_AI_MODEL_NAME: str = "gemini-3.8-flash"

    # --- Notifications ---
    EMAIL_PROVIDER: str = "smtp"
    EMAIL_API_KEY: Optional[str] = None
    EMAIL_FROM_ADDRESS: str = "no-reply@fashionhub.example"
    EMAIL_HOST: str = "localhost"
    EMAIL_PORT: int = 587
    EMAIL_USERNAME: Optional[str] = None
    EMAIL_PASSWORD: Optional[str] = None
    EMAIL_USE_TLS: bool = True
    SMS_PROVIDER: Optional[str] = None
    SMS_API_KEY: Optional[str] = None
    PUSH_PROVIDER: Optional[str] = None

    # --- Object storage ---
    STORAGE_PROVIDER: str = "local"  # local | s3-compatible
    STORAGE_BUCKET: Optional[str] = None
    STORAGE_ENDPOINT: Optional[str] = None
    STORAGE_ACCESS_KEY: Optional[str] = None
    STORAGE_SECRET_KEY: Optional[str] = None
    STORAGE_PUBLIC_BASE_URL: Optional[str] = None

    # --- Pagination ---
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # --- Weather (delivery-time forecasts) ---
    WEATHER_PROVIDER: str = "openweathermap"
    WEATHER_API_KEY: Optional[str] = None

    # --- NIN identity verification (KYC) ---
    NIN_PROVIDER: str = "manual"
    NIN_API_KEY: Optional[str] = None

    # --- WhatsApp notifications ---
    WHATSAPP_PROVIDER: Optional[str] = None
    WHATSAPP_API_KEY: Optional[str] = None
    WHATSAPP_FROM_NUMBER: Optional[str] = None

    # --- Platform economics ---
    # Never exposed to the customer role — see docs/commission.md. The
    # professional's quoted price to the customer already has this baked
    # in; this rate is only used to compute the professional/vendor's own
    # net payout.
    PLATFORM_COMMISSION_RATE: float = 0.15
    # Share of the PLATFORM's commission (not of the order total) paid out
    # to whoever referred the seller, once the seller's referred signup
    # completes their first successful paid order.
    REFERRAL_COMMISSION_SHARE: float = 0.20

    @field_validator("DATABASE_URL")
    @classmethod
    def valid_database_url(cls, value: str) -> str:
        return normalize_database_url(value)

    @field_validator("CORS_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def split_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("APP_ENV")
    @classmethod
    def valid_environment(cls, value: str) -> str:
        if value not in {"development", "test", "staging", "production"}:
            raise ValueError("Invalid APP_ENV")
        return value

    @model_validator(mode="after")
    def validate_deployment(self):
        if self.ENABLE_PRODUCTION_PAYMENTS:
            raise ValueError("Production Saga payments are not approved or implemented.")
        if self.APP_ENV in {"staging", "production"}:
            if len(self.SECRET_KEY) < 32:
                raise ValueError("Signing configuration must contain at least 32 random characters")
            if self.DEBUG or self.DATABASE_ECHO:
                raise ValueError("Disable DEBUG and DATABASE_ECHO in staging/production")
            if not self.FRONTEND_URL.startswith("https://"):
                raise ValueError("Configure an HTTPS FRONTEND_URL for authentication email links")
            if not self.CORS_ALLOWED_ORIGINS or any(
                origin == "*" or not origin.startswith("https://")
                for origin in self.CORS_ALLOWED_ORIGINS
            ):
                raise ValueError("Configure explicit HTTPS CORS origins in staging/production")
            if not self.RATE_LIMIT_STORAGE_URI.startswith(("redis://", "rediss://")):
                raise ValueError("Use shared Redis rate-limit storage in staging/production")
        return self

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
