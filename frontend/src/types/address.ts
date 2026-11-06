export interface AddressInput {
  label: string;
  recipient_name: string;
  recipient_phone: string;
  formatted_address: string;
  city: string;
  state_region: string;
  country: string;
  postal_code?: string;
  /** Nigerian addressing details riders navigate by. All optional. */
  lga?: string | null;
  landmark?: string | null;
  nearest_bus_stop?: string | null;
  delivery_instructions?: string | null;
  latitude: number;
  longitude: number;
}

export interface SavedAddress extends AddressInput {
  id: string;
  is_default: boolean;
}
