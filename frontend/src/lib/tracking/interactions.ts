/**
 * Records shopping activity for recommendations: views, searches and started bookings.
 *
 * Events are queued and sent in small batches a few seconds apart (and when the tab is hidden),
 * so tracking never slows a page down or shows an error. Nothing is sent when the browser asks
 * sites not to track (Global Privacy Control / Do Not Track) or the visitor turned it off on the
 * Privacy page. Signed-in accounts that switched personalisation off are ignored by the server.
 *
 * Signed-out visitors are identified only by a random ID stored in this browser. It is separate
 * from the security device ID, so shopping activity can't be joined to security records.
 */
import { interactionsApi, type InteractionEventIn } from "@/api/interactions.api";

const ANON_KEY = "tailora.recs_browser_id";
export const OPT_OUT_KEY = "tailora.recs_opt_out";
const FLUSH_DELAY_MS = 3000;
const MAX_BATCH = 50;
const SEARCH_SETTLE_MS = 1500;

let queue: InteractionEventIn[] = [];
let timer: ReturnType<typeof setTimeout> | null = null;
let anonymousId: string | null = null;
const searchTimers = new Map<string, ReturnType<typeof setTimeout>>();

function storage(): Storage | null {
  try {
    return globalThis.localStorage ?? null;
  } catch {
    return null;
  }
}

export function trackingDisabled(): boolean {
  const nav = globalThis.navigator as (Navigator & { globalPrivacyControl?: boolean }) | undefined;
  if (nav?.globalPrivacyControl === true || nav?.doNotTrack === "1") return true;
  return storage()?.getItem(OPT_OUT_KEY) === "1";
}

export function setBrowserOptOut(optOut: boolean): void {
  const store = storage();
  if (!store) return;
  if (optOut) {
    store.setItem(OPT_OUT_KEY, "1");
    store.removeItem(ANON_KEY); // forget this browser's ID too
    anonymousId = null;
    queue = [];
  } else {
    store.removeItem(OPT_OUT_KEY);
  }
}

export function getAnonymousId(): string {
  if (anonymousId) return anonymousId;
  const store = storage();
  const stored = store?.getItem(ANON_KEY);
  if (stored && /^[0-9a-f-]{36}$/i.test(stored)) return (anonymousId = stored);
  const fresh = globalThis.crypto?.randomUUID?.();
  if (!fresh) return "";
  try {
    store?.setItem(ANON_KEY, fresh);
  } catch {
    // storage full or blocked: keep the ID for this page load only
  }
  return (anonymousId = fresh);
}

export async function flush(): Promise<void> {
  if (timer) {
    clearTimeout(timer);
    timer = null;
  }
  if (queue.length === 0) return;
  const events = queue.slice(0, MAX_BATCH);
  queue = queue.slice(MAX_BATCH);
  const id = getAnonymousId();
  try {
    await interactionsApi.send({ anonymous_id: id || undefined, events });
  } catch {
    // Recommendations are best-effort; a lost batch is not worth bothering anyone about.
  }
  if (queue.length > 0) schedule();
}

function schedule(): void {
  if (!timer) timer = setTimeout(() => void flush(), FLUSH_DELAY_MS);
}

function enqueue(event: InteractionEventIn): void {
  if (trackingDisabled()) return;
  queue.push(event);
  if (queue.length >= MAX_BATCH) void flush();
  else schedule();
}

export type ItemType = "product" | "design" | "professional";

/** The page section a visit came from (e.g. ?from=similar_items), or the given default. */
export function viewSource(fromParam: string | null, fallback: string): string {
  return fromParam && /^[a-z][a-z_]{0,31}$/.test(fromParam) ? fromParam : fallback;
}

export function trackView(itemType: ItemType, itemId: string | undefined, source: string): void {
  if (itemId) enqueue({ event_type: "view", item_type: itemType, item_id: itemId, source });
}

export function trackBookingStarted(professionalId: string | undefined, source = "booking"): void {
  if (professionalId) enqueue({ event_type: "booking_started", item_type: "professional", item_id: professionalId, source });
}

/** Records a search once the person stops typing, so each keystroke isn't a search. */
export function trackSearch(query: string, source: string): void {
  const existing = searchTimers.get(source);
  if (existing) clearTimeout(existing);
  const text = query.trim();
  if (text.length < 2) {
    searchTimers.delete(source);
    return;
  }
  searchTimers.set(source, setTimeout(() => {
    searchTimers.delete(source);
    enqueue({ event_type: "search", search_query: text.slice(0, 100), source });
  }, SEARCH_SETTLE_MS));
}

if (typeof document !== "undefined") {
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") void flush();
  });
}

/**
 * Called when the signed-in account changes. Drops events queued for the previous account and,
 * on sign-out, starts a new browser ID so the next person on a shared device isn't linked to the
 * previous account's activity.
 */
export function discardPendingInteractions({ newBrowserId }: { newBrowserId: boolean }): void {
  queue = [];
  if (timer) clearTimeout(timer);
  timer = null;
  searchTimers.forEach(clearTimeout);
  searchTimers.clear();
  if (newBrowserId) {
    anonymousId = null;
    try {
      storage()?.removeItem(ANON_KEY);
    } catch {
      /* storage blocked */
    }
  }
}

/** Test helper. */
export function resetTrackingForTests(): void {
  queue = [];
  anonymousId = null;
  if (timer) clearTimeout(timer);
  timer = null;
  searchTimers.forEach(clearTimeout);
  searchTimers.clear();
}
