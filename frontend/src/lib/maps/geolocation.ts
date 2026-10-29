/** Thin wrapper over the browser Geolocation API, used by "use my current
 * location" affordances (Find a Tailor, delivery pickup confirmation). */
export interface Coordinates {
  latitude: number;
  longitude: number;
}

export type GeolocationErrorCode = "PERMISSION_DENIED" | "POSITION_UNAVAILABLE" | "TIMEOUT" | "UNSUPPORTED";

export class GeolocationError extends Error {
  constructor(public readonly code: GeolocationErrorCode, message: string) {
    super(message);
    this.name = "GeolocationError";
  }
}

const ERROR_CODES: Record<number, GeolocationErrorCode> = {
  1: "PERMISSION_DENIED",
  2: "POSITION_UNAVAILABLE",
  3: "TIMEOUT",
};

export function getCurrentPosition(): Promise<Coordinates> {
  return new Promise((resolve, reject) => {
    if (!("geolocation" in navigator)) {
      reject(new GeolocationError("UNSUPPORTED", "Geolocation is not supported by this browser."));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => resolve({ latitude: position.coords.latitude, longitude: position.coords.longitude }),
      (error) => reject(
        new GeolocationError(
          ERROR_CODES[error.code] ?? "POSITION_UNAVAILABLE",
          error.code === 1
            ? "Location permission was denied. Please allow location access in your browser settings."
            : error.code === 3
            ? "Location request timed out. Please try again."
            : "Your location could not be determined.",
        )
      ),
      { enableHighAccuracy: true, timeout: 10_000 },
    );
  });
}
