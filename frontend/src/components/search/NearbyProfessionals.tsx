import { useEffect, useState } from "react";
import { useGeolocation } from "@/hooks/use-geolocation";
import { professionalsApi } from "@/api/professionals.api";
import { addressesApi } from "@/api/addresses.api";
import { ProfessionalGrid } from "@/components/professionals/ProfessionalGrid";
import { Button } from "@/components/ui/button";
import type { Professional } from "@/types/professional";
import type { SavedAddress } from "@/types/address";

export function NearbyProfessionals({ detailsPathFor }: { detailsPathFor: (id: string) => string }) {
  const { coordinates, locate, isLocating, error: geolocationError, errorCode: geolocationErrorCode } = useGeolocation();
  const [city, setCity] = useState("");
  const [saved, setSaved] = useState<SavedAddress[]>([]);
  const [professionals, setProfessionals] = useState<Professional[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    addressesApi.list().then(setSaved).catch(() => { /* Guests may not have saved addresses. */ });
  }, []);

  useEffect(() => {
    let active = true;
    setIsLoading(true);
    setError("");
    professionalsApi.list(city.trim()
      ? { query: city.trim() }
      : coordinates
        ? { latitude: coordinates.latitude, longitude: coordinates.longitude, radiusKm: 10 }
        : {})
      .then(response => {
        if (!active) return;
        setProfessionals(response.items);
        setTotal(response.total);
      })
      .catch(() => { if (active) setError("Unable to load professionals. Retry your search."); })
      .finally(() => { if (active) setIsLoading(false); });
    return () => { active = false; };
  }, [coordinates, city]);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex min-w-0 flex-1 flex-col gap-1 text-sm">
          City, neighborhood or postal code
          <input aria-label="Enter City, Neighborhood, or Postal Code"
            className="min-h-11 rounded-lg border border-line bg-paper px-3"
            value={city} onChange={e => setCity(e.target.value)} placeholder="Ikeja, Lekki, Abuja…" />
        </label>
        <Button onClick={() => { void locate(); }} isLoading={isLocating}>Use my location</Button>
      </div>
      {saved.length > 0 && (
        <label className="flex flex-col gap-1 text-sm">Use a saved address
          <select className="min-h-11 rounded-lg border border-line bg-paper px-3" defaultValue=""
            onChange={e => {
              const item = saved.find(address => address.id === e.target.value);
              if (item) setCity(item.city || item.formatted_address);
            }}>
            <option value="">Select saved address</option>
            {saved.map(address => <option value={address.id} key={address.id}>{address.label}: {address.formatted_address}</option>)}
          </select>
        </label>
      )}
      <p className="text-xs text-ink-soft">Location access is optional. Browse verified professionals or search manually.</p>
      {geolocationError && (
        <p role="alert" className="text-sm text-thread">
          {geolocationErrorCode === "PERMISSION_DENIED"
            ? "Location permission was denied. Allow location access in your browser settings to search by proximity."
            : geolocationErrorCode === "TIMEOUT"
            ? "Location request timed out. Try again, or search by city above."
            : "Your location could not be determined. Search by city above."}
        </p>
      )}
      {error && <p role="alert" className="text-sm text-thread">{error}</p>}
      <ProfessionalGrid professionals={professionals} total={total} isLoading={isLoading} detailsPathFor={detailsPathFor} />
    </div>
  );
}
