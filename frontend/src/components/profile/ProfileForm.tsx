import { useState, type FormEvent } from "react";
import { useUser } from "@/hooks/use-user";
import { validateProfile } from "@/lib/validation/profile";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";

export function ProfileForm() {
  const { user, isSaving, updateProfile } = useUser();
  const { showToast } = useToast();
  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const validationErrors = validateProfile({ fullName });
    if (validationErrors.length > 0) {
      setErrors(Object.fromEntries(validationErrors.map((err) => [err.field, err.message])));
      return;
    }
    setErrors({});
    setFormError(null);
    try {
      await updateProfile({ full_name: fullName });
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
      {formError && <p className="text-sm text-thread">{formError}</p>}
      <Button type="submit" isLoading={isSaving} className="self-start">Save changes</Button>
    </form>
  );
}
