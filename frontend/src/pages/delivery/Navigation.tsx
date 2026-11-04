import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { deliveriesApi } from "@/api/deliveries.api";
import type { DeliveryTrip } from "@/types/delivery";
import { DispatchTripCard } from "@/components/delivery/DispatchTripCard";
import { RiderGpsSharing } from "@/components/delivery/RiderGpsSharing";
import { useDelivery } from "@/hooks/use-delivery";
import { useOrderWeather } from "@/hooks/use-weather";
import { WeatherForecastCard } from "@/components/weather/WeatherForecastCard";
import { LoadingScreen } from "@/components/common/LoadingScreen";

export default function Navigation() {
  const { deliveryId } = useParams<{ deliveryId: string }>();
  const { delivery, isLoading } = useDelivery(deliveryId);
  const [trip, setTrip] = useState<DeliveryTrip | null>(null);
  useEffect(() => {
    if (!deliveryId) return;
    let active = true;
    deliveriesApi.getTrip(deliveryId).then((data) => { if (active) setTrip(data); }).catch(() => {});
    return () => { active = false; };
  }, [deliveryId]);
  const { weather, isLoading: isWeatherLoading, error: weatherError } = useOrderWeather(delivery?.order_id, Boolean(delivery));

  if (isLoading || !delivery) return <LoadingScreen />;

  return (
    <div className="flex flex-col gap-4">
      <h1 className="font-display text-xl text-ink">Navigate</h1>
      <WeatherForecastCard weather={weather} isLoading={isWeatherLoading} error={weatherError} />
      {trip ? <DispatchTripCard trip={trip} /> : <p className="text-sm text-ink-soft">Routing details are unavailable. Check your delivery assignment.</p>}
      {deliveryId && delivery.status === "in_transit" && <RiderGpsSharing deliveryId={deliveryId} />}
    </div>
  );
}
