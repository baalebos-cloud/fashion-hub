# Weather at Delivery

`GET /api/v1/orders/{order_id}/weather` returns the forecast at an
order's delivery destination, aimed at the delivery's current ETA (not
just "now") once a `Delivery`/`DeliveryTracking` row exists for the
order -- see `app/api/v1/orders.py::get_order_delivery_weather`. Visible
to the order's customer and its assigned delivery partner (same
`_assert_can_view_order` check as every other order sub-resource).

`GET /api/v1/weather/current?latitude=&longitude=` is the standalone
lookup, e.g. for a delivery partner's own current position.

## Provider

`app/integrations/weather/` -- `WeatherProvider` ABC + an
`OpenWeatherMapProvider` implementation (One Call API 3.0). Swappable via
`WEATHER_PROVIDER` the same way payments/maps/delivery providers are.

## Caching

`WeatherService` caches both current and forecast lookups in Redis for 15
minutes, keyed by rounded coordinates (+ hour-bucket for forecasts) --
weather doesn't change fast enough to justify hitting the provider on
every 15-second tracking poll from the frontend.

## `rain_expected`

`WeatherService.is_rain_expected()` is the one place that turns a raw
condition string into a yes/no the frontend can render a warning banner
from directly, rather than re-deriving "is this bad weather" client-side
from provider-specific condition codes.
