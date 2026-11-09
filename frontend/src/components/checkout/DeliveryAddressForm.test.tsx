import { beforeEach, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { DeliveryAddressForm } from "./DeliveryAddressForm";
import { addressesApi } from "@/api/addresses.api";

vi.mock("@/api/addresses.api", () => ({ addressesApi: { create: vi.fn() } }));
vi.mock("./MapLocationPicker", () => ({
  MapLocationPicker: ({ onChange }: { onChange: (location: object) => void }) => (
    <>
      <button type="button" onClick={() => onChange({
        latitude: 7.64037, longitude: 5.22104,
        formatted_address: "Ado-Iworoko Road, Ado Ekiti, Ekiti, Nigeria",
        city: "Ado Ekiti", state_region: "Ekiti", country: "Nigeria",
      })}>Select test pin</button>
      {/* What "Use my current location" brings back for a point in Lekki. */}
      <button type="button" onClick={() => onChange({
        latitude: 6.4474, longitude: 3.4728,
        formatted_address: "14 Admiralty Way, Lekki Phase 1, Lekki 106104, Lagos, Nigeria",
        street: "14 Admiralty Way", area: "Lekki Phase 1", city: "Lekki", lga: "Eti-Osa",
        state_region: "Lagos State", country: "Nigeria", landmark: "Lekki Central Mosque", nearest_bus_stop: "Jakande Bus Stop",
      })}>Use my current location (test)</button>
    </>
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

it("sends the LGA, landmark, bus stop and instructions riders navigate by", async () => {
  vi.mocked(addressesApi.create).mockResolvedValue({
    id: "a2", is_default: false, label: "Home", recipient_name: "Test Customer", recipient_phone: "08031234567",
    formatted_address: "x", city: "Ado Ekiti", state_region: "Ekiti", country: "NG", latitude: 7.64037, longitude: 5.22104,
  });
  render(<DeliveryAddressForm onSaved={vi.fn()} />);
  fireEvent.click(screen.getByText("Select test pin"));
  fillContact();
  // The map said "Ado Ekiti", which is an Ekiti LGA, so it is already chosen; pick another to prove it's editable.
  expect((screen.getByLabelText("Local government area (LGA)") as HTMLSelectElement).value).toBe("Ado Ekiti");
  fireEvent.change(screen.getByLabelText("Local government area (LGA)"), { target: { value: "Ikere" } });
  fireEvent.change(screen.getByLabelText("Landmark"), { target: { value: "Behind Fajuyi Park" } });
  fireEvent.change(screen.getByLabelText("Nearest bus stop"), { target: { value: "Okeyinmi bus stop" } });
  fireEvent.click(screen.getByText("Save delivery address"));
  await waitFor(() => expect(addressesApi.create).toHaveBeenCalledWith(expect.objectContaining({
    lga: "Ikere", landmark: "Behind Fajuyi Park", nearest_bus_stop: "Okeyinmi bus stop",
  })));
});

it("lists every state and only the chosen state's LGAs", () => {
  render(<DeliveryAddressForm onSaved={vi.fn()} />);
  const state = screen.getByLabelText("State") as HTMLSelectElement;
  expect(state.options.length - 1).toBe(37); // 36 states + FCT, plus the "Choose" prompt
  const lga = screen.getByLabelText("Local government area (LGA)") as HTMLSelectElement;
  expect(lga.disabled).toBe(true);
  fireEvent.change(state, { target: { value: "Lagos" } });
  expect(lga.disabled).toBe(false);
  expect(lga.options.length - 1).toBe(20);
  expect([...lga.options].map((o) => o.value)).toContain("Eti-Osa");
  fireEvent.change(lga, { target: { value: "Eti-Osa" } });
  fireEvent.change(state, { target: { value: "Kano" } });
  expect(lga.value).toBe(""); // Eti-Osa isn't in Kano
  expect(lga.options.length - 1).toBe(44);
});

it("won't save a Nigerian address without its LGA", async () => {
  vi.mocked(addressesApi.create).mockResolvedValue({} as never);
  render(<DeliveryAddressForm onSaved={vi.fn()} />);
  fireEvent.click(screen.getByText("Select test pin"));
  fillContact();
  fireEvent.change(screen.getByLabelText("Local government area (LGA)"), { target: { value: "" } });
  fireEvent.change(screen.getByLabelText("State"), { target: { value: "Oyo" } });
  const lga = screen.getByLabelText("Local government area (LGA)") as HTMLSelectElement;
  expect(lga.validity.valueMissing).toBe(true); // the browser asks for it before submitting
  fireEvent.submit(lga.form!); // and the form checks it too
  expect(await screen.findByText("Choose your local government area (LGA).")).toBeTruthy();
  expect(addressesApi.create).not.toHaveBeenCalled();
});

it("shows a saved address's state and LGA even when written differently", () => {
  render(<DeliveryAddressForm onSaved={vi.fn()} initial={{
    id: "a1", is_default: true, label: "Home", recipient_name: "Amaka", recipient_phone: "08031234567",
    formatted_address: "14 Admiralty Way", city: "Lekki", state_region: "Lagos State", country: "NG",
    lga: "eti osa", latitude: 6.4474, longitude: 3.4728,
  }} />);
  expect((screen.getByLabelText("State") as HTMLSelectElement).value).toBe("Lagos");
  expect((screen.getByLabelText("Local government area (LGA)") as HTMLSelectElement).value).toBe("Eti-Osa");
});

it("fills street, city, state, LGA, landmark and bus stop from the current location", () => {
  render(<DeliveryAddressForm onSaved={vi.fn()} />);
  fireEvent.click(screen.getByText("Use my current location (test)"));
  const value = (label: string) => (screen.getByLabelText(label) as HTMLInputElement | HTMLSelectElement).value;
  expect(value("Street address")).toBe("14 Admiralty Way, Lekki Phase 1");
  expect(value("City or town")).toBe("Lekki");
  expect(value("State")).toBe("Lagos");
  expect(value("Local government area (LGA)")).toBe("Eti-Osa");
  expect(value("Landmark")).toBe("Lekki Central Mosque");
  expect(value("Nearest bus stop")).toBe("Jakande Bus Stop");
  expect(value("Recipient name")).toBe(""); // the person's own details are never guessed
});

it("never overwrites a landmark or bus stop the person typed", () => {
  render(<DeliveryAddressForm onSaved={vi.fn()} />);
  fireEvent.change(screen.getByLabelText("Landmark"), { target: { value: "Blue gate opposite the pharmacy" } });
  fireEvent.click(screen.getByText("Use my current location (test)"));
  expect((screen.getByLabelText("Landmark") as HTMLInputElement).value).toBe("Blue gate opposite the pharmacy");
  expect((screen.getByLabelText("Nearest bus stop") as HTMLInputElement).value).toBe("Jakande Bus Stop");
});
