import { useAuth } from "@/hooks/use-auth";

function partOfDay(hour: number) {
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

/** "Good afternoon, Ada" heading for dashboards; first name only. */
export function Greeting({ subtitle }: { subtitle?: string }) {
  const { user } = useAuth();
  const first = (user?.full_name ?? "").trim().split(" ")[0];
  return (
    <div>
      <h1 className="font-display text-2xl text-ink">{partOfDay(new Date().getHours())}{first ? `, ${first}` : ""}</h1>
      {subtitle && <p className="mt-1 text-sm text-ink-soft">{subtitle}</p>}
    </div>
  );
}
