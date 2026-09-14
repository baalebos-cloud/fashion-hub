import { useEffect, useState } from "react";
import { useGeolocation } from "@/hooks/use-geolocation";
import { professionalsApi } from "@/api/professionals.api";
import { ProfessionalGrid } from "@/components/professionals/ProfessionalGrid";
import { Button } from "@/components/ui/button";
import type { Professional } from "@/types/professional";

export function NearbyProfessionals({ detailsPathFor }: { detailsPathFor: (id: string) => string }) {
  const { coordinates, locate, isLocating, error } = useGeolocation();
  const [professionals, setProfessionals] = useState<Professional[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!coordinates) return;
    setIsLoading(true);
    professionalsApi
      .list({ latitude: coordinates.latitude, longitude: coordinates.longitude, radiusKm: 10 })
      .then((response) => setProfessionals(response.items))
      .finally(() => setIsLoading(false));
  }, [coordinates]);

  if (!coordinates) {
    return (
      <div className="flex flex-col items-start gap-2">
        <Button onClick={locate} isLoading={isLocating}>Show tailors near me</Button>
        {error && <p className="text-sm text-thread">{error}</p>}
      </div>
    );
  }

  return <ProfessionalGrid professionals={professionals} total={professionals.length} isLoading={isLoading} detailsPathFor={detailsPathFor} />;
}
