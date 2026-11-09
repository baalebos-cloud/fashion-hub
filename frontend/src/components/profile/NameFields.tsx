import { Input } from "@/components/ui/input";
import type { NameErrors, NameParts } from "@/lib/names";

/** First name, middle name (optional) and surname, used on sign-up and on every profile. */
export function NameFields({ value, onChange, errors = {}, idPrefix = "name" }: {
  value: NameParts;
  onChange: (next: NameParts) => void;
  errors?: NameErrors;
  idPrefix?: string;
}) {
  const field = (key: keyof NameParts, label: string, autoComplete: string, optional = false) => {
    const id = `${idPrefix}-${key}`;
    return (
      <div className="flex flex-col gap-1.5">
        <label htmlFor={id} className="text-sm font-medium text-ink">
          {label} {optional && <span className="font-normal text-ink-soft">(optional)</span>}
        </label>
        <Input id={id} autoComplete={autoComplete} value={value[key]} maxLength={80}
          onChange={(e) => onChange({ ...value, [key]: e.target.value })} error={errors[key]}
          aria-describedby={errors[key] ? `${id}-error` : undefined} />
        {errors[key] && <p id={`${id}-error`} className="text-xs text-thread">{errors[key]}</p>}
      </div>
    );
  };
  return (
    <fieldset className="flex flex-col gap-3">
      <legend className="sr-only">Your name</legend>
      {field("first", "First name", "given-name")}
      {field("middle", "Middle name", "additional-name", true)}
      {field("last", "Surname", "family-name")}
      <p className="text-xs text-ink-soft">Write your names exactly as they appear on your NIN slip, so verification goes smoothly.</p>
    </fieldset>
  );
}
