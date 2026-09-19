import { useParams } from "react-router-dom";
import { useDelivery } from "@/hooks/use-delivery";
import { useOrderWeather } from "@/hooks/use-weather";
import { DeliveryMap } from "@/components/delivery/DeliveryMap";
import { WeatherForecastCard } from "@/components/weather/WeatherForecastCard";
import { LoadingScreen } from "@/components/common/LoadingScreen";

export default function Navigation() {
  const { deliveryId } = useParams<{ deliveryId: string }>();
  const { delivery, isLoading } = useDelivery(deliveryId);
  const { weather, isLoading: isWeatherLoading, error: weatherError } = useOrderWeather(delivery?.order_id, Boolean(delivery));

  if (isLoading || !delivery) return <LoadingScreen />;

  return (
    <div className="flex flex-col gap-4">
      <h1 className="font-display text-xl text-ink">Navigate</h1>
      <WeatherForecastCard weather={weather} isLoading={isWeatherLoading} error={weatherError} />
      <DeliveryMap />
    </div>
  );
}
