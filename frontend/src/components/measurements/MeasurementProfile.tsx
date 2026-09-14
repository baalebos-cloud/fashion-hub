import { MeasurementTable } from "./MeasurementTable";
import type { MeasurementProfile as MeasurementProfileType } from "@/types/measurement";

export function MeasurementProfile({ profile }: { profile: MeasurementProfileType }) {
  return (
    <div className="rounded-card border border-line p-4">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="font-medium text-ink">{profile.label}</h3>
        {profile.garment_type && <span className="text-xs text-ink-soft">{profile.garment_type}</span>}
      </div>
      <MeasurementTable fields={profile.fields ?? []} />
    </div>
  );
}
