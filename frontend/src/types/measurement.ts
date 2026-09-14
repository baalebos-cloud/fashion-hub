export interface MeasurementField {
  field_name: string;
  value: number;
  unit: string;
}

export interface MeasurementProfile {
  id: string;
  label: string;
  garment_type?: string | null;
  fields?: MeasurementField[];
}
