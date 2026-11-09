import { useEffect, useState } from "react";
import { vendorsApi } from "@/api/vendors.api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { Vendor } from "@/types/vendor";
import { ProfilePhoto } from "@/components/profile/ProfilePhoto";
import { ProfileForm } from "@/components/profile/ProfileForm";
import { useAuthStore } from "@/store/auth.store";

export default function Profile() {
  const [profile, setProfile] = useState<Vendor | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const user = useAuthStore((st) => st.user);
  const refreshUser = useAuthStore((st) => st.refreshUser);
  useEffect(() => {
    let active = true;
    vendorsApi.mine().then((value) => { if (active) setProfile(value); }).catch((err) => { if (active) setError(getDisplayErrorMessage(err)); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);
  async function save() {
    setSaving(true); setError(null);
    try { setProfile(await vendorsApi.create({ business_name: name })); }
    catch (err) { setError(getDisplayErrorMessage(err)); }
    finally { setSaving(false); }
  }
  return <div className="flex max-w-lg flex-col gap-4">
    <h1 className="font-display text-xl">Vendor business profile</h1>
    <div className="flex flex-col gap-1">
      <p className="text-sm font-medium text-ink">Profile photo <span className="text-ink-soft">(required)</span></p>
      <p className="text-xs text-ink-soft">A clear photo of you or your shop front. Customers and riders see it.</p>
      <ProfilePhoto currentUrl={user?.profile_photo_url} onUploaded={() => void refreshUser()} />
    </div>
    {loading ? <p role="status">Loading profile…</p> : profile ? <>
      <p>{profile.business_name}</p><p>{profile.is_verified ? "Verified — active products can appear in the marketplace." : "Awaiting administrator verification. Products stay private until verification."}</p>
    </> : <>
      <label htmlFor="vendor-business-name">Business name</label><Input id="vendor-business-name" value={name} maxLength={255} onChange={(event) => setName(event.target.value)} />
      <Button onClick={() => { void save(); }} disabled={!name.trim()} isLoading={saving}>Create business profile</Button>
    </>}
    {error && <p role="alert">{error}</p>}
    <section aria-labelledby="vendor-your-name" className="flex flex-col gap-3 border-t border-line pt-4">
      <h2 id="vendor-your-name" className="font-display text-lg">Your name and contact</h2>
      <ProfileForm />
    </section>
  </div>;
}
