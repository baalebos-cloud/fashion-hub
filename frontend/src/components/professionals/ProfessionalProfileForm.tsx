import { useEffect, useState, type FormEvent } from "react";
import { professionalsApi } from "@/api/professionals.api";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";

export function ProfessionalProfileForm() {
  const [name, setName] = useState("");
  const [bio, setBio] = useState("");
  const [years, setYears] = useState(0);
  const [accepting, setAccepting] = useState(true);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    professionalsApi.mine().then((profile) => {
      if (!active || !profile) return;
      setName(profile.business_name ?? ""); setBio(profile.bio ?? "");
      setYears(profile.years_experience ?? 0); setAccepting(profile.accepts_new_orders);
      setStatus(profile.is_verified ? "Verified profile" : "Profile awaiting administrator verification");
    }).catch(() => { if (active) setError("Could not load your business profile. Please reload before editing."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);
  async function save(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError(""); setStatus("");
    try {
      const profile = await professionalsApi.saveProfile({ business_name: name, bio, years_experience: years, accepts_new_orders: accepting });
      setStatus(profile.is_verified ? "Business profile saved." : "Business profile saved. Your order availability follows the marketplace verification policy.");
    } catch { setError("Could not save your business profile. Please try again."); }
    finally { setSaving(false); }
  }
  if (loading) return <p role="status">Loading business profile…</p>;
  return <form onSubmit={save} className="flex flex-col gap-3">
    <h2 className="font-display text-xl">Business profile</h2>
    <label htmlFor="business-name">Business name</label>
    <Input id="business-name" required minLength={2} maxLength={255} value={name} onChange={(e) => setName(e.target.value)} />
    <label htmlFor="business-bio">About your business</label>
    <Textarea id="business-bio" maxLength={4000} value={bio} onChange={(e) => setBio(e.target.value)} />
    <label htmlFor="business-years">Years of experience</label>
    <Input id="business-years" type="number" min={0} max={80} required value={years} onChange={(e) => setYears(Number(e.target.value))} />
    <label><input type="checkbox" checked={accepting} onChange={(e) => setAccepting(e.target.checked)} /> Accepting new orders</label>
    {error && <p role="alert">{error}</p>}
    {status && <p role="status">{status}</p>}
    <Button type="submit" isLoading={saving}>Save business profile</Button>
  </form>;
}
