import { useEffect, useState } from "react";
import { vendorsApi } from "@/api/vendors.api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { MapLocationPicker } from "@/components/checkout/MapLocationPicker";
import { getDisplayErrorMessage } from "@/lib/utils/errors";

/** Where riders collect materials from. Required before a vendor can request a rider. */
export function VendorPickupLocation() {
  const [hasLocation, setHasLocation] = useState<boolean | null>(null);
  const [editing, setEditing] = useState(false);
  const [message, setMessage] = useState<{ tone: "ok" | "error"; text: string } | null>(null);

  useEffect(() => {
    vendorsApi.mine().then((v) => setHasLocation(Boolean(v?.warehouse_location_id))).catch(() => setHasLocation(false));
  }, []);

  if (hasLocation === null) return null;
  const showPicker = editing || !hasLocation;

  return (
    <Card className="flex flex-col gap-3 p-5" role="region" aria-label="Store pickup location">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-medium text-ink">Store pickup location</h2>
          <p className="text-xs text-ink-soft">
            {hasLocation
              ? "Riders collect materials from here. Changing it doesn't affect riders already on their way."
              : "Set where riders collect materials from. You need this before you can request a rider."}
          </p>
        </div>
        {hasLocation && !editing && <Button size="sm" variant="secondary" onClick={() => setEditing(true)}>Change</Button>}
      </div>
      {showPicker && (
        <MapLocationPicker onSelect={async (location) => {
          setMessage(null);
          try {
            await vendorsApi.updateMyLocation({
              latitude: location.latitude, longitude: location.longitude, formattedAddress: location.formatted_address,
              city: location.city, stateRegion: location.state_region, country: location.country,
            });
            setHasLocation(true);
            setEditing(false);
            setMessage({ tone: "ok", text: "Pickup location saved." });
          } catch (err) {
            setMessage({ tone: "error", text: getDisplayErrorMessage(err, "Couldn't save your pickup location.") });
          }
        }} />
      )}
      {message && <p role={message.tone === "error" ? "alert" : "status"}
        className={message.tone === "error" ? "text-sm text-thread" : "text-sm text-[#256a3f]"}>{message.text}</p>}
    </Card>
  );
}
