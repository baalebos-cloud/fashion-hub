import { Spinner } from "@/components/ui/spinner";

export function LoadingScreen({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex h-full min-h-[240px] flex-col items-center justify-center gap-3 text-ink-soft">
      <Spinner size="lg" />
      <span className="text-sm">{label}</span>
    </div>
  );
}
