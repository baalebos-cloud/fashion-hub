import { describe, expect, it } from "vitest";
import { mapsDestination } from "./DispatchTripCard";

const point = { address: "Test Street", latitude: 7.64037, longitude: 5.22102,
  contact_name: "Test Customer", can_call: true };

describe("rider navigation", () => {
  it("opens the actual selected point instead of a guessed address", () => {
    expect(mapsDestination(point)).toContain("destination=7.64037,5.22102");
  });
  it("does not create directions from missing coordinates", () => {
    expect(mapsDestination({ ...point, latitude: null })).toBeNull();
  });
});
