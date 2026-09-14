export interface VendorProduct {
  id: string;
  vendor_id: string;
  category_id?: string | null;
  name: string;
  description?: string | null;
  base_price: number;
  currency: string;
  primary_image_url?: string | null;
  is_active: boolean;
}

export interface ProductVariant {
  id: string;
  product_id: string;
  sku: string;
  attributes?: Record<string, string> | null;
  price: number;
}

export interface Inventory {
  id: string;
  product_variant_id: string;
  quantity_available: number;
  quantity_reserved: number;
}
