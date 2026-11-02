import { beforeEach, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { DeliveryAddressForm } from "./DeliveryAddressForm";
import { addressesApi } from "@/api/addresses.api";

vi.mock("@/api/addresses.api", () => ({ addressesApi: { create: vi.fn() } }));
vi.mock("./MapLocationPicker", () => ({
  MapLocationPicker: ({ onChange }: { onChange: (location: object) => void }) => (
    <button type="button" onClick={() => onChange({
      latitude: 7.64037, longitude: 5.22104,
      formatted_address: "Ado-Iworoko Road, Ado Ekiti, Ekiti, Nigeria",
      city: "Ado Ekiti", state_region: "Ekiti", country: "Nigeria",
    })}>Select test pin</button>
  ),
}));
beforeEach(() => vi.clearAllMocks());

function fillContact() {
  fireEvent.change(screen.getByLabelText("Recipient name"), { target: { value: "Test Customer" } });
  fireEvent.change(screen.getByLabelText("Recipient phone"), { target: { value: "08031234567" } });
}

it("blocks submitting without a selected map pin", () => {
  render(<DeliveryAddressForm onSaved={vi.fn()} />);
  expect((screen.getByText("Save delivery address") as HTMLButtonElement).disabled).toBe(true);
  expect(addressesApi.create).not.toHaveBeenCalled();
});

it("requires recipient details and persists address with pin coordinates", async () => {
  vi.mocked(addressesApi.create).mockResolvedValue({
    id: "test-id", is_default: false, label: "Home", recipient_name: "Test Customer", recipient_phone: "08031234567",
    formatted_address: "Ado-Iworoko Road, Ado Ekiti, Ekiti, Nigeria",
    city: "Ado Ekiti", state_region: "Ekiti", country: "NG", latitude: 7.64037, longitude: 5.22104,
  });
  const saved = vi.fn();
  render(<DeliveryAddressForm onSaved={saved} />);
  fireEvent.click(screen.getByText("Select test pin"));
  fireEvent.click(screen.getByText("Save delivery address"));
  expect(addressesApi.create).not.toHaveBeenCalled();
  fillContact();
  fireEvent.click(screen.getByText("Save delivery address"));
  await waitFor(() => expect(addressesApi.create).toHaveBeenCalledWith(expect.objectContaining({
    latitude: 7.64037, longitude: 5.22104,
    city: "Ado Ekiti", state_region: "Ekiti", country: "NG",
    recipient_name: "Test Customer", recipient_phone: "08031234567",
  })));
  await waitFor(() => expect(saved).toHaveBeenCalled());
});
