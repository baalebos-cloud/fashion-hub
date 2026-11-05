import { useState } from "react";
import { callsApi } from "@/api/calls.api";
import { Button, type ButtonProps } from "@/components/ui/button";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
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

/**
 * Starts a masked call: Tailora rings the user's own phone, then connects them.
 * Neither side sees the other's number.
 */
export function CallButton({ orderId, party, label, disabled, variant = "secondary" }: CallButtonProps) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ tone: "ok" | "error"; text: string } | null>(null);

  async function call() {
    setBusy(true);
    setMessage(null);
    try {
      const started = await callsApi.start(orderId, party);
      const ending = started.your_phone_ending ? ` ending ${started.your_phone_ending}` : "";
      setMessage({ tone: "ok", text: `Tailora is calling your phone${ending}. Answer to be connected to ${started.callee_display_name}. Your number stays private.` });
    } catch (err) {
      setMessage({ tone: "error", text: getDisplayErrorMessage(err, "The call couldn't be started. Please try again.") });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-1.5">
      <Button type="button" size="sm" variant={variant} onClick={() => void call()} isLoading={busy} disabled={disabled}>
        {!busy && <PhoneIcon />}{label}
      </Button>
      {message && (
        <p role={message.tone === "error" ? "alert" : "status"}
          className={message.tone === "error" ? "text-xs text-thread" : "text-xs text-ink-soft"}>
          {message.text}
        </p>
      )}
    </div>
  );
}
