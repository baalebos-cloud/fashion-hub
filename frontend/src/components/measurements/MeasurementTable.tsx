import type { MeasurementField } from "@/types/measurement";

export function MeasurementTable({ fields }: { fields: MeasurementField[] }) {
  return (
    <table className="w-full text-sm">
      <tbody>
        {fields.map((field) => (
          <tr key={field.field_name} className="border-b border-line last:border-0">
            <td className="py-2 capitalize text-ink-soft">{field.field_name.replace(/_/g, " ")}</td>
            <td className="py-2 text-right font-medium text-ink">{field.value} {field.unit}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
