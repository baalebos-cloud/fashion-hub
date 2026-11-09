import { useEffect, useState, type FormEvent } from "react";
import { useUser } from "@/hooks/use-user";
import { useAuthStore } from "@/store/auth.store";
import { validateProfile } from "@/lib/validation/profile";
import { nameParts, validateNameParts, type NameErrors, type NameParts } from "@/lib/names";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { NameFields } from "./NameFields";

const WHATSAPP_ROLES = ["tailor", "designer", "vendor", "delivery_partner"];

export function ProfileForm() {
  const { user, isSaving, updateProfile } = useUser();
  const refreshUser = useAuthStore((s) => s.refreshUser);
  const { showToast } = useToast();
  const [name, setName] = useState<NameParts>(() => nameParts(user));
  const [whatsappNumber, setWhatsappNumber] = useState(user?.whatsapp_number ?? "");
  const [nameErrors, setNameErrors] = useState<NameErrors>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);

  // The account may still be loading when the page opens: fill the fields once it arrives,
  // instead of leaving them empty.
  const userId = user?.id;
  useEffect(() => {
    if (!userId) return;
    setName(nameParts(user));
    setWhatsappNumber(user?.whatsapp_number ?? "");
    // Only when a different account loads; not while the person is typing.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  const showWhatsappField = user ? WHATSAPP_ROLES.includes(user.role) : false;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const nErrors = validateNameParts(name);
    const validationErrors = validateProfile({ phoneNumber: whatsappNumber || undefined });
    setNameErrors(nErrors);
    setErrors(Object.fromEntries(validationErrors.map((err) => [err.field, err.message])));
    if (Object.keys(nErrors).length > 0 || validationErrors.length > 0) return;
    setFormError(null);
    try {
      await updateProfile({
        first_name: name.first.trim(),
        middle_name: name.middle.trim(),
        last_name: name.last.trim(),
        whatsapp_number: whatsappNumber || undefined,
      });
      await refreshUser().catch(() => {});
      showToast("Profile updated.", "success");
    } catch (err) {
      setFormError(getDisplayErrorMessage(err));
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex max-w-sm flex-col gap-4" noValidate>
      <NameFields value={name} onChange={setName} errors={nameErrors} idPrefix="profile-name" />
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
      {formError && <p role="alert" className="text-sm text-thread">{formError}</p>}
      <Button type="submit" isLoading={isSaving} className="self-start">Save changes</Button>
    </form>
  );
}
