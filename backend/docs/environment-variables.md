# Environment Variables

See `.env.example` for the authoritative, always-up-to-date list with
defaults. Grouped summary:

| Group | Key variables |
|---|---|
| Application | `APP_ENV`, `APP_URL`, `API_PREFIX`, `DEBUG` |
| Database | `DATABASE_URL`, `DATABASE_POOL_SIZE`, `DATABASE_MAX_OVERFLOW` |
| Redis | `REDIS_URL` |
| Celery | `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` |
| Auth | `SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` |
| CORS | `CORS_ALLOWED_ORIGINS` (comma-separated) |
| Rate limiting | `RATE_LIMIT_DEFAULT`, `RATE_LIMIT_AUTH`, `RATE_LIMIT_WEBHOOK` |
| Payments | `PAYMENT_PROVIDER` (`paystack`\|`flutterwave`), `PAYMENT_SECRET_KEY`, `PAYMENT_WEBHOOK_SECRET` |
| Maps | `MAP_PROVIDER` (`google_maps`\|`mapbox`), `MAPS_API_KEY` |
| Delivery | `DELIVERY_PROVIDER` (`internal` by default) |
| KYC/KYB | `KYC_PROVIDER` (`manual` by default) |
| AI | `AI_PROVIDER`, `AI_API_KEY`, `AI_MODEL` |
| Notifications | `EMAIL_PROVIDER`, `EMAIL_FROM_ADDRESS`, `SMS_PROVIDER`, `PUSH_PROVIDER` |
| Storage | `STORAGE_PROVIDER` (`local`\|s3-compatible), `STORAGE_BUCKET`, `STORAGE_ENDPOINT` |

`app/core/config.py::Settings` (Pydantic Settings) is the single source of
truth for how these are parsed and defaulted — consult it directly if this
table and the code ever drift.

**Never commit `.env`.** `.gitignore` already excludes it.
