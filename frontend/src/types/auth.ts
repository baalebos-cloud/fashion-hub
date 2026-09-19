import { User, UserRole } from "./user";
export type { UserRole };

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface LogInPayload {
  email: string;
  password: string;
}

export interface SignUpPayload {
  email: string;
  password: string;
  full_name: string;
  role: string;
  referral_code?: string;
  phone_number?: string; // Made optional to seamlessly handle variations without breaking compilation
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isInitializing: boolean;
  initialize: () => Promise<void>;
  login: (payload: LogInPayload) => Promise<void>;
  signup: (payload: SignUpPayload) => Promise<void>;
  logout: () => void;
}
