import { describe, expect, it } from "vitest";
import { validateMeasurementFields } from "@/lib/measurements/validation";

describe("measurement validation", () => {
  it("builds typed fields from positive measurements", () => {
    const result = validateMeasurementFields(["chest", "waist"], { chest: "85.25", waist: "70" }, "cm");
    expect(result.errors).toEqual({});
    expect(result.fields).toEqual([
      { field_name: "chest", value: 85.25, unit: "cm" },
      { field_name: "waist", value: 70, unit: "cm" },
    ]);
  });

  it.each(["", "0", "-2", "NaN", "Infinity", "1e10", "1.222", "1000"])(
    "rejects invalid cm measurement %s", (value) => {
      const result = validateMeasurementFields(["chest"], { chest: value }, "cm");
      expect(result.errors.chest).toBeTruthy();
      expect(result.fields).toHaveLength(0);
    },
  );

  it("rejects duplicate fields and missing required fields", () => {
    const result = validateMeasurementFields(["chest", "chest", "waist"], { chest: "80" }, "cm");
    expect(result.errors.chest).toBeTruthy();
    expect(result.errors.waist).toBeTruthy();
  });

  it("allows inches within realistic bounds", () => {
    const result = validateMeasurementFields(["chest"], { chest: "34.5" }, "in");
    expect(result.errors).toEqual({});
    expect(result.fields[0].unit).toBe("in");
  });
});
