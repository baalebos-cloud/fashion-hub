import { useEffect, useRef, useState } from "react";
import { useMap } from "@/hooks/use-map";
import { useGeolocation } from "@/hooks/use-geolocation";
import { reverseGeocode } from "@/lib/maps/geocoding";
import { mapConfig } from "@/config/map.config";
import { Button } from "@/components/ui/button";
import type { PickedLocation } from "@/types/location";

export interface MapLocationPickerProps {
  mode?: "shop" | "delivery";
  onChange?: (location: PickedLocation) => void;
  onResolvingChange?: (resolving: boolean) => void;
  onSelect: (location: PickedLocation) => void;
}

type Point = { lat: number; lng: number };
type MapsApi = {
  Map: new (element: HTMLElement, options: Record<string, unknown>) => {
    addListener: (event: string, handler: (event: { latLng?: { lat: () => number; lng: () => number } }) => void) => void;
    panTo: (point: Point) => void;
    setZoom: (zoom: number) => void;
  };
  Marker: new (options: Record<string, unknown>) => { setPosition: (point: Point) => void; setMap: (map: null) => void; addListener?: (event: string, callback: () => void) => void; getPosition?: () => { lat: () => number; lng: () => number } | null };
};
type GoogleHost = Window & { google?: { maps?: MapsApi } };
type MapInstance = InstanceType<MapsApi["Map"]>;
type MarkerInstance = InstanceType<MapsApi["Marker"]>;

