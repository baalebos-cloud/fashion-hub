import { Textarea } from "@/components/ui/textarea";

export function DesignRequirementForm({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return (
    <div>
      <label htmlFor="requirements" className="mb-1.5 block text-sm font-medium text-ink">
        Anything specific you'd like the tailor to know?
      </label>
      <Textarea
        id="requirements"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Fabric preferences, color, occasion, deadline…"
        rows={4}
      />
    </div>
  );
}
