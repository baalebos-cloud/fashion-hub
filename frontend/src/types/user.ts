export type UserRole = 'admin' | 'customer' | 'vendor' | 'professional' | 'tailor' | 'designer' | 'delivery_partner' | string;

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_email_verified: boolean;
  is_phone_verified: boolean;
  timezone?: string;
  profile_photo_url?: string;
  whatsapp_number?: string;
}
