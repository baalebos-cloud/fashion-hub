import { useState } from "react";
import { useAuth } from "@/hooks/use-auth";
import { useDesigns } from "@/hooks/use-designs";
import { DesignCard } from "@/components/designs/DesignCard";
import { DesignUpload } from "@/components/designs/DesignUpload";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import type { Design } from "@/types/design";

export default function Services() {
  const { user } = useAuth();
  const { designs: fetchedDesigns } = useDesigns(user?.id);
  const [localDesigns, setLocalDesigns] = useState<Design[]>([]);
  const [isAdding, setIsAdding] = useState(false);

  const services = [...fetchedDesigns, ...localDesigns];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-xl text-ink">Services & pricing</h1>
        {!isAdding && <Button onClick={() => setIsAdding(true)}>Add service</Button>}
      </div>
      {isAdding && <DesignUpload onCreated={(d) => { setLocalDesigns((prev) => [...prev, d]); setIsAdding(false); }} />}
      {services.length === 0 ? (
        <EmptyState title="No services listed yet" />
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {services.map((service) => <DesignCard key={service.id} design={service} />)}
        </div>
      )}
    </div>
  );
}
