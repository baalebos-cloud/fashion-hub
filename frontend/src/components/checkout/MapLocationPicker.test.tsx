import { beforeEach, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
  Button: ({ children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) => <button {...props}>{children}</button>,
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
  mocks.click?.({ latLng: { lat: () => 7.12345, lng: () => 4.65432 } });
  await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Address lookup is unavailable"));
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
  mocks.click?.({ latLng: { lat: () => 8, lng: () => 5 } });
  await waitFor(() => expect(screen.getByLabelText("Shop address")).toHaveValue("Pinned location (8.00000, 5.00000)"));
  fireEvent.click(screen.getByText("Save shop location"));
  expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ latitude: 8, longitude: 5 }));
});
