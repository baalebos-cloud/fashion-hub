import { useState, type ComponentProps } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useMeasurements } from "@/hooks/use-measurements";
import { useToast } from "@/components/ui/toast";
import { DesignRequirementForm } from "@/components/designs/DesignRequirementForm";
import { MapLocationPicker } from "@/components/checkout/MapLocationPicker";
import { Select } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { locationsApi } from "@/api/locations.api";
import { customerRoutes } from "@/config/routes.config";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { ordersApi } from "@/api/orders.api";

export default function CreateOrder() {
  const { professionalId } = useParams<{ professionalId: string }>();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { profiles } = useMeasurements();

  const [measurementProfileId, setMeasurementProfileId] = useState("");
  const [requirements, setRequirements] = useState("");
  const [deliveryAddressId, setDeliveryAddressId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleLocationSelect(location: Parameters<ComponentProps<typeof MapLocationPicker>["onSelect"]>[0]) {
    const saved = await locationsApi.create({ ...location, locationType: "customer_address" });
    setDeliveryAddressId(saved.id);
  }

  async function handleSubmit() {
    if (!professionalId || !measurementProfileId || !deliveryAddressId) {
      setError("Please select a measurement profile and delivery location.");
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      const order = await ordersApi.create({
        professional_user_id: professionalId,
        items: [{ reference_type: "service", name_snapshot: requirements || "Custom order", unit_price: 0, quantity: 1 }],
        delivery_address_id: deliveryAddressId,
        measurement_profile_id: measurementProfileId,
      });
      showToast("Order created — proceed to payment.", "success");
      navigate(customerRoutes.payment(order.id));
    } catch (err) {
      setError(getDisplayErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-lg flex-col gap-6">
      <h1 className="font-display text-xl text-ink">Place your order</h1>

      <div>
        <label className="mb-1.5 block text-sm font-medium text-ink">Measurement profile</label>
        <Select value={measurementProfileId} onChange={(e) => setMeasurementProfileId(e.target.value)}>
          <option value="">Select a profile…</option>
          {profiles.map((profile) => (
            <option key={profile.id} value={profile.id}>{profile.label}</option>
          ))}
        </Select>
      </div>

      <DesignRequirementForm value={requirements} onChange={setRequirements} />

      <div>
        <h2 className="mb-2 text-sm font-medium text-ink">Delivery location</h2>
        <MapLocationPicker onSelect={handleLocationSelect} />
      </div>

      {error && <p className="text-sm text-thread">{error}</p>}

      <Button onClick={handleSubmit} isLoading={isSubmitting} className="self-start">Continue to checkout</Button>
    </div>
  );
}
