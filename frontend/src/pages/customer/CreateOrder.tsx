import { useEffect, useRef, useState } from "react";
import { trackBookingStarted, trackView } from "@/lib/tracking/interactions";
import { Link, useParams, useNavigate } from "react-router-dom";
import { useMeasurements } from "@/hooks/use-measurements";
import { useDesigns } from "@/hooks/use-designs";
import { useToast } from "@/components/ui/toast";
import { MeasurementForm } from "@/components/measurements/MeasurementForm";
import { DeliveryAddressForm } from "@/components/checkout/DeliveryAddressForm";
import { Select } from "@/components/ui/select";
import { Field } from "@/components/ui/field";
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

  useEffect(() => { if (professional) trackBookingStarted(professional.id); }, [professional]);
  useEffect(() => { if (selectedDesignId) trackView("design", selectedDesignId, "booking"); }, [selectedDesignId]);

  useEffect(() => {
    let active = true;
    setProfessional(null);
    setSelectedDesignId("");
    setLoadError(null);
    if (professionalId) {
      Promise.all([professionalsApi.getById(professionalId), addressesApi.list()])
        .then(([profile, saved]) => {
          if (active) { setProfessional(profile); setAddresses(saved); setDeliveryAddressId(saved.find((a) => a.is_default)?.id ?? ""); }
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
  const selectedProfile = profiles.find((profile) => profile.id === measurementProfileId);
  const requiredFields = selectedDesign?.required_measurement_fields ?? [];
  // Only checkable when the saved profile came back with its values.
  const missingFields = selectedProfile?.fields
    ? requiredFields.filter((name) => !selectedProfile.fields?.some((field) => field.field_name === name && field.value > 0))
    : [];
  const pretty = (name: string) => name.replace(/_/g, " ");
  const canContinue = Boolean(professional && selectedDesign && measurementProfileId && deliveryAddressId) && missingFields.length === 0;
  const selectedAddress = addresses.find((address) => address.id === deliveryAddressId);

  return (
    <div className="mx-auto grid max-w-5xl gap-6 lg:grid-cols-12 lg:items-start">
      <div className="flex flex-col gap-6 lg:col-span-7">
        <div className="flex flex-col gap-1">
          <h1 className="font-display text-3xl text-ink">Place your order</h1>
          <p className="text-sm text-ink-soft">
            {professional ? <>With <span className="font-semibold text-ink">{professional.business_name ?? "this professional"}</span>. </> : null}
            Checkout is available for priced designs delivered within Nigeria.
          </p>
        </div>

        <section aria-labelledby="step-design" className="flex flex-col gap-3 rounded-card border border-line bg-surface p-5">
          <h2 id="step-design" className="flex items-center gap-2 font-semibold text-ink"><span className="font-mono text-sm text-indigo">1</span> Choose a design</h2>
          <Field label="Published design" htmlFor="order-design" help="Custom work needs an agreed quote and isn't available through this checkout yet.">
            <Select id="order-design" value={selectedDesignId} onChange={(e) => setSelectedDesignId(e.target.value)} disabled={isLoading || isSubmitting} aria-describedby="order-design-hint">
              <option value="">Select a design…</option>
              {designs.map((design) => <option key={design.id} value={design.id}>{design.title} — {formatCurrency(design.base_price, design.currency)}</option>)}
            </Select>
          </Field>
          {!isLoading && !designError && designs.length === 0 && <p role="status" className="text-sm text-ink-soft">This professional has no published designs available for checkout. <Link className="font-semibold text-indigo underline" to={customerRoutes.findProfessionals}>Browse other professionals</Link> or ask them to publish a priced design first.</p>}
        </section>

        <section aria-labelledby="step-measurements" className="flex flex-col gap-3 rounded-card border border-line bg-surface p-5">
          <h2 id="step-measurements" className="flex items-center gap-2 font-semibold text-ink"><span className="font-mono text-sm text-indigo">2</span> Your measurements</h2>
          <Field label="Measurement profile" htmlFor="order-measurements"
            help={requiredFields.length ? `This design needs: ${requiredFields.map(pretty).join(", ")}.` : undefined}>
            <Select id="order-measurements" value={measurementProfileId} onChange={(e) => setMeasurementProfileId(e.target.value)} disabled={isSubmitting} aria-describedby="order-measurements-hint">
              <option value="">Select a profile…</option>
              {profiles.map((profile) => <option key={profile.id} value={profile.id}>{profile.label}</option>)}
            </Select>
          </Field>
          {profiles.length === 0 && !measurementError && <p role="status" className="text-sm text-ink-soft">No measurements saved yet. Add a profile below, then select it.</p>}
          {missingFields.length > 0 && (
            <div role="alert" className="flex flex-col gap-1 rounded-control bg-danger-wash p-3 text-sm text-thread">
              <span className="font-semibold">Add {missingFields.map(pretty).join(", ")} to continue</span>
              <span>"{selectedProfile?.label}" doesn't have {missingFields.length === 1 ? "this measurement" : "these measurements"} yet. Add a new profile with {missingFields.length === 1 ? "it" : "them"} below; your other choices are kept.</span>
            </div>
          )}
          <Button type="button" variant="ghost" size="sm" className="self-start" onClick={() => setIsAddingProfile(!isAddingProfile)}>
            {isAddingProfile ? "Close measurement form" : "+ Add a measurement profile"}
          </Button>
          {isAddingProfile && <MeasurementForm key={selectedDesignId} requiredFields={selectedDesign?.required_measurement_fields ?? undefined} onSaved={() => { setIsAddingProfile(false); void refetchProfiles(); }} />}
        </section>

        <section aria-labelledby="step-delivery" className="flex flex-col gap-3 rounded-card border border-line bg-surface p-5">
          <h2 id="step-delivery" className="flex items-center gap-2 font-semibold text-ink"><span className="font-mono text-sm text-indigo">3</span> Delivery address</h2>
          <Field label="Delivery address" htmlFor="order-address">
            <Select id="order-address" value={deliveryAddressId} onChange={(e) => setDeliveryAddressId(e.target.value)} disabled={isSubmitting}>
              <option value="">Select an address…</option>
              {addresses.map((address) => <option key={address.id} value={address.id}>{address.label}: {address.formatted_address}, {address.city}</option>)}
            </Select>
          </Field>
          {addresses.length === 0 && !loadError && <p role="status" className="text-sm text-ink-soft">No delivery address saved yet. Add a Nigerian delivery address below to continue.</p>}
          <Button type="button" variant="ghost" size="sm" className="self-start" onClick={() => setIsAddingAddress(!isAddingAddress)}>
            {isAddingAddress ? "Close address form" : "+ Add a delivery address"}
          </Button>
          {isAddingAddress && <DeliveryAddressForm onSaved={(address) => { setAddresses((previous) => [address, ...previous]); setDeliveryAddressId(address.id); setIsAddingAddress(false); }} />}
        </section>
      </div>

      <aside aria-label="Order summary" className="flex flex-col gap-3 rounded-card border border-line bg-surface p-5 lg:sticky lg:top-6 lg:col-span-5">
        <h2 className="font-semibold text-ink">Summary</h2>
        <dl className="flex flex-col gap-2 text-sm">
          <div className="flex justify-between gap-3"><dt className="text-ink-soft">Design</dt><dd className="text-right font-semibold text-ink">{selectedDesign?.title ?? "Not chosen"}</dd></div>
          <div className="flex justify-between gap-3"><dt className="text-ink-soft">Measurements</dt><dd className="text-right text-ink">{selectedProfile?.label ?? "Not chosen"}</dd></div>
          <div className="flex justify-between gap-3"><dt className="text-ink-soft">Deliver to</dt><dd className="text-right text-ink">{selectedAddress ? `${selectedAddress.label}, ${selectedAddress.city}` : "Not chosen"}</dd></div>
          <div className="flex justify-between gap-3 border-t border-line pt-2 text-base"><dt className="text-ink">Tailor's price</dt><dd className="font-mono font-semibold text-ink">{selectedDesign ? formatCurrency(selectedDesign.base_price, selectedDesign.currency) : "—"}</dd></div>
        </dl>
        <p className="text-[13px] text-ink-soft">The saved order shows the final total, including delivery, before you pay on the next page.</p>
        {[loadError, designError, measurementError, error].filter(Boolean).map((message, index) => <p key={index} role="alert" className="text-sm text-thread">{message}</p>)}
        {!professionalId && <p role="alert" className="text-sm text-thread">No professional selected. Choose a professional from the directory first.</p>}
        <Button onClick={handleSubmit} isLoading={isSubmitting} disabled={!canContinue} className="w-full">Continue to checkout</Button>
        {!canContinue && !isSubmitting && (
          <p className="text-center text-[13px] text-ink-soft">
            {missingFields.length > 0 ? "Add the missing measurements to continue." : "Choose a design, measurements and an address to continue."}
          </p>
        )}
      </aside>
    </div>
  );
}
