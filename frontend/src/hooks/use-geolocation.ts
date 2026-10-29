import { useCallback, useState } from "react";
import { getCurrentPosition, GeolocationError, type Coordinates } from "@/lib/maps/geolocation";

export function useGeolocation() {
  const [coordinates, setCoordinates] = useState<Coordinates | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [isLocating, setIsLocating] = useState(false);

  const locate = useCallback(async () => {
    setIsLocating(true);
    setError(null);
    setErrorCode(null);
    try {
      const position = await getCurrentPosition();
      setCoordinates(position);
      return position;
    } catch (err) {
      if (err instanceof GeolocationError) {
        setErrorCode(err.code);
        setError(err.message);
      } else {
        setError(err instanceof Error ? err.message : "Could not determine your location.");
      }
      return null;
    } finally {
      setIsLocating(false);
    }
  }, []);

  return { coordinates, error, errorCode, isLocating, locate };
}
