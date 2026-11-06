import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { LogInPayload, SignUpPayload, TokenResponse } from "@/types/auth";
import type { User } from "@/types/user";

export interface AdminSignInStep {
  step: "enroll" | "code";
  challenge: string;
  /** Only on first sign-in: the authenticator setup key. */
  secret?: string;
  otpauth_uri?: string;
}

export const authApi = {
  /** Admin step 1: password. Returns a short-lived challenge for the authenticator code. */
  async adminLogIn(email: string, password: string): Promise<AdminSignInStep> {
    return (await apiClient.post<AdminSignInStep>("/auth/admin/login", { email, password })).data;
  },
  /** Admin step 2: the six-digit code from the authenticator app. */
  async adminVerify(challenge: string, code: string): Promise<Pick<TokenResponse, "access_token" | "refresh_token" | "token_type">> {
    return (await apiClient.post<TokenResponse>("/auth/admin/verify", { challenge, code })).data;
  },

  async signUp(payload: SignUpPayload): Promise<User> {
    const response = await apiClient.post<User>(endpoints.auth.signup, payload);
    return response.data;
  },

  async logIn(payload: LogInPayload): Promise<TokenResponse> {
    const response = await apiClient.post<TokenResponse>(endpoints.auth.login, payload);
    return response.data;
  },

  async logOut(refreshToken: string): Promise<void> {
    await apiClient.post(endpoints.auth.logout, { refresh_token: refreshToken });
  },

  async verifyEmail(token: string): Promise<void> {
    await apiClient.post(endpoints.auth.verifyEmail, { token });
  },

  async forgotPassword(email: string): Promise<void> {
    await apiClient.post(endpoints.auth.forgotPassword, { email });
  },

  async resetPassword(token: string, newPassword: string): Promise<void> {
    await apiClient.post(endpoints.auth.resetPassword, { token, new_password: newPassword });
  },
};
