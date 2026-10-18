import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { addressesApi } from "@/api/addresses.api";
import { useCart } from "@/hooks/use-cart";
import { useCheckout } from "@/hooks/use-checkout";
import { DeliveryAddressForm } from "./DeliveryAddressForm";
import { Button } from "@/components/ui/button";
import { professionalRoutes } from "@/config/routes.config";
import { formatCurrency } from "@/lib/formatters/currency";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { SavedAddress } from "@/types/address";

export function CheckoutPage() {
  const navigate = useNavigate();
  const { summary, isLoading, error: cartError } = useCart();
  const { submit, isSubmitting, error } = useCheckout();
  const [addresses, setAddresses] = useState<SavedAddress[]>([]);
  const [addressError, setAddressError] = useState<string | null>(null);
  const [selectedAddressId, setSelectedAddressId] = useState("");
  const [selectedVendorId, setSelectedVendorId] = useState("");
  const keys = useRef(new Map<string, string>());
  useEffect(() => {
    let active = true;
    addressesApi.list().then((values) => { if (active) setAddresses(values); })
      .catch((err) => { if (active) setAddressError(getDisplayErrorMessage(err)); });
    return () => { active = false; };
  }, []);
  const vendors = [...new Map((summary?.items ?? []).map((item) => [item.vendor_id, item.vendor_name])).entries()];
  const vendorId = selectedVendorId || vendors[0]?.[0] || "";
  const addressId = selectedAddressId || addresses[0]?.id || "";
  const items = summary?.items.filter((item) => item.vendor_id === vendorId) ?? [];
  const total = items.reduce((sum, item) => sum + item.quantity * item.unit_price_snapshot, 0);
  async function placeOrder() {
    if (!summary || !addressId || !vendorId) return;
    const intent = JSON.stringify([summary.cart_id, summary.revision, vendorId, addressId]);
    if (!keys.current.has(intent)) keys.current.set(intent, crypto.randomUUID());
    try {
      const order = await submit({ cart_id: summary.cart_id, cart_revision: summary.revision, vendor_id: vendorId,
        delivery_address_id: addressId, idempotency_key: keys.current.get(intent)! });
      navigate(professionalRoutes.vendorOrderDetails(order.id));
    } catch { /* useCheckout displays the error; preserve intent/key for retry. */ }
  }
  return (
    <div className="mx-auto flex max-w-lg flex-col gap-5">
      <h1 className="font-display text-xl text-ink">Checkout materials</h1>
      <p className="text-sm text-ink-soft">Each vendor has a separate order and payment. Review the final price before paying. Stock is held for a limited time after creating an order.</p>
      {(cartError || addressError) && <p role="alert">{cartError || addressError}</p>}
      {isLoading && <p role="status">Loading cart…</p>}
      {!isLoading && summary?.items.length === 0 && <p>Your cart is empty. <Link to={professionalRoutes.vendorOrders} className="underline">View material orders</Link></p>}
      <label htmlFor="checkout-vendor">Vendor</label>
      <select id="checkout-vendor" value={vendorId} onChange={(event) => setSelectedVendorId(event.target.value)} disabled={isSubmitting}>
        {vendors.map(([id, name]) => <option key={id} value={id}>{name}</option>)}
      </select>
      <ul>{items.map((item) => <li key={item.id}>{item.product_name} × {item.quantity} — {formatCurrency(item.quantity * item.unit_price_snapshot, item.currency)}{!item.is_available && <span role="alert"> — Unavailable; update your cart.</span>}</li>)}</ul>
      <p>Estimated total: {formatCurrency(total, summary?.currency)}</p>
      <p className="text-xs text-ink-soft">Current catalog prices are confirmed when the order is created. Checkout currently supports Nigeria and NGN.</p>
      <label htmlFor="checkout-address">Delivery address</label>
      <select id="checkout-address" value={addressId} onChange={(event) => setSelectedAddressId(event.target.value)} disabled={isSubmitting}>
        <option value="">Select an address</option>
        {addresses.map((value) => <option key={value.id} value={value.id}>{value.label}: {value.formatted_address}, {value.city}</option>)}
      </select>
      <details><summary className="cursor-pointer underline">Add delivery address</summary><DeliveryAddressForm onSaved={(value) => { setAddresses((previous) => [...previous, value]); setSelectedAddressId(value.id); setAddressError(null); }} /></details>
      {error && <p role="alert" className="text-thread">{error}</p>}
      <Button onClick={() => { void placeOrder(); }} isLoading={isSubmitting} disabled={!addressId || items.length === 0 || items.some((item) => !item.is_available) || isLoading}>Create order and review total</Button>
      <Link to={professionalRoutes.cart} className="underline">Back to cart</Link>
    </div>
  );
}
