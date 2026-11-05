import { describe, expect, it } from "vitest";
import { contactLinks, mapsDestination } from "./DispatchTripCard";

const point = { address: "Test Street", latitude: 7.64037, longitude: 5.22102,
  contact_name: "Test Customer", contact_phone: "08031234567" };

describe("rider navigation", () => {
  it("opens the actual selected point instead of a guessed address", () => {
    expect(mapsDestination(point)).toContain("destination=7.64037,5.22102");
  });
  it("does not create directions from missing coordinates", () => {
    expect(mapsDestination({ ...point, latitude: null })).toBeNull();
  });
  it("normalizes Nigerian local numbers for WhatsApp and calls", () => {
    expect(contactLinks("08031234567")).toEqual({
      call: "tel:+2348031234567", whatsapp: "https://wa.me/2348031234567",
    });
    expect(contactLinks("not a phone")).toBeNull();
  });
});
