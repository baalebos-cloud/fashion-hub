import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { LogInPayload, SignUpPayload, TokenResponse } from "@/types/auth";
import type { User } from "@/types/user";

export const authApi = {
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
