export interface WeatherSnapshot {
  condition: string;
  description: string;
  temperature_celsius: number;
  feels_like_celsius: number;
  precipitation_probability?: number | null;
  wind_speed_kmh?: number | null;
  icon_code?: string | null;
  observed_at: string;
  rain_expected: boolean;
}
