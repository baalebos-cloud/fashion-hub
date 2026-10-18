export interface CartItem {
  id: string;
  product_variant_id: string;
  vendor_id: string;
  product_name: string;
  sku: string;
  vendor_name: string;
  currency: string;
  is_available: boolean;
  quantity: number;
  unit_price_snapshot: number;
}

export interface CartSummary {
  cart_id: string;
  revision: number;
  currency: string;
  items: CartItem[];
  subtotal: number;
}