export function MapLocationPicker({ onSelect, onChange, onResolvingChange, mode = "shop" }: MapLocationPickerProps) {
  const { isReady, error: mapError } = useMap();
  const { locate, isLocating, error: geolocationError, errorCode: geolocationErrorCode } = useGeolocation();
  const elementRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapInstance | null>(null);
  const markerRef = useRef<MarkerInstance | null>(null);
  const [resolvedAddress, setResolvedAddress] = useState<string>("");
  const [selectedPoint, setSelectedPoint] = useState<Point | null>(null);
  type Details = Omit<PickedLocation, "latitude" | "longitude" | "formatted_address">;
  const NO_DETAILS: Details = { city: null, state_region: null, country: null };
  const [addressDetails, setAddressDetails] = useState<Details>(NO_DETAILS);
  const requestVersion = useRef(0);
  const [selectionError, setSelectionError] = useState<string | null>(null);
  const [addressNotFound, setAddressNotFound] = useState(false);
  const [isResolving, setResolving] = useState(false);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;
  const resolvingRef = useRef(onResolvingChange);
  resolvingRef.current = onResolvingChange;

  async function selectPoint(latitude: number, longitude: number) {
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude) ||
        Math.abs(latitude) > 90 || Math.abs(longitude) > 180) {
      setSelectionError("Invalid coordinates. Place the pin again.");
      return;
    }
    const version = ++requestVersion.current;
    setSelectedPoint({ lat: latitude, lng: longitude });
    setAddressDetails(NO_DETAILS);
    // Coordinates are shown beside the field, never put into it as if they were an address.
    setResolvedAddress("");
    setAddressNotFound(false);
    setSelectionError(null);
    setResolving(true);
    resolvingRef.current?.(true);
    onChangeRef.current?.({ latitude, longitude, formatted_address: null, city: null, state_region: null, country: null });
    try {
      const address = await reverseGeocode(latitude, longitude);
      if (requestVersion.current !== version) return;
      if (address.formatted_address?.trim()) {
        setResolvedAddress(address.formatted_address);
        const details: Details = { city: address.city, state_region: address.state_region, country: address.country,
          street: address.street, area: address.area, lga: address.lga, landmark: address.landmark,
          nearest_bus_stop: address.nearest_bus_stop };
        setAddressDetails(details);
        onChangeRef.current?.({ latitude, longitude, formatted_address: address.formatted_address, ...details });
      }
      else if (requestVersion.current === version) setAddressNotFound(true);
    } catch {
      // Not an error for the user: the pin is valid, only the street name lookup failed.
      if (requestVersion.current === version) setAddressNotFound(true);
    } finally {
      if (requestVersion.current === version) { setResolving(false); resolvingRef.current?.(false); }
    }
  }

  function saveSelection() {
    if (!selectedPoint) return;
    onSelectRef.current({
      latitude: selectedPoint.lat,
      longitude: selectedPoint.lng,
      formatted_address: resolvedAddress.trim() || null,
      ...addressDetails,
    });
  }

  useEffect(() => {
    if (!isReady || !elementRef.current) return;
    if (mapConfig.provider !== "google_maps") {
      setSelectionError("This address picker needs the Google Maps JavaScript API.");
      return;
    }
    const maps = (window as GoogleHost).google?.maps;
    if (!maps?.Map || !maps.Marker) {
      setSelectionError("The Google Maps SDK loaded without the required map APIs. Check your Maps JavaScript API key.");
      return;
    }
    const map = new maps.Map(elementRef.current, {
      center: mapConfig.defaultCenter, zoom: mapConfig.defaultZoom,
      mapTypeControl: false, streetViewControl: false,
    });
    mapRef.current = map;
    map.addListener("click", (event) => {
      const position = event.latLng;
      if (!position) return;
      const point = { lat: position.lat(), lng: position.lng() };
      if (!markerRef.current) {
        markerRef.current = new maps.Marker({ map, position: point, draggable: true });
        markerRef.current.addListener?.("dragend", () => {
          const dropped = markerRef.current?.getPosition?.();
          if (dropped) void selectPoint(dropped.lat(), dropped.lng());
        });
      }
      else markerRef.current.setPosition(point);
      void selectPoint(point.lat, point.lng);
    });
    return () => {
      markerRef.current?.setMap(null);
      markerRef.current = null;
      mapRef.current = null;
    };
  // Map listener is installed only when the SDK becomes ready.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isReady]);

  async function handleUseCurrentLocation() {
    const coords = await locate();
    if (!coords) return;
    const point = { lat: coords.latitude, lng: coords.longitude };
    mapRef.current?.panTo(point);
    mapRef.current?.setZoom(16);
    const maps = (window as GoogleHost).google?.maps;
    if (maps && mapRef.current) {
      if (!markerRef.current) markerRef.current = new maps.Marker({ map: mapRef.current, position: point, draggable: true });
      else markerRef.current.setPosition(point);
    }
    await selectPoint(coords.latitude, coords.longitude);
  }

  return (
    <div className="flex flex-col gap-3">
      <div ref={elementRef} role="application" aria-label="Interactive address map. Click to place a pin."
        className="h-56 w-full rounded-card border border-line bg-muslin"
        style={{ display: isReady && !mapError ? "block" : "none" }} />
      {(!isReady || mapError) && (
        <div className="flex h-56 items-center justify-center rounded-card border border-line bg-muslin p-4 text-center text-sm text-ink-soft">
          {mapError || "Loading map…"}
        </div>
      )}
      <p className="text-xs text-ink-soft">Tap the map to choose your address, or use your current location.</p>
      <Button type="button" variant="secondary" onClick={() => { void handleUseCurrentLocation(); }}
        isLoading={isLocating || isResolving} className="self-start">
        Use my current location
      </Button>
      {selectedPoint && (
        <p className="text-xs text-ink-soft" aria-live="polite">
          Pin placed at {selectedPoint.lat.toFixed(5)}, {selectedPoint.lng.toFixed(5)}
        </p>
      )}
      {isResolving && <p role="status" className="text-sm text-ink-soft">Finding the street address for your pin…</p>}
      {addressNotFound && !isResolving && (
        <p role="status" className="rounded-lg bg-[#fbf0dd] px-3 py-2 text-sm text-[#8a5f1f]">
          {mode === "shop"
            ? "We couldn't find the street name for this pin automatically. Type your shop's address below; your pin position is kept."
            : "We couldn't find the street name for this pin automatically. Complete the address fields below; your pin position is kept."}
        </p>
      )}
      {mode === "shop" && selectedPoint && (
        <label className="text-sm text-ink">
          Shop address
          <input aria-label="Shop address" value={resolvedAddress} disabled={isResolving}
            placeholder="Street address, e.g. 14 Iworoko Road, Ado-Ekiti"
            className="mt-1 w-full rounded-lg border border-line bg-paper px-3 py-2.5 text-sm text-ink placeholder:text-ink-soft/60 focus:border-brass focus:outline-none"
            onChange={(event) => { setResolvedAddress(event.target.value); setAddressDetails(NO_DETAILS); }} />
          <span className="mt-1 block text-xs text-ink-soft">Customers and riders see this address, so make it easy to find.</span>
        </label>
      )}
      {mode === "shop" && selectedPoint && (
        <Button type="button" onClick={saveSelection} disabled={isResolving || resolvedAddress.trim().length < 5}>
          Save shop location
        </Button>
      )}
      {selectionError && <p role="alert" className="text-sm text-thread">{selectionError}</p>}
      {geolocationError && (
        <p role="alert" className="text-sm text-thread">
          {geolocationErrorCode === "PERMISSION_DENIED"
            ? "Location permission was denied. Allow location access in your browser settings, or tap the map to select an address manually."
            : geolocationErrorCode === "TIMEOUT"
            ? "Location request timed out. Please try again, or tap the map to select an address manually."
            : "Location access was unavailable. Tap the map to select an address manually."}
        </p>
      )}
    </div>
  );
}
