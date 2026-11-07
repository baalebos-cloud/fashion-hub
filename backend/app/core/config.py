"""
Central application configuration.

All configuration is sourced from environment variables (see .env.example).
Never hard-code secrets here. This module is imported everywhere via the
`settings` singleton, so keep it free of side effects other than reading env.
"""
from functools import lru_cache
from typing import Annotated, List, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import NoDecode, BaseSettings, SettingsConfigDict

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

    # --- Admin access ---
    # Only these emails may hold an admin session (comma-separated). In staging/production an
    # empty list means nobody can use the admin area.
    ADMIN_EMAILS: Annotated[List[str], NoDecode] = []  # plain comma list, not JSON
    ADMIN_TOTP_ISSUER: str = "Tailora Admin"
    # Railway (and most PaaS) put a proxy in front of the app; trust its client-IP headers only there.
    TRUST_PROXY_HEADERS: bool = False
    # Activity log (sign-ins and changes, with IP and device) is kept this long, then deleted.
    ACTIVITY_LOG_RETENTION_DAYS: int = 180
    # Shopping activity used for recommendations (views, cart adds, favourites, searches,
    # bookings, purchases). No IP, location or message content is stored; deleted after this long.
    INTERACTION_RETENTION_DAYS: int = 180
    RATE_LIMIT_INTERACTIONS: str = "60/minute"

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
    # Optional secondary resolver. For public Nominatim, configure an identifying
    # contact email and shared Redis to enforce the service-wide request limit.
    GEOCODING_FALLBACK_URL: Optional[str] = None
    GEOCODING_CONTACT_EMAIL: Optional[str] = None

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
    AI_FALLBACK_PROVIDER: str = "groq"
    GROQ_API_KEY: Optional[str] = Field(None, repr=False)
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    # Vision-capable Groq model used as the photo-measurement fallback.
    GROQ_VISION_MODEL: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    VERTEX_AI_API_KEY: Optional[str] = Field(None, repr=False)
    VERTEX_AI_ENABLED: bool = False
    # Temporary hackathon discoverability; does not grant KYC/KYB approval.
    HACKATHON_SHOW_PENDING_PROFESSIONALS: bool = False
    # Optional comma-separated HTTPS origins for demo preview pages.
    HACKATHON_UI_ORIGINS: str = ""
    GCP_PROJECT_ID: Optional[str] = None
    GCP_SERVICE_ACCOUNT_JSON: Optional[str] = Field(None, repr=False)
    GEMINI_API_KEY: Optional[str] = Field(None, repr=False)
    GCP_REGION: str = "us-central1"
    VERTEX_AI_MODEL_NAME: str = "gemini-1.5-flash"

    # --- Notifications ---
    EMAIL_PROVIDER: str = "smtp"
    EMAIL_API_KEY: Optional[str] = None
    EMAIL_FROM_ADDRESS: str = "no-reply@fashionhub.example"
    EMAIL_HOST: str = "localhost"
    EMAIL_PORT: int = 587
    EMAIL_USERNAME: Optional[str] = None
    EMAIL_PASSWORD: Optional[str] = None
    EMAIL_USE_TLS: bool = True
    # --- Dispatch pricing (naira). Suggested fare = base + per_km * road_km, min fare applies. ---
    DISPATCH_BASE_FARE: int = 500
    DISPATCH_PER_KM_FARE: int = 150
    DISPATCH_MIN_FARE: int = 1000
    # Straight-line distance is multiplied by this to approximate road distance.
    DISPATCH_ROAD_FACTOR: float = 1.35
    DISPATCH_OFFER_TTL_MINUTES: int = 10
    # Sequential auto-offers (phase 3). Off by default: when on, each new job is offered to the
    # best-ranked eligible rider with an exclusive window, then the next; finally the open board.
    DISPATCH_AUTO_OFFER_ENABLED: bool = False
    DISPATCH_AUTO_OFFER_TTL_SECONDS: int = 90
    DISPATCH_AUTO_OFFER_MAX_ATTEMPTS: int = 5
    DISPATCH_AUTO_OFFER_RADIUS_KM: float = 20.0
    # Explainable scoring for auto-offers (logistics phase 3). Off keeps the original order:
    # nearest by straight line, then rating, then experience.
    DISPATCH_SMART_SCORING_ENABLED: bool = False
    DISPATCH_SCORING_ROUTE_TOP_N: int = 5   # road ETAs computed for at most this many riders per offer
    # Multi-stop routes (logistics phase 4): dispatchers may add a job to a busy rider's route
    # when the planned route stays within capacity and the time limit.
    DISPATCH_MULTISTOP_ENABLED: bool = False
    # External courier companies (logistics phase 6). Comma list of enabled adapters; empty = none.
    # "sandbox" is a pretend courier for development and is refused in production.
    EXTERNAL_COURIERS: Annotated[List[str], NoDecode] = []
    SANDBOX_COURIER_WEBHOOK_SECRET: Optional[str] = Field(None, repr=False)
    # Delivery intelligence (logistics phase 7). Both off until validated and approved.
    DELIVERY_ETA_CALIBRATION_ENABLED: bool = False
    DELIVERY_AI_SUMMARIES_ENABLED: bool = False
    # Control tower alert thresholds (logistics phase 5), in minutes / km.
    DISPATCH_ALERT_UNASSIGNED_MIN: int = 15
    DISPATCH_ALERT_PICKUP_MIN: int = 30
    DISPATCH_ALERT_DROPOFF_MIN: int = 90            # used when no route time is known
    DISPATCH_ALERT_DROPOFF_FACTOR: float = 1.5      # route time x factor + grace
    DISPATCH_ALERT_DROPOFF_GRACE_MIN: int = 15
    DISPATCH_ALERT_TRACKING_MIN: int = 5
    DISPATCH_ALERT_OFF_ROUTE_KM: float = 3.0
    DISPATCH_BATCH_MAX_MINUTES: int = 150
    DISPATCH_VEHICLE_CAPACITY: dict = {"foot": 1, "bike": 3, "car": 8, "van": 20}  # orders carried at once
    # Shareable recipient tracking links (phase 4).
    TRACKING_LINK_TTL_HOURS: int = 168          # 7 days
    TRACKING_LINK_AFTER_DELIVERY_HOURS: int = 48  # links stop working this long after delivery
    TRACKING_LINK_MAX_ACTIVE: int = 3
    # Road routing (logistics phase 1). "none" keeps the labelled straight-line estimate.
    ROUTING_PROVIDER: str = "none"  # none | google | osrm
    ROUTING_GOOGLE_API_KEY: Optional[str] = Field(None, repr=False)  # server key with Routes API + billing
    ROUTING_GOOGLE_TWO_WHEELER: bool = False  # use Google's two-wheeler mode for bikes where supported
    ROUTING_OSRM_URL: Optional[str] = None
    ROUTING_TIMEOUT_SECONDS: float = 3.0
    ROUTING_RETRIES: int = 1
    ROUTING_CACHE_SECONDS: int = 86400          # routes without live traffic
    ROUTING_TRAFFIC_CACHE_SECONDS: int = 900    # traffic-aware routes go stale faster
    ROUTING_LIVE_ETA_SECONDS: int = 60          # live ETA recomputed at most this often per delivery
    ROUTING_BREAKER_THRESHOLD: int = 3
    ROUTING_BREAKER_WINDOW_SECONDS: int = 120
    ROUTING_BREAKER_COOLDOWN_SECONDS: int = 120
    # Fares stay on the straight-line formula until the owner approves pricing from road distance.
    DISPATCH_PRICE_FROM_ROAD_ROUTES: bool = False
    # Delivery proof (phase 6). Codes are one-time, expire, and rotate on request.
    HANDOVER_CODE_TTL_MINUTES: int = 30
    PICKUP_CODE_TTL_MINUTES: int = 30
    # The seller gives the rider a pickup code; the rider enters it to start the trip.
    DELIVERY_PICKUP_CODE_REQUIRED: bool = True
    # Buyer alerts from the rider's shared GPS (phase 7).
    DELIVERY_PROXIMITY_ALERTS_ENABLED: bool = True
    DELIVERY_APPROACH_ALERT_MINUTES: int = 5
    DELIVERY_ARRIVAL_RADIUS_M: int = 150
    # --- Masked voice calls (Africa's Talking). Numbers are never shown to the other party. ---
    # None disables calling; "sandbox" fakes the provider for local testing; "africastalking" is live.
    VOICE_PROVIDER: Optional[str] = None
    AT_USERNAME: Optional[str] = None
    AT_API_KEY: Optional[str] = Field(None, repr=False)
    AT_VOICE_NUMBER: Optional[str] = None  # Tailora's virtual number, E.164, e.g. +2341...
    AT_ENVIRONMENT: str = "sandbox"  # sandbox | production
    VOICE_WEBHOOK_SECRET: Optional[str] = Field(None, repr=False)
    VOICE_CALLBACK_WINDOW_HOURS: int = 2
    VOICE_MAX_CALL_SECONDS: int = 900
    SMS_PROVIDER: Optional[str] = None
    SMS_API_KEY: Optional[str] = None
    PUSH_PROVIDER: Optional[str] = None

    # --- Object storage ---
    STORAGE_PROVIDER: str = "local"  # local | postgres | s3-compatible
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
    # Business (CAC) lookups for KYB. "manual" sends every submission to admin review.
    KYB_PROVIDER: str = "manual"  # manual | prembly
    # Prembly key for CAC lookups; falls back to NIN_API_KEY (same Prembly account).
    PREMBLY_API_KEY: Optional[str] = Field(None, repr=False)
    PREMBLY_CAC_URL: str = "https://api.prembly.com/verification/cac/advance"

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

    @field_validator("EMAIL_FROM_ADDRESS", mode="before")
    @classmethod
    def clean_sender(cls, v):
        # Dashboards make it easy to paste "Tailora <hello@x>" with the quotes or a trailing newline.
        if isinstance(v, str):
            v = v.strip()
            # Only quotes wrapping the whole value; '"Tailora Support" <hello@x>' keeps its own.
            if len(v) >= 2 and v[0] == v[-1] and v[0] in {'"', "'"}:
                v = v[1:-1].strip()
        return v

    @field_validator("EXTERNAL_COURIERS", mode="before")
    @classmethod
    def split_couriers(cls, v):
        if isinstance(v, str):
            v = v.split(",")
        return [item.strip().lower() for item in (v or []) if item and item.strip()]

    @field_validator("ADMIN_EMAILS", mode="before")
    @classmethod
    def split_admin_emails(cls, v):
        if isinstance(v, str):
            v = [item for item in v.split(",")]
        return [item.strip().lower() for item in (v or []) if item and item.strip()]

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
