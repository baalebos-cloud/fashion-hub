import { useEffect, useRef, useState } from "react";
import { useMap } from "@/hooks/use-map";
import { useGeolocation } from "@/hooks/use-geolocation";
import { reverseGeocode } from "@/lib/maps/geocoding";
import { mapConfig } from "@/config/map.config";
import { Button } from "@/components/ui/button";
import type { GeoLocation } from "@/types/location";

export interface MapLocationPickerProps {
  onSelect: (location: Pick<GeoLocation, "latitude" | "longitude" | "formatted_address" | "city" | "state_region" | "country">) => void;
}

type Point = { lat: number; lng: number };
type MapsApi = {
  Map: new (element: HTMLElement, options: Record<string, unknown>) => {
    addListener: (event: string, handler: (event: { latLng?: { lat: () => number; lng: () => number } }) => void) => void;
    panTo: (point: Point) => void;
    setZoom: (zoom: number) => void;
  };
  Marker: new (options: Record<string, unknown>) => { setPosition: (point: Point) => void; setMap: (map: null) => void };
};
type GoogleHost = Window & { google?: { maps?: MapsApi } };
type MapInstance = InstanceType<MapsApi["Map"]>;
type MarkerInstance = InstanceType<MapsApi["Marker"]>;

export function MapLocationPicker({ onSelect }: MapLocationPickerProps) {
  const { isReady, error: mapError } = useMap();
  const { locate, isLocating, error: geolocationError } = useGeolocation();
  const elementRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapInstance | null>(null);
  const markerRef = useRef<MarkerInstance | null>(null);
  const [resolvedAddress, setResolvedAddress] = useState<string | null>(null);
  const [selectionError, setSelectionError] = useState<string | null>(null);
  const [isResolving, setResolving] = useState(false);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  async function selectPoint(latitude: number, longitude: number) {
    setSelectionError(null);
    setResolving(true);
    try {
      const address = await reverseGeocode(latitude, longitude);
      setResolvedAddress(address.formatted_address);
      onSelectRef.current({
        latitude, longitude, formatted_address: address.formatted_address,
        city: address.city, state_region: address.state_region, country: address.country,
      });
    } catch {
      setResolvedAddress(null);
      setSelectionError("The pin was placed, but the address could not be resolved. Check the maps service and try again.");
    } finally {
      setResolving(false);
    }
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
      if (!markerRef.current) markerRef.current = new maps.Marker({ map, position: point });
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
      if (!markerRef.current) markerRef.current = new maps.Marker({ map: mapRef.current, position: point });
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
      {resolvedAddress && <p role="status" className="text-sm text-ink-soft">{resolvedAddress}</p>}
      {isResolving && <p role="status" className="text-sm text-ink-soft">Finding the selected address…</p>}
      {selectionError && <p role="alert" className="text-sm text-thread">{selectionError}</p>}
      {geolocationError && (
        <p role="alert" className="text-sm text-thread">
          Location access was unavailable or denied. Allow location permission in your browser, or tap the map to select an address manually.
        </p>
      )}
    </div>
  );
}
