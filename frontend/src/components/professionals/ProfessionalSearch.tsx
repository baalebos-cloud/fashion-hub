import { Input } from "@/components/ui/input";

export function ProfessionalSearch({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return (
    <Input
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder="Search by name, specialty, or style…"
      aria-label="Search professionals"
    />
  );
}
