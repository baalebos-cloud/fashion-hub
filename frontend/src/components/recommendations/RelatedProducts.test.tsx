import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { RelatedProducts } from "@/components/recommendations/RelatedProducts";
import type { RelatedProduct } from "@/api/recommendations.api";
import { viewSource } from "@/lib/tracking/interactions";

afterEach(cleanup);

const item = (over: Partial<RelatedProduct>): RelatedProduct => ({
  product_id: "p1", name: "Lace", vendor_name: "Lagos Fabrics", primary_image_url: null, price_ngn: 5000,
  currency: "NGN", unit_of_measure: "yard", reason: "viewed_together", learned: true, ...over,
});

const renderRow = (load: () => Promise<RelatedProduct[]>) => render(
  <MemoryRouter>
    <RelatedProducts title="You might also like" loadKey="k" source="similar_items" load={load}
      detailsPathFor={(id) => `/products/${id}`} />
  </MemoryRouter>);

describe("related products row", () => {
  it("labels each suggestion with why it's shown and links with its source", async () => {
    renderRow(() => Promise.resolve([
      item({}), item({ product_id: "p2", name: "Thread", reason: "similar", learned: false }),
    ]));
    expect(await screen.findByRole("region", { name: "You might also like" })).toBeTruthy();
    expect(screen.getByText("Shoppers also viewed")).toBeTruthy();
    expect(screen.getByText("Similar item")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Thread/ }).getAttribute("href")).toBe("/products/p2?from=similar_items");
  });

  it("stays hidden when there is nothing to suggest or loading fails", async () => {
    const empty = vi.fn().mockResolvedValue([]);
    const { container } = renderRow(empty);
    await waitFor(() => expect(empty).toHaveBeenCalled());
    expect(container.innerHTML).toBe("");
    cleanup();
    const failing = vi.fn().mockRejectedValue(new Error("offline"));
    const second = renderRow(failing);
    await waitFor(() => expect(failing).toHaveBeenCalled());
    expect(second.container.innerHTML).toBe("");
  });
});

describe("view source", () => {
  it("accepts a known-shape section name and ignores anything else", () => {
    expect(viewSource("similar_items", "product_page")).toBe("similar_items");
    expect(viewSource("<script>", "product_page")).toBe("product_page");
    expect(viewSource(null, "product_page")).toBe("product_page");
  });
});
