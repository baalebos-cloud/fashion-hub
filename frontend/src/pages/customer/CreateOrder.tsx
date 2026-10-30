import { useEffect, useRef, useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import { useMeasurements } from "@/hooks/use-measurements";
import { useDesigns } from "@/hooks/use-designs";
import { useToast } from "@/components/ui/toast";
import { MeasurementForm } from "@/components/measurements/MeasurementForm";
import { DeliveryAddressForm } from "@/components/checkout/DeliveryAddressForm";
import { Select } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { addressesApi } from "@/api/addresses.api";
import { professionalsApi } from "@/api/professionals.api";
import { customerRoutes } from "@/config/routes.config";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { formatCurrency } from "@/lib/formatters/currency";
import { ordersApi } from "@/api/orders.api";
import type { Professional } from "@/types/professional";
import type { SavedAddress } from "@/types/address";

export default function CreateOrder() {
  const { professionalId } = useParams<{ professionalId: string }>();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { profiles, error: measurementError, refetch: refetchProfiles } = useMeasurements();
  const { designs, error: designError, isLoading } = useDesigns(professionalId);
  const [professional, setProfessional] = useState<Professional | null>(null);
  const [addresses, setAddresses] = useState<SavedAddress[]>([]);
  const [selectedDesignId, setSelectedDesignId] = useState("");
  const [measurementProfileId, setMeasurementProfileId] = useState("");
  const [isAddingProfile, setIsAddingProfile] = useState(false);
  const [isAddingAddress, setIsAddingAddress] = useState(false);
  const [deliveryAddressId, setDeliveryAddressId] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const retry = useRef<{ signature: string; key: string } | null>(null);
  const submitting = useRef(false);
  const selectedDesign = designs.find((design) => design.id === selectedDesignId);

  useEffect(() => {
    let active = true;
    setProfessional(null);
    setSelectedDesignId("");
    setLoadError(null);
    if (professionalId) {
      Promise.all([professionalsApi.getById(professionalId), addressesApi.list()])
        .then(([profile, saved]) => {
          if (active) { setProfessional(profile); setAddresses(saved); }
        })
        .catch((err) => { if (active) setLoadError(getDisplayErrorMessage(err)); });
    }
    return () => { active = false; };
  }, [professionalId]);

  async function handleSubmit() {
    if (submitting.current) return;
    if (!professional || !selectedDesign || !measurementProfileId || !deliveryAddressId) {
      setError("Select a published design, measurement profile and delivery address.");
      return;
    }
    const intent = {
      professional_user_id: professional.user_id,
      items: [{ reference_type: "design" as const, reference_id: selectedDesign.id, quantity: 1 }],
      delivery_address_id: deliveryAddressId,
      measurement_profile_id: measurementProfileId,
    };
    const signature = JSON.stringify(intent);
    if (retry.current?.signature !== signature) retry.current = { signature, key: crypto.randomUUID() };
    submitting.current = true;
    setIsSubmitting(true);
    setError(null);
    try {
      const order = await ordersApi.create({ ...intent, idempotency_key: retry.current.key });
      showToast("Order created — proceed to payment.", "success");
      navigate(customerRoutes.payment(order.id));
    } catch (err) {
      setError(getDisplayErrorMessage(err));
    } finally {
      submitting.current = false;
      setIsSubmitting(false);
    }
  }
  return (
    <div className="mx-auto flex max-w-lg flex-col gap-6">
      <h1 className="font-display text-xl text-ink">Place your order</h1>
      <p className="text-sm text-ink-soft">Checkout is currently available for NGN designs delivered within Nigeria.</p>
      <div>
        <label htmlFor="order-design" className="mb-1.5 block text-sm font-medium text-ink">Published design</label>
        <Select id="order-design" value={selectedDesignId} onChange={(e) => setSelectedDesignId(e.target.value)} disabled={isLoading || isSubmitting}>
          <option value="">Select a design…</option>
          {designs.map((design) => <option key={design.id} value={design.id}>{design.title} — {formatCurrency(design.base_price, design.currency)}</option>)}
        </Select>
        {!isLoading && !designError && designs.length === 0 && <p role="status" className="mt-2 text-sm text-ink-soft">This professional has no published designs available for checkout. <Link className="text-brass-deep underline" to={customerRoutes.findProfessionals}>Browse other professionals</Link> or ask this professional to publish a priced design first.</p>}
        <p className="mt-2 text-xs text-ink-soft">Custom work needs an agreed quote and is not available through this checkout yet. The saved order shows the final amount before payment.</p>
      </div>
      <div>
        <label htmlFor="order-measurements" className="mb-1.5 block text-sm font-medium text-ink">Measurement profile</label>
        <Select id="order-measurements" value={measurementProfileId} onChange={(e) => setMeasurementProfileId(e.target.value)} disabled={isSubmitting}>
          <option value="">Select a profile…</option>
          {profiles.map((profile) => <option key={profile.id} value={profile.id}>{profile.label}</option>)}
        </Select>
        {profiles.length === 0 && !measurementError && <p role="status" className="mt-2 text-sm text-ink-soft">No measurement profile saved yet. Use “Add a new measurement profile” below, then select the saved profile.</p>}
        {selectedDesign?.required_measurement_fields?.length ? <p className="mt-1.5 text-xs text-ink-soft">This design needs: {selectedDesign.required_measurement_fields.join(", ").replace(/_/g, " ")}</p> : null}
        <button type="button" onClick={() => setIsAddingProfile(!isAddingProfile)} className="mt-2 text-xs text-brass-deep hover:underline">{isAddingProfile ? "Close measurement form" : "+ Add a new measurement profile"}</button>
      </div>
      {isAddingProfile && <MeasurementForm key={selectedDesignId} requiredFields={selectedDesign?.required_measurement_fields ?? undefined} onSaved={() => { setIsAddingProfile(false); void refetchProfiles(); }} />}
      <div>
        <label htmlFor="order-address" className="mb-1.5 block text-sm font-medium text-ink">Delivery address</label>
        <Select id="order-address" value={deliveryAddressId} onChange={(e) => setDeliveryAddressId(e.target.value)} disabled={isSubmitting}>
          <option value="">Select an address…</option>
          {addresses.map((address) => <option key={address.id} value={address.id}>{address.label}: {address.formatted_address}, {address.city}</option>)}
        </Select>
        {addresses.length === 0 && !loadError && <p role="status" className="mt-2 text-sm text-ink-soft">No delivery address saved yet. Add a Nigerian delivery address below to continue.</p>}
        <button type="button" onClick={() => setIsAddingAddress(!isAddingAddress)} className="mt-2 text-xs text-brass-deep hover:underline">{isAddingAddress ? "Close address form" : "+ Add a delivery address"}</button>
      </div>
      {isAddingAddress && <DeliveryAddressForm onSaved={(address) => { setAddresses((previous) => [address, ...previous]); setDeliveryAddressId(address.id); setIsAddingAddress(false); }} />}
      {[loadError, designError, measurementError, error].filter(Boolean).map((message, index) => <p key={index} role="alert" className="text-sm text-thread">{message}</p>)}
      {!professionalId && <p role="alert" className="text-sm text-thread">No professional selected. Choose a professional from the directory first.</p>}
      <Button onClick={handleSubmit} isLoading={isSubmitting} disabled={!professional || !selectedDesign || !measurementProfileId || !deliveryAddressId} className="self-start">Continue to checkout</Button>
    </div>
  );
}
