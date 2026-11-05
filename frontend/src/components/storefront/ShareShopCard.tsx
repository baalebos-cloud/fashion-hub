import { useEffect, useState, type FormEvent } from "react";
import { HANDLE_PATTERN, storefrontsApi, whatsappShareUrl } from "@/api/storefronts.api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { StorefrontLink } from "@/types/storefront";

/** Owner-facing card: the shop's shareable link, quick share actions, and handle editing. */
export function ShareShopCard({ displayName }: { displayName?: string | null }) {
  const [link, setLink] = useState<StorefrontLink | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    storefrontsApi.myLink().then(setLink).catch((err) => setLoadError(getDisplayErrorMessage(err, "Your shop link isn't available yet.")));
  }, []);

  if (loadError) {
    return (
      <Card>
        <h2 className="text-sm font-medium text-ink">Your shop link</h2>
        <p className="mt-1 text-sm text-ink-soft">{loadError}</p>
      </Card>
    );
  }
  if (!link) return null;

  async function copy() {
    if (!link) return;
    try {
      await navigator.clipboard.writeText(link.share_url);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch { /* Clipboard blocked; the link stays visible to copy by hand. */ }
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    const handle = draft.trim().toLowerCase();
    if (!HANDLE_PATTERN.test(handle)) {
      setSaveError("Use 3–30 lowercase letters, numbers and single hyphens.");
      return;
    }
    setSaving(true);
    setSaveError(null);
    try {
      setLink(await storefrontsApi.changeHandle(handle));
      setEditing(false);
    } catch (err) {
      setSaveError(getDisplayErrorMessage(err, "Could not update your link."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-medium text-ink">Your shop link</h2>
          <p className="mt-0.5 text-xs text-ink-soft">{link.status_message}</p>
        </div>
        <span className={link.is_public
          ? "rounded-full bg-[#e5f3ea] px-2 py-0.5 text-[11px] font-medium text-[#256a3f]"
          : "rounded-full bg-[#fbf0dd] px-2 py-0.5 text-[11px] font-medium text-[#8a5f1f]"}>
          {link.is_public ? "Live" : "Awaiting verification"}
        </span>
      </div>

      {editing ? (
        <form onSubmit={(e) => void save(e)} className="flex flex-col gap-2">
          <label className="text-xs text-ink-soft" htmlFor="shop-handle">Shop link name</label>
          <div className="flex items-center overflow-hidden rounded-lg border border-line bg-paper focus-within:border-brass">
            <span className="px-3 text-sm text-ink-soft">/s/</span>
            <input id="shop-handle" value={draft} onChange={(e) => setDraft(e.target.value)} maxLength={30}
              autoCapitalize="none" autoComplete="off" spellCheck={false}
              className="min-w-0 flex-1 bg-transparent py-2 pr-3 text-sm text-ink outline-none" />
          </div>
          {saveError && <p role="alert" className="text-xs text-thread">{saveError}</p>}
          <div className="flex gap-2">
            <Button type="submit" size="sm" isLoading={saving}>Save link</Button>
            <Button type="button" size="sm" variant="ghost" onClick={() => { setEditing(false); setSaveError(null); }}>Cancel</Button>
          </div>
        </form>
      ) : (
        <div className="flex items-center gap-2 rounded-lg bg-muslin px-3 py-2">
          <code className="min-w-0 flex-1 truncate text-sm text-ink" data-testid="shop-link">{link.share_url}</code>
        </div>
      )}

      {!editing && (
        <div className="flex flex-wrap gap-2">
          <Button size="sm" onClick={() => void copy()}>{copied ? "Copied" : "Copy link"}</Button>
          <a href={whatsappShareUrl(displayName, link.share_url)} target="_blank" rel="noopener noreferrer">
            <Button size="sm" variant="secondary">Share to WhatsApp</Button>
          </a>
          <Button size="sm" variant="ghost" onClick={() => { setDraft(link.handle); setEditing(true); }}>Change link</Button>
        </div>
      )}
    </Card>
  );
}
