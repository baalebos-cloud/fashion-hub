export type UserRole = "customer" | "tailor" | "designer" | "vendor" | "delivery_partner" | "admin";

export interface SignUpPayload {
  email: string;
  phone_number?: string;
  password: string;
  full_name: string;
  role: UserRole;
}

export interface LogInPayload {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
}

export interface AuthSession {
  accessToken: string;
  refreshToken: string;
}
