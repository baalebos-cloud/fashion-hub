import { useState } from "react";
import { Button } from "@/components/ui/button";
import { setBrowserOptOut, trackingDisabled } from "@/lib/tracking/interactions";

/** Lets a visitor (signed in or not) stop this browser sending shopping activity. */
export function BrowserTrackingChoice() {
  const [off, setOff] = useState(() => trackingDisabled());
  return (
    <div className="flex flex-col items-start gap-2">
      <p role="status">
        {off ? "This browser is not sending shopping activity to Tailora." : "This browser is sending shopping activity to Tailora."}
      </p>
      <Button size="sm" variant="secondary" onClick={() => { setBrowserOptOut(!off); setOff(trackingDisabled()); }}>
        {off ? "Allow on this browser" : "Stop on this browser"}
      </Button>
    </div>
  );
}
