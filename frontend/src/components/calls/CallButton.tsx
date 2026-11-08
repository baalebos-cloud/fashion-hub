import { useCallStore } from "@/store/call.store";
import { Button, type ButtonProps } from "@/components/ui/button";
import type { CallParty } from "@/types/call";

function PhoneIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2"
        stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

interface CallButtonProps {
  orderId: string;
  party: CallParty;
  label: string;
  disabled?: boolean;
  variant?: ButtonProps["variant"];
}

/** Starts an in-app call (voice over the internet). Neither side sees the other's number. */
export function CallButton({ orderId, party, label, disabled, variant = "secondary", calleeName }: CallButtonProps & { calleeName?: string }) {
  const start = useCallStore((s) => s.start);
  const phase = useCallStore((s) => s.phase);
  const busy = phase === "starting";
  return (
    <Button type="button" size="sm" variant={variant} onClick={() => void start(orderId, party, calleeName ?? label)}
      isLoading={busy} disabled={disabled || (phase !== "idle" && phase !== "ended")}>
      {!busy && <PhoneIcon />}{label}
    </Button>
  );
}
