import { useState, type FormEvent } from "react";
import { useUser } from "@/hooks/use-user";
import { useAuth } from "@/hooks/use-auth";
import { validateProfile } from "@/lib/validation/profile";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";

const WHATSAPP_ROLES = ["tailor", "designer", "vendor", "delivery_partner"];

export function ProfileForm() {
  const { user, isSaving, updateProfile } = useUser();
  const { user: authUser } = useAuth();
  const { showToast } = useToast();
  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [whatsappNumber, setWhatsappNumber] = useState(user?.whatsapp_number ?? "");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);

  const showWhatsappField = authUser ? WHATSAPP_ROLES.includes(authUser.role) : false;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const validationErrors = validateProfile({ fullName, phoneNumber: whatsappNumber || undefined });
    if (validationErrors.length > 0) {
      setErrors(Object.fromEntries(validationErrors.map((err) => [err.field, err.message])));
      return;
    }
    setErrors({});
    setFormError(null);
    try {
      await updateProfile({ full_name: fullName, whatsapp_number: whatsappNumber || undefined });
      showToast("Profile updated.", "success");
    } catch (err) {
      setFormError(getDisplayErrorMessage(err));
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex max-w-sm flex-col gap-4">
      <div>
        <label htmlFor="fullName" className="mb-1.5 block text-sm font-medium text-ink">Full name</label>
        <Input id="fullName" value={fullName} onChange={(e) => setFullName(e.target.value)} error={errors.fullName} />
        {errors.fullName && <p className="mt-1 text-xs text-thread">{errors.fullName}</p>}
      </div>
      <div>
        <label className="mb-1.5 block text-sm font-medium text-ink">Email</label>
        <Input value={user?.email ?? ""} disabled />
      </div>
      {showWhatsappField && (
        <div>
          <label htmlFor="whatsapp" className="mb-1.5 block text-sm font-medium text-ink">WhatsApp number</label>
          <Input
            id="whatsapp"
            value={whatsappNumber}
            onChange={(e) => setWhatsappNumber(e.target.value)}
            placeholder="+234…"
            error={errors.phoneNumber}
          />
          <p className="mt-1 text-xs text-ink-soft">
            Used only to notify you about order updates from vendors/professionals you work with — never shown to customers.
          </p>
          {errors.phoneNumber && <p className="mt-1 text-xs text-thread">{errors.phoneNumber}</p>}
        </div>
      )}
      {formError && <p className="text-sm text-thread">{formError}</p>}
      <Button type="submit" isLoading={isSaving} className="self-start">Save changes</Button>
    </form>
  );
}
