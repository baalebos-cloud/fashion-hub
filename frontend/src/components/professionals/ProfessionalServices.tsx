import { useDesigns } from "@/hooks/use-designs";
import { DesignGallery } from "@/components/designs/DesignGallery";

export function ProfessionalServices({ professionalId, onSelectDesign }: { professionalId: string; onSelectDesign?: (designId: string) => void }) {
  const { designs, isLoading } = useDesigns(professionalId);

  return (
    <div>
      <h2 className="mb-3 text-sm font-medium text-ink-soft">Services</h2>
      <DesignGallery designs={designs} isLoading={isLoading} onSelect={onSelectDesign} />
    </div>
  );
}
