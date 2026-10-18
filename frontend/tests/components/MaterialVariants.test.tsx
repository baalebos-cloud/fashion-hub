import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ProductDetails } from "@/components/marketplace/ProductDetails";
import type { VendorProduct } from "@/types/product";
afterEach(cleanup);
it("uses selected variant availability and shows add errors without claiming success", async () => {
  const add = vi.fn().mockRejectedValue(new Error("Stock changed"));
  const product: VendorProduct = { id: "product", vendor_id: "vendor", name: "Fabric", base_price: 10, currency: "NGN", is_active: true };
  render(<ProductDetails product={product} variants={[
    { id: "out", product_id: "product", sku: "sold out", price: 10, quantity_available: 0 },
    { id: "in", product_id: "product", sku: "available", price: 25, quantity_available: 2 },
  ]} inventory={null} onAddToCart={add} />);
  const button = screen.getByRole("button", { name: "Add to cart" }) as HTMLButtonElement;
  expect(button.disabled).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "available" }));
  expect(button.disabled).toBe(false);
  fireEvent.click(button);
  await waitFor(() => expect(add).toHaveBeenCalledWith("in", 1));
  await screen.findByRole("alert");
  expect(button.disabled).toBe(false);
});
