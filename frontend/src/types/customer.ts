export interface Customer {
  id: string;
  user_id: string;
  preferred_currency: string;
  default_measurement_profile_id?: string | null;
}
