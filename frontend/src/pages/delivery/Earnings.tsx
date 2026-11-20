import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { deliveriesApi } from "@/api/deliveries.api";
import { Card } from "@/components/ui/card";
import { deliveryRoutes } from "@/config/routes.config";
import { formatCurrency } from "@/lib/formatters/currency";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { RiderEarnings } from "@/types/delivery";

const PERIODS = [["today", "Today"], ["week", "This week"], ["month", "This month"], ["all_time", "All time"]] as const;

/** Agreed fares of the rider's delivered jobs. */
export default function Earnings() {
  const [earnings, setEarnings] = useState<RiderEarnings | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    deliveriesApi.myEarnings()
      .then((value) => { if (active) setEarnings(value); })
      .catch((err) => { if (active) setError(getDisplayErrorMessage(err, "Couldn't load your earnings.")); });
    return () => { active = false; };
  }, []);

  return (
    <div className="flex flex-col gap-4">
      <h1 className="font-display text-xl text-ink">Earnings</h1>
      {error && <p role="alert" className="text-thread">{error}</p>}
      {!earnings && !error && <p role="status">Loading your earnings…</p>}
      {earnings && (
        <>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {PERIODS.map(([key, label]) => (
              <Card key={key}>
                <div className="text-xs text-ink-soft">{label}</div>
                <div className="mt-1 text-xl font-medium text-ink">{formatCurrency(earnings[key].amount)}</div>
                <div className="text-xs text-ink-soft">
                  {earnings[key].deliveries} deliver{earnings[key].deliveries === 1 ? "y" : "ies"}
                </div>
              </Card>
            ))}
          </div>
          <p className="text-xs text-ink-soft">
            The agreed fares of the jobs you delivered, in Nigerian time (weeks start on Monday).{" "}
            <Link to={deliveryRoutes.history} className="font-semibold text-indigo">See each delivery</Link>
          </p>
        </>
      )}
    </div>
  );
}
