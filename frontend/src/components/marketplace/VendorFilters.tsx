import { Switch } from "@/components/ui/switch";

export interface VendorFiltersValue {
  verifiedOnly: boolean;
}

export function VendorFilters({ value, onChange }: { value: VendorFiltersValue; onChange: (v: VendorFiltersValue) => void }) {
  return (
    <label className="flex items-center gap-2 text-sm text-ink">
      <Switch checked={value.verifiedOnly} onChange={(verifiedOnly) => onChange({ ...value, verifiedOnly })} label="Verified vendors only" />
      Verified vendors only
    </label>
  );
}
