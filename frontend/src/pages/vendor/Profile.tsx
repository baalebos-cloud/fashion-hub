import { useEffect, useState } from "react";
import { vendorsApi } from "@/api/vendors.api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { Vendor } from "@/types/vendor";

export default function Profile() {
  const [profile, setProfile] = useState<Vendor | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
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
    {loading ? <p role="status">Loading profile…</p> : profile ? <>
      <p>{profile.business_name}</p><p>{profile.is_verified ? "Verified — active products can appear in the marketplace." : "Awaiting administrator verification. Products stay private until verification."}</p>
    </> : <>
      <label htmlFor="vendor-business-name">Business name</label><Input id="vendor-business-name" value={name} maxLength={255} onChange={(event) => setName(event.target.value)} />
      <Button onClick={() => { void save(); }} disabled={!name.trim()} isLoading={saving}>Create business profile</Button>
    </>}
    {error && <p role="alert">{error}</p>}
  </div>;
}
