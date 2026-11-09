export type UserRole = 'admin' | 'customer' | 'vendor' | 'tailor' | 'designer' | 'delivery_partner';

export interface User {
  id: string;
  email: string;
  full_name: string;
  /** The name in three parts; older accounts may only have full_name (see lib/names.ts). */
  first_name?: string | null;
  middle_name?: string | null;
  last_name?: string | null;
  role: UserRole;
  is_email_verified: boolean;
  is_phone_verified: boolean;
  timezone?: string;
  profile_photo_url?: string;
  whatsapp_number?: string;
}
