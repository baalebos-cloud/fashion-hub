/**
 * Every backend route path used by src/api/*.api.ts lives here, mirroring
 * backend/app/api/v1/*.py exactly (see backend/docs/api-reference.md).
 * No file outside this one should contain a literal "/orders/..." string.
 */
export const endpoints = {
  auth: {
    signup: "/auth/signup",
    login: "/auth/login",
    refresh: "/auth/refresh",
    logout: "/auth/logout",
    verifyEmail: "/auth/verify-email",
    forgotPassword: "/auth/forgot-password",
    resetPassword: "/auth/reset-password",
  },

  users: {
    me: "/users/me",
  },

  customers: {
    me: "/customers/me",
  },

  professionals: {
    list: "/professionals",
    details: (id: string) => `/professionals/${id}`,
  },

  tailors: {
    details: (id: string) => `/tailors/${id}`,
  },

  designers: {
    details: (id: string) => `/designers/${id}`,
  },

  vendors: {
    list: "/vendors",
    details: (id: string) => `/vendors/${id}`,
  },

  vendorProducts: {
    list: "/vendor-products",
    details: (id: string) => `/vendor-products/${id}`,
  },

  categories: {
    list: "/categories",
  },

  cart: {
    summary: "/carts",
    items: "/carts/items",
    item: (id: string) => `/carts/items/${id}`,
  },

  checkout: {
    submit: "/checkout",
  },

  orders: {
    list: "/orders",
    details: (id: string) => `/orders/${id}`,
    accept: (id: string) => `/orders/${id}/accept`,
    startProduction: (id: string) => `/orders/${id}/start-production`,
    ready: (id: string) => `/orders/${id}/ready`,
    ship: (id: string) => `/orders/${id}/ship`,
    tracking: (id: string) => `/orders/${id}/tracking`,
    received: (id: string) => `/orders/${id}/received`,
    timeline: (id: string) => `/orders/${id}/timeline`,
    review: (id: string) => `/orders/${id}/review`,
    cancel: (id: string) => `/orders/${id}/cancel`,
  },

  payments: {
    initialize: "/payments",
    verify: (reference: string) => `/payments/${reference}/verify`,
  },

  invoices: {
    details: (id: string) => `/invoices/${id}`,
    byOrder: (orderId: string) => `/invoices/by-order/${orderId}`,
  },

  deliveries: {
    details: (id: string) => `/deliveries/${id}`,
  },

  tracking: {
    byOrder: (orderId: string) => `/orders/${orderId}/tracking`,
  },

  locations: {
    create: "/locations",
  },

  maps: {
    geocode: "/geocoding/geocode",
    reverseGeocode: "/geocoding/reverse",
  },

  measurements: {
    list: "/measurements",
    create: "/measurements",
  },

  designs: {
    list: "/designs",
    details: (id: string) => `/designs/${id}`,
  },

  reviews: {
    forProfessional: (professionalId: string) => `/reviews?professional_id=${professionalId}`,
  },

  notifications: {
    list: "/notifications",
    markRead: (id: string) => `/notifications/${id}/read`,
  },

  messages: {
    conversations: "/messages/conversations",
    inConversation: (conversationId: string) => `/messages/conversations/${conversationId}/messages`,
  },

  ai: {
    sendMessage: "/ai/navigation/messages",
    conversations: "/ai/navigation/conversations",
    conversationMessages: (id: string) => `/ai/navigation/conversations/${id}/messages`,
    feedback: "/ai/navigation/feedback",
  },

  kyc: {
    submit: "/kyc",
    status: "/kyc/status",
  },

  kyb: {
    submit: "/kyb",
    status: "/kyb/status",
  },

  favorites: {
    toggle: "/favorites",
  },

  search: {
    professionals: "/search/professionals",
    designs: "/search/designs",
    products: "/search/vendor-products",
  },

  dashboard: {
    summary: "/dashboard",
  },
} as const;
