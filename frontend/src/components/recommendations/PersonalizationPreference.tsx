import { useEffect, useState } from "react";
import { Switch } from "@/components/ui/switch";
import { interactionsApi } from "@/api/interactions.api";

/** Account switch for personalised recommendations. Turning it off deletes recorded activity. */
export function PersonalizationPreference() {
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    interactionsApi.getPreference()
      .then((value) => { if (active) setEnabled(value); })
      .catch(() => { if (active) setMessage("Couldn't load this setting. Refresh to try again."); });
    return () => { active = false; };
  }, []);

  async function change(next: boolean) {
    setSaving(true);
    setMessage(null);
    try {
      const saved = await interactionsApi.setPreference(next);
      setEnabled(saved);
      setMessage(saved ? "Personalised recommendations are on."
        : "Personalised recommendations are off, and your recorded browsing activity has been deleted.");
    } catch {
      setMessage("Couldn't save this setting. Try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex max-w-sm flex-col gap-2">
      <label className="flex items-center justify-between text-sm text-ink">
        Personalised recommendations
        <Switch checked={enabled ?? false} disabled={enabled === null || saving}
          onChange={(next) => void change(next)} label="Personalised recommendations" />
      </label>
      <p className="text-xs text-ink-soft">
        Uses what you view, save, search for and buy on Tailora to suggest items and tailors.
        Turning it off stops this and deletes what we've recorded.
      </p>
      {message && <p role="status" className="text-xs text-ink-soft">{message}</p>}
    </div>
  );
}
