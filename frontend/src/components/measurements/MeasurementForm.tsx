import { MeasurementWorkflow } from "./MeasurementWorkflow";

export interface MeasurementFormProps {
  onSaved?: () => void;
  requiredFields?: string[];
}

/** Stable public component API; actual form uses validated two-step workflow. */
export function MeasurementForm(props: MeasurementFormProps) {
  return <MeasurementWorkflow {...props} />;
}
