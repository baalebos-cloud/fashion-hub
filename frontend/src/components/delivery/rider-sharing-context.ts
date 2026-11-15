import { createContext, useContext } from "react";

export type SharingStatus = "off" | "live" | "retrying" | "denied" | "no_signal";

export interface RiderSharing {
  /** The delivery being shared, or null when not sharing. */
  deliveryId: string | null;
  status: SharingStatus;
  busy: boolean;
  message: string | null;
  lastSent: Date | null;
  start: (deliveryId: string) => Promise<void>;
  stop: (note?: string) => Promise<void>;
}

export const RiderSharingContext = createContext<RiderSharing | null>(null);

/** Location sharing state for the rider area (see RiderSharingProvider). */
export function useRiderSharing(): RiderSharing {
  const value = useContext(RiderSharingContext);
  if (!value) throw new Error("useRiderSharing must be used inside RiderSharingProvider");
  return value;
}
