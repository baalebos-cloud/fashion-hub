import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import AddProduct from "@/pages/vendor/AddProduct";
import { ProductVariantSelector } from "@/components/marketplace/ProductVariantSelector";
import { productsApi } from "@/api/products.api";

vi.mock("@/api/products.api", () => ({ productsApi: { create: vi.fn() } }));
vi.mock("@/lib/storage/file-storage", () => ({ uploadFile: vi.fn().mockResolvedValue({ url: "https://cdn.example/lace.jpg" }) }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });

async function fillBasics() {
  fireEvent.change(screen.getByLabelText("Product name"), { target: { value: "French lace" } });
  fireEvent.change(screen.getByLabelText("Material photos (1–5)"), { target: { files: [new File(["x"], "lace.jpg", { type: "image/jpeg" })] } });
  await screen.findByAltText("Material photo 1");
}

describe("add product in colours", () => {
  it("sends one price and stock per colour, with the lowest price as the base", async () => {
    vi.mocked(productsApi.create).mockResolvedValue({ id: "p1" } as never);
    render(<MemoryRouter><AddProduct /></MemoryRouter>);
    await fillBasics();
    fireEvent.click(screen.getByLabelText("This comes in more than one colour"));
    expect(screen.queryByLabelText("Price per yard (₦)", { selector: "#new-product-price" })).toBeNull();
    const rows = within(screen.getByRole("list", { name: "Colours" })).getAllByRole("listitem");
    const fill = (row: HTMLElement, name: string, price: string, stock: string) => {
      fireEvent.change(within(row).getByLabelText(/Colour \d/), { target: { value: name } });
      fireEvent.change(within(row).getByLabelText(/Price per yard/), { target: { value: price } });
      fireEvent.change(within(row).getByLabelText(/In stock/), { target: { value: stock } });
    };
    fill(rows[0], "Royal blue", "9500", "30");
    fill(rows[1], "Gold", "10200", "12");
    const preview = screen.getByRole("complementary", { name: "How tailors will see it" });
    expect(within(preview).getByText("from ₦9,500 / yard")).toBeTruthy();
    expect(within(preview).getByText("2 colours")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Add product" }));
    await waitFor(() => expect(productsApi.create).toHaveBeenCalledWith({
      name: "French lace", description: "", base_price: 9500, initial_stock: 0, image_urls: ["https://cdn.example/lace.jpg"],
      unit_of_measure: "yard", colours: [{ name: "Royal blue", price: 9500, stock: 30 }, { name: "Gold", price: 10200, stock: 12 }],
    }));
  });

  it("blocks duplicate or incomplete colours", async () => {
    render(<MemoryRouter><AddProduct /></MemoryRouter>);
    await fillBasics();
    fireEvent.click(screen.getByLabelText("This comes in more than one colour"));
    expect(screen.getByText(/fill in a name, price and stock for every colour/)).toBeTruthy();
    const rows = within(screen.getByRole("list", { name: "Colours" })).getAllByRole("listitem");
    for (const row of rows) {
      fireEvent.change(within(row).getByLabelText(/Colour \d/), { target: { value: "Gold" } });
      fireEvent.change(within(row).getByLabelText(/Price per yard/), { target: { value: "100" } });
    }
    expect(screen.getAllByText(/different name/).length).toBeGreaterThan(0);
    expect((screen.getByRole("button", { name: "Add product" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Remove colour 2" }));
    expect((screen.getByRole("button", { name: "Add product" }) as HTMLButtonElement).disabled).toBe(false);
    expect((screen.getByRole("button", { name: "Remove colour 1" }) as HTMLButtonElement).disabled).toBe(true);
  });
});

describe("colour picker for buyers", () => {
  it("labels colour versions as Colour", () => {
    render(<ProductVariantSelector selectedId="a" onSelect={() => {}} variants={[
      { id: "a", product_id: "p", sku: "A", price: 1, attributes: { color: "Royal blue" } },
      { id: "b", product_id: "p", sku: "B", price: 2, attributes: { color: "Gold" } },
    ]} />);
    expect(screen.getByText("Colour")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Gold" }).getAttribute("aria-pressed")).toBe("false");
  });
});

describe("single colour and cart lines", () => {
  it("names the colour even when there's only one", () => {
    render(<ProductVariantSelector selectedId="a" onSelect={() => {}} variants={[
      { id: "a", product_id: "p", sku: "A", price: 1, attributes: { color: "Navy" } }]} />);
    expect(screen.getByText("Navy")).toBeTruthy();
    cleanup();
    const { container } = render(<ProductVariantSelector selectedId="a" onSelect={() => {}} variants={[
      { id: "a", product_id: "p", sku: "A", price: 1, attributes: null }]} />);
    expect(container.textContent).toBe("");
  });

  it("shows the colour on each cart line", async () => {
    const { CartItem } = await import("@/components/cart/CartItem");
    render(<CartItem item={{ id: "c1", product_variant_id: "v1", product_id: "p", vendor_id: "v", vendor_name: "Lagos Fabrics",
      product_name: "French lace", colour: "Gold", sku: "FH-1", quantity: 2, unit_price_snapshot: 9500, currency: "NGN", is_available: true } as never} />);
    expect(screen.getByText(/· Gold/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Remove French lace (Gold)" })).toBeTruthy();
  });
});

