import { useParams, useNavigate } from "react-router-dom";
import { DeliveryConfirmation } from "@/components/delivery/DeliveryConfirmation";
import { deliveryRoutes } from "@/config/routes.config";

export default function Dropoff() {
  const { deliveryId } = useParams<{ deliveryId: string }>();
  const navigate = useNavigate();

  return (
    <div className="max-w-sm">
      <h1 className="mb-4 font-display text-xl text-ink">Confirm drop-off</h1>
      <DeliveryConfirmation
        onConfirm={async () => {
          navigate(deliveryRoutes.details(deliveryId ?? ""));
        }}
      />
    </div>
  );
}
