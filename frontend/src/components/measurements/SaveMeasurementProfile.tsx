import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export function SaveMeasurementProfile({ onSave, isSaving }: { onSave: (label: string) => Promise<void>; isSaving?: boolean }) {
  const [label, setLabel] = useState("");

  return (
    <div className="flex gap-2">
      <Input placeholder="e.g. My measurements" value={label} onChange={(e) => setLabel(e.target.value)} />
      <Button onClick={() => onSave(label)} isLoading={isSaving} disabled={!label.trim()}>Save</Button>
    </div>
  );
}
