export interface CartItem {
  id: string;
  product_variant_id: string;
  vendor_id: string;
  quantity: number;
  unit_price_snapshot: number;
}

export interface CartSummary {
  cart_id: string;
  items: CartItem[];
  subtotal: number;
}
