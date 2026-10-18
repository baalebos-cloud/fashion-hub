import { Checkbox } from "@/components/ui/checkbox";

/** Buyer acknowledgement before starting payment; this is not a legal signature. */
export function PaymentConsent({ checked, onChange }: { checked: boolean; onChange: (checked: boolean) => void }) {
  return (
    <label className="flex items-start gap-2 text-sm text-ink-soft">
      <Checkbox checked={checked} onChange={(e) => onChange(e.target.checked)} className="mt-0.5" />
      I authorize this payment for the order total shown above.
    </label>
  );
}
