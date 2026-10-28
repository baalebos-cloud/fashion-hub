import { z } from "zod";

export const measurementUnitSchema = z.enum(["cm", "in"]);
export const measurementNames = [
  "chest", "waist", "hip", "inseam", "shoulder_width", "sleeve_length", "neck",
] as const;
const dimension = z.number().finite().positive().max(999.99);
const dimensions = z.object({
  chest: dimension.optional(),
  waist: dimension.optional(),
  hip: dimension.optional(),
  inseam: dimension.optional(),
  shoulder_width: dimension.optional(),
  sleeve_length: dimension.optional(),
  neck: dimension.optional(),
}).strict();

export const measurementSchema = z.object({
  unit: measurementUnitSchema,
  label: z.string().trim().min(1).max(128),
  values: dimensions,
}).superRefine((input, ctx) => {
  if (Object.values(input.values).every((value) => value === undefined)) {
    ctx.addIssue({ code: "custom", path: ["values"], message: "Enter at least one measurement." });
  }
  for (const [name, value] of Object.entries(input.values)) {
    if (value !== undefined && (input.unit === "in" ? value > 393.7 : value > 999.99)) {
      ctx.addIssue({ code: "custom", path: ["values", name], message: "Measurement outside supported range." });
    }
  }
});

export type MeasurementInput = z.infer<typeof measurementSchema>;

export function measurementFieldsInCentimetres(input: MeasurementInput) {
  const parsed = measurementSchema.parse(input);
  return Object.entries(parsed.values).filter((pair): pair is [string, number] => pair[1] !== undefined)
    .map(([field_name, value]) => ({
      field_name,
      value: Math.round((parsed.unit === "in" ? value * 2.54 : value) * 100) / 100,
      unit: "cm",
    }));
}
