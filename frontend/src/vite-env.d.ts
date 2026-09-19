/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_APP_NAME: string
  readonly VITE_APP_ENV: string
  readonly VITE_MAPS_PROVIDER: string
  readonly VITE_MAPS_PUBLIC_KEY: string
  readonly VITE_PAYMENT_PROVIDER: string
  readonly VITE_PAYMENT_PUBLIC_KEY: string
  readonly VITE_ENABLE_AI_ASSISTANT: string
  readonly VITE_ENABLE_MESSAGING: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
