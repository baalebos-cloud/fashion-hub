import { useState } from "react";
import { useAuth } from "@/hooks/use-auth";
import { useDesigns } from "@/hooks/use-designs";
import { DesignGallery } from "@/components/designs/DesignGallery";
import { DesignUpload } from "@/components/designs/DesignUpload";
import { Button } from "@/components/ui/button";
import type { Design } from "@/types/design";

export default function Designs() {
  const { user } = useAuth();
  const { designs: fetchedDesigns, isLoading } = useDesigns(user?.id);
  const [localDesigns, setLocalDesigns] = useState<Design[]>([]);
  const [isAdding, setIsAdding] = useState(false);

  const designs = [...fetchedDesigns, ...localDesigns];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-xl text-ink">Designs</h1>
        {!isAdding && <Button onClick={() => setIsAdding(true)}>Add design</Button>}
      </div>
      {isAdding && (
        <DesignUpload
          onCreated={(design) => {
            setLocalDesigns((prev) => [...prev, design]);
            setIsAdding(false);
          }}
        />
      )}
      <DesignGallery designs={designs} isLoading={isLoading} />
    </div>
  );
}
