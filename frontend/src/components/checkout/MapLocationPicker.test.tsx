import type { ButtonHTMLAttributes } from "react";
import { beforeEach, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MapLocationPicker } from "./MapLocationPicker";

const mocks = vi.hoisted(() => ({
  reverse: vi.fn(),
  locate: vi.fn(),
  click: null as null | ((event: { latLng: { lat: () => number; lng: () => number } }) => void),
}));
vi.mock("@/lib/maps/geocoding", () => ({ reverseGeocode: mocks.reverse }));
vi.mock("@/hooks/use-map", () => ({ useMap: () => ({ isReady: true, error: null }) }));
vi.mock("@/hooks/use-geolocation", () => ({
  useGeolocation: () => ({ locate: mocks.locate, isLocating: false, error: null, errorCode: null }),
}));
vi.mock("@/config/map.config", () => ({
  mapConfig: { provider: "google_maps", defaultCenter: { lat: 6.5, lng: 3.3 }, defaultZoom: 12 },
}));
vi.mock("@/components/ui/button", () => ({
  Button: ({ children, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) => <button {...props}>{children}</button>,
}));

beforeEach(() => {
  mocks.reverse.mockReset();
  mocks.locate.mockReset();
  mocks.click = null;
  Object.defineProperty(window, "google", {
    configurable: true,
    value: { maps: {
      Map: class {
        addListener(_event: string, handler: typeof mocks.click) { mocks.click = handler; }
        panTo() {}
        setZoom() {}
      },
      Marker: class { setPosition() {} setMap() {} },
    } },
  });
});

it("saves valid coordinates and editable address even when reverse geocoding fails", async () => {
  mocks.reverse.mockRejectedValue(new Error("REQUEST_DENIED"));
  const onSelect = vi.fn();
  render(<MapLocationPicker onSelect={onSelect} />);
  act(() => { mocks.click?.({ latLng: { lat: () => 7.12345, lng: () => 4.65432 } }); });
  await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("Address could not be verified by the available map providers"));
  fireEvent.change(screen.getByLabelText("Shop address"), { target: { value: "My shop, Ekiti" } });
  fireEvent.click(screen.getByText("Save shop location"));
  expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({
    latitude: 7.12345, longitude: 4.65432, formatted_address: "My shop, Ekiti",
  }));
});

it("keeps pin coordinates available when lookup returns no street address", async () => {
  mocks.reverse.mockResolvedValue({ formatted_address: "" });
  const onSelect = vi.fn();
  render(<MapLocationPicker onSelect={onSelect} />);
  act(() => { mocks.click?.({ latLng: { lat: () => 8, lng: () => 5 } }); });
  await waitFor(() => expect((screen.getByLabelText("Shop address") as HTMLInputElement).value).toBe("Pinned location (8.00000, 5.00000)"));
  fireEvent.click(screen.getByText("Save shop location"));
  expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ latitude: 8, longitude: 5 }));
});

it("preserves resolved street and locality fields for saving", async () => {
  mocks.reverse.mockResolvedValue({
    formatted_address: "Ado-Iworoko Road, Ado Ekiti, Nigeria",
    city: "Ado Ekiti", state_region: "Ekiti", country: "Nigeria",
  });
  const onSelect = vi.fn();
  render(<MapLocationPicker onSelect={onSelect} />);
  act(() => { mocks.click?.({ latLng: { lat: () => 7.64037, lng: () => 5.22104 } }); });
  await waitFor(() => expect((screen.getByLabelText("Shop address") as HTMLInputElement).value)
    .toBe("Ado-Iworoko Road, Ado Ekiti, Nigeria"));
  fireEvent.click(screen.getByText("Save shop location"));
  expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({
    latitude: 7.64037, longitude: 5.22104,
    city: "Ado Ekiti", state_region: "Ekiti", country: "Nigeria",
  }));
});
