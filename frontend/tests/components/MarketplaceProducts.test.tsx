import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ProductDetails } from "@/components/marketplace/ProductDetails";
import { ProductCard } from "@/components/marketplace/ProductCard";
import type { VendorProduct } from "@/types/product";

afterEach(cleanup);

const base: VendorProduct = {
  id: "p1", vendor_id: "v1", vendor_name: "Lagos Fabrics", name: "French lace", base_price: 12000, currency: "NGN",
  is_active: true, primary_image_url: "https://cdn.example/1.jpg",
  image_urls: ["https://cdn.example/1.jpg", "https://cdn.example/2.jpg", "https://cdn.example/3.jpg"],
  variants: [{ id: "var1", product_id: "p1", sku: "FH-1", price: 12000, quantity_available: 5 }],
};

describe("product page", () => {
  it("shows every photo the vendor added", () => {
    render(<ProductDetails product={base} variants={base.variants!} inventory={null} onAddToCart={vi.fn()} />);
    const thumbnails = screen.getAllByRole("button").filter((b) => b.querySelector("img"));
    expect(thumbnails).toHaveLength(3);
    fireEvent.click(thumbnails[2]);
    expect(screen.getByAltText("French lace").getAttribute("src")).toBe("https://cdn.example/3.jpg");
  });

  it("older products with one photo still show it", () => {
    render(<ProductDetails product={{ ...base, image_urls: [] }} variants={base.variants!} inventory={null} onAddToCart={vi.fn()} />);
    expect(screen.getByAltText("French lace").getAttribute("src")).toBe("https://cdn.example/1.jpg");
  });

  it("can't be ordered until the vendor is verified", () => {
    render(<ProductDetails product={{ ...base, vendor_verified: false }} variants={base.variants!} inventory={null} onAddToCart={vi.fn()} />);
    expect(screen.getByText(/Lagos Fabrics is still being verified/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Add to cart" })).toBeNull();
  });
});

it("marks products from vendors still being verified in the marketplace", () => {
  render(<MemoryRouter><ProductCard product={{ ...base, vendor_verified: false }} detailsPath="/products/p1" /></MemoryRouter>);
  expect(screen.getByText("Vendor verification in progress")).toBeTruthy();
  cleanup();
  render(<MemoryRouter><ProductCard product={{ ...base, vendor_verified: true }} detailsPath="/products/p1" /></MemoryRouter>);
  expect(screen.queryByText("Vendor verification in progress")).toBeNull();
});
