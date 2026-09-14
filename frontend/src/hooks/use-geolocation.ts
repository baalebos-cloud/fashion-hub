import { useCallback, useState } from "react";
import { getCurrentPosition, type Coordinates } from "@/lib/maps/geolocation";

export function useGeolocation() {
  const [coordinates, setCoordinates] = useState<Coordinates | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLocating, setIsLocating] = useState(false);

  const locate = useCallback(async () => {
    setIsLocating(true);
    setError(null);
    try {
      const position = await getCurrentPosition();
      setCoordinates(position);
      return position;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not determine your location.");
      return null;
    } finally {
      setIsLocating(false);
    }
  }, []);

  return { coordinates, error, isLocating, locate };
}
