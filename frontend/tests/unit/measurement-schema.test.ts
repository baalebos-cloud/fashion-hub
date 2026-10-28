import { describe, expect, it } from "vitest";
import { measurementSchema, measurementFieldsInCentimetres } from "@/schemas/measurement";

describe("measurementSchema", () => {
  it("validates measurements and normalizes inches to centimetres", () => {
    const value = measurementSchema.parse({ unit: "in", label: "Wedding suit", values: { chest: 40, waist: 32 } });
    expect(measurementFieldsInCentimetres(value)).toEqual([
      { field_name: "chest", value: 101.6, unit: "cm" },
      { field_name: "waist", value: 81.28, unit: "cm" },
    ]);
  });
  it("rejects empty measurements", () => {
    expect(measurementSchema.safeParse({ label: "test", unit: "cm", values: {} }).success).toBe(false);
  });
  it.each([0, -1, 1000, Number.POSITIVE_INFINITY, Number.NaN])(
    "rejects invalid chest value %s", (chest) => {
      expect(measurementSchema.safeParse({ label: "test", unit: "cm", values: { chest } }).success).toBe(false);
    },
  );
  it("rejects overlong labels and unknown dimensions", () => {
    expect(measurementSchema.safeParse({ label: "x".repeat(129), unit: "cm", values: { chest: 80 } }).success).toBe(false);
    expect(measurementSchema.safeParse({ label: "x", unit: "cm", values: { chest: 80, secret: 20 } }).success).toBe(false);
  });
  it("rejects impossible inch values", () => {
    expect(measurementSchema.safeParse({ label: "x", unit: "in", values: { chest: 400 } }).success).toBe(false);
  });
});
