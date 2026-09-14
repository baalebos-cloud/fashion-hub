import { useState } from "react";
import { useMeasurements } from "@/hooks/use-measurements";
import { MeasurementForm } from "@/components/measurements/MeasurementForm";
import { MeasurementProfile } from "@/components/measurements/MeasurementProfile";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";

export default function Measurements() {
  const { profiles, isLoading } = useMeasurements();
  const [isAdding, setIsAdding] = useState(false);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-xl text-ink">Measurements</h1>
        {!isAdding && <Button onClick={() => setIsAdding(true)}>Add profile</Button>}
      </div>

      {isAdding && <MeasurementForm onSaved={() => setIsAdding(false)} />}

      {!isLoading && profiles.length === 0 && !isAdding && (
        <EmptyState title="No measurement profiles yet" description="Add one to make ordering faster next time." />
      )}

      <div className="flex flex-col gap-4">
        {profiles.map((profile) => (
          <MeasurementProfile key={profile.id} profile={profile} />
        ))}
      </div>
    </div>
  );
}
