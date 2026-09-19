import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { WeatherSnapshot } from "@/types/weather";

const CONDITION_ICON: Record<string, string> = {
  rain: "🌧️",
  drizzle: "🌦️",
  thunderstorm: "⛈️",
  clear: "☀️",
  clouds: "☁️",
  snow: "❄️",
  mist: "🌫️",
  fog: "🌫️",
};

function iconFor(condition: string): string {
  return CONDITION_ICON[condition.toLowerCase()] ?? "🌤️";
}

export interface WeatherForecastCardProps {
  weather: WeatherSnapshot | null;
  isLoading?: boolean;
  error?: string | null;
}

/**
 * Shown on order tracking pages so the customer and the delivery partner
 * both know what to expect at the delivery destination -- specifically
 * built to surface rain (see backend/docs/weather.md's `rain_expected`
 * flag) since that's the scenario the product spec calls out by name.
 */
export function WeatherForecastCard({ weather, isLoading, error }: WeatherForecastCardProps) {
  if (isLoading && !weather) {
    return <Skeleton className="h-20" />;
  }

  if (error && !weather) {
    return null; // weather is a nice-to-have; fail silently rather than clutter a tracking page with an error banner
  }

  if (!weather) return null;

  return (
    <Card className={weather.rain_expected ? "border-thread/40 bg-[#fbeceA]" : undefined}>
      <div className="flex items-center gap-3">
        <span className="text-2xl" aria-hidden="true">{iconFor(weather.condition)}</span>
        <div className="flex-1">
          <div className="text-sm font-medium text-ink">
            {Math.round(weather.temperature_celsius)}°C — {weather.description}
          </div>
          <div className="text-xs text-ink-soft">
            {weather.rain_expected
              ? "Rain is expected around delivery time — your order may be delayed."
              : "At the delivery destination"}
          </div>
        </div>
      </div>
    </Card>
  );
}
