export interface InvoiceLineItem {
  name: string;
  unit_price: number;
  quantity: number;
  line_total: number;
}

export interface Invoice {
  id: string;
  invoice_number: string;
  order_id: string;
  subtotal: number;
  delivery_fee: number;
  tax_amount: number;
  discount_amount: number;
  total_amount: number;
  currency: string;
  payment_status: string;
  pdf_url?: string | null;
}
