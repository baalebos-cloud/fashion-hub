import type { MeasurementField } from "@/types/measurement";

export type MeasurementUnit = "cm" | "in";

export function validateMeasurementFields(
  names: readonly string[],
  values: Record<string, string>,
  unit: MeasurementUnit,
): { fields: MeasurementField[]; errors: Record<string, string> } {
  const errors: Record<string, string> = {};
  const fields: MeasurementField[] = [];
  const seen = new Set<string>();
  for (const name of names) {
    if (!name || seen.has(name)) {
      errors[name] = "Duplicate or invalid measurement name.";
      continue;
    }
    seen.add(name);
    const raw = values[name]?.trim() ?? "";
    const value = Number(raw);
    if (!raw || !Number.isFinite(value) || value <= 0 || value > (unit === "cm" ? 999.99 : 393.7)) {
      errors[name] = "Enter a positive, realistic measurement.";
      continue;
    }
    if (!/^\d+(?:\.\d{1,2})?$/.test(raw)) {
      errors[name] = "Use a number with at most two decimal places.";
      continue;
    }
    fields.push({ field_name: name, value, unit });
  }
  if (unit !== "cm" && unit !== "in") {
    errors.unit = "Select a valid unit.";
  }
  return { fields, errors };
}
