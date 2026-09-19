import { Checkbox } from "@/components/ui/checkbox";

/** Standard measurement field vocabulary -- mirrors the field names used
 * throughout components/measurements/ (MeasurementForm.FIELD_NAMES) so a
 * tailor's selections here line up exactly with what a customer's
 * measurement profile actually contains. */
export const STANDARD_MEASUREMENT_FIELDS = ["chest", "waist", "hip", "sleeve_length", "inseam"];

export interface MeasurementFieldSelectorProps {
  selected: string[];
  onChange: (fields: string[]) => void;
}

/**
 * Lets a tailor/designer specify exactly which measurements THIS design
 * needs (see backend/docs/measurement-requirements.md). Leaving every box
 * unchecked means "use the customer's full default profile as-is" --
 * this is the explicit, visible version of that default, not a hidden
 * fallback.
 */
export function MeasurementFieldSelector({ selected, onChange }: MeasurementFieldSelectorProps) {
  function toggle(field: string) {
    onChange(selected.includes(field) ? selected.filter((f) => f !== field) : [...selected, field]);
  }

  return (
    <div>
      <div className="mb-1.5 text-sm font-medium text-ink">Required measurements</div>
      <p className="mb-2 text-xs text-ink-soft">
        Select the fields you need for this design. Leave all unchecked to use the customer's full measurement profile.
      </p>
      <div className="flex flex-wrap gap-3">
        {STANDARD_MEASUREMENT_FIELDS.map((field) => (
          <label key={field} className="flex items-center gap-1.5 text-sm capitalize text-ink">
            <Checkbox checked={selected.includes(field)} onChange={() => toggle(field)} />
            {field.replace(/_/g, " ")}
          </label>
        ))}
      </div>
    </div>
  );
}
