import type { UserRole } from "./auth";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_email_verified: boolean;
  is_phone_verified: boolean;
  profile_photo_url?: string | null;
  timezone: string;
}
