export interface AddressInput {
  label: string;
  recipient_name: string;
  recipient_phone: string;
  formatted_address: string;
  city: string;
  state_region: string;
  country: string;
  postal_code?: string;
}

export interface SavedAddress extends AddressInput {
  id: string;
}
