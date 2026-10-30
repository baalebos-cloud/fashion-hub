import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { professionalsApi } from "@/api/professionals.api";
import { authRoutes, publicRoutes } from "@/config/routes.config";
import type { Professional } from "@/types/professional";

const OPTIONS = [
  ["Custom outfit", "A unique piece made just for me"],
  ["Alterations", "Adjust or repair an existing outfit"],
  ["Traditional wear", "Agbada, aso-ebi, native attire and more"],
  ["Ready-to-wear", "Explore designs and inspiration"],
] as const;
const BUDGETS = ["Under ₦20,000", "₦20,000 – ₦50,000", "₦50,000 – ₦100,000", "Above ₦100,000", "Not sure yet"];
const STYLES = ["Native / Traditional", "Corporate", "Casual", "Wedding / Occasion", "Streetwear", "Other"];

export default function TailoraOnboarding() {
  const [step, setStep] = useState(0);
  const [need, setNeed] = useState("");
  const [style, setStyle] = useState("");
  const [location, setLocation] = useState("");
  const [budget, setBudget] = useState("");
  const [results, setResults] = useState<Professional[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);

  useEffect(() => {
    if (step !== 4) return;
    let active = true;
    setLoading(true);
    setError("");
    // Marketplace results must be genuine verified/active professionals,
    // never generated or invented for a demo.
    professionalsApi.list({ query: location.trim() || undefined, pageSize: 50 })
      .then(async (data) => {
        // A city-only query may find no matches when newly registered studios
        // have not yet provided a business location. Show all registered
        // professionals as a clearly unfiltered fallback.
        if (data.items.length === 0 && location.trim()) {
          return professionalsApi.list({ pageSize: 50 });
        }
        return data;
      })
      .then((data) => { if (active) { setResults(data.items); setSearched(true); } })
      .catch(() => { if (active) setError("We couldn't load available professionals. Please try again."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [step, location]);

  const questions = [
    ["What are you looking for today?", "Tell us what you need, and we'll help you find tailors who are a good match."],
    ["What's your style?", "Choose a style that feels most like you."],
    ["Where should we look?", "Find fashion professionals near you, or search any Nigerian city."],
    ["What is your budget?", "This helps us understand what works for you. Final prices are set by professionals."],
    ["Your Tailora matches", "Explore registered fashion professionals and choose who you want to work with."],
  ];
  const canContinue = [Boolean(need), Boolean(style), Boolean(location.trim()), Boolean(budget), true][step];
  const choiceClass = (selected: boolean) => `rounded-2xl border p-5 text-left transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#ad7847] ${selected ? "border-[#ad7847] bg-[#fbf1e7] shadow-sm" : "border-[#e8dfd6] bg-white hover:border-[#bfa384]"}`;

  return (
    <main className="min-h-[75vh] bg-[#faf7f2] px-4 py-10 text-[#302d2a] sm:py-16">
      <div className="mx-auto max-w-4xl overflow-hidden rounded-[30px] border border-[#e7ddd2] bg-white shadow-[0_18px_70px_rgba(46,31,19,0.07)]">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[#f0e9e1] px-6 py-5 sm:px-10">
          <Link to={publicRoutes.home} className="font-display text-2xl font-semibold tracking-tight text-[#4b2f29]">Tailora<span className="text-[#c58d5d]">.</span></Link>
          <div className="text-right text-[11px] font-semibold uppercase tracking-[0.22em] text-[#997352]">Premium fashion marketplace</div>
        </div>
        <div className="grid gap-0 md:grid-cols-[0.8fr_1.2fr]">
          <aside className="flex flex-col justify-between bg-[#432f2a] px-7 py-10 text-[#fdf7f0] sm:px-10">
            <div>
              <p className="mb-5 text-xs font-medium uppercase tracking-[0.22em] text-[#e0b793]">Personal style, perfected</p>
              <h1 className="font-display text-3xl leading-tight sm:text-4xl">Let's find the right tailor for you.</h1>
              <p className="mt-5 text-sm leading-7 text-[#e7d9ce]">Discover verified fashion professionals, create an order, and pay securely when you're ready.</p>
            </div>
            <div className="mt-12">
              <p className="mb-3 text-xs uppercase tracking-[0.2em] text-[#d7b99f]">Your journey</p>
              <div className="flex gap-2" aria-label={`Step ${step + 1} of 5`}>{questions.map((_, i) => <span key={i} className={`h-1.5 flex-1 rounded-full ${i <= step ? "bg-[#eab88e]" : "bg-[#74564c]"}`} />)}</div>
              <p className="mt-3 text-sm text-[#f4e7da]">{String(step + 1).padStart(2, "0")} / 05</p>
            </div>
          </aside>
          <section className="flex min-h-[510px] flex-col px-6 py-10 sm:px-12">
            <span className="text-xs font-bold uppercase tracking-[0.18em] text-[#aa7b57]">{step === 4 ? "Discover professionals" : "Your preferences"}</span>
            <h2 className="mt-4 font-display text-3xl leading-tight sm:text-4xl">{questions[step][0]}</h2>
            <p className="mt-3 max-w-md text-sm leading-7 text-[#786e66]">{questions[step][1]}</p>
            <div className="mt-8 flex-1">
              {step === 0 && <div className="grid gap-3 sm:grid-cols-2">{OPTIONS.map(([label, description]) => <button type="button" key={label} aria-pressed={need === label} className={choiceClass(need === label)} onClick={() => setNeed(label)}><span className="block font-semibold">{label}</span><span className="mt-2 block text-xs leading-5 text-[#7c7168]">{description}</span></button>)}</div>}
              {step === 1 && <div className="grid gap-3 sm:grid-cols-2">{STYLES.map((option) => <button type="button" key={option} aria-pressed={style === option} className={choiceClass(style === option)} onClick={() => setStyle(option)}>{option}</button>)}</div>}
              {step === 2 && <div><label htmlFor="tailora-city" className="mb-2 block text-sm font-medium">City, state or neighbourhood</label><input id="tailora-city" value={location} onChange={(e) => setLocation(e.target.value)} placeholder="e.g. Ado-Ekiti, Lagos, Abuja" maxLength={100} className="w-full rounded-xl border border-[#dcccbf] px-4 py-3 text-base outline-none focus:border-[#a77551]" /><p className="mt-3 text-xs leading-5 text-[#83786f]">We'll search verified professionals by their listed business location.</p></div>}
              {step === 3 && <div className="grid gap-3">{BUDGETS.map(option => <button type="button" key={option} aria-pressed={budget === option} className={choiceClass(budget === option)} onClick={() => setBudget(option)}>{option}</button>)}</div>}
              {step === 4 && <div aria-live="polite">{loading && <p className="text-[#786e66]">Finding verified professionals…</p>}{error && <p role="alert" className="text-red-700">{error}</p>}{searched && !loading && results.length === 0 && <div className="rounded-2xl border border-[#e8dfd6] p-6"><p className="font-semibold">No registered professionals found yet.</p><p className="mt-2 text-sm text-[#786e66]">Try another city or browse all registered professionals.</p><button type="button" className="mt-4 text-sm font-semibold underline" onClick={() => {setLocation("");setSearched(false);}}>Search all locations</button></div>}{!loading && results.length > 0 && <div className="grid gap-3">{results.map((p) => <Link key={p.id} to={publicRoutes.professionalProfile(p.id)} className="rounded-xl border border-[#e8dfd6] p-4 transition hover:border-[#a77551]"><strong className="block">{p.business_name || "Fashion professional"}</strong><span className="mt-1 block text-sm capitalize text-[#786e66]">{p.professional_type} · {p.is_verified ? "Verified profile" : "Verification pending"}</span><span className="mt-2 block text-sm font-semibold text-[#9b6644]">View profile and request an order →</span></Link>)}</div>}</div>}
            </div>
            <div className="mt-10 flex items-center justify-between gap-3 border-t border-[#eee4dc] pt-6">
              <button type="button" className="rounded-full px-5 py-3 text-sm font-medium text-[#695c50] hover:bg-[#f8f1eb] disabled:opacity-40" disabled={step === 0} onClick={() => setStep(s => Math.max(0, s - 1))}>← Back</button>
              {step < 4 ? <button type="button" disabled={!canContinue} onClick={() => setStep(s => s + 1)} className="rounded-full bg-[#432f2a] px-7 py-3 text-sm font-semibold text-white hover:bg-[#624439] disabled:cursor-not-allowed disabled:opacity-40">Continue →</button> : <Link to={authRoutes.signup} className="rounded-full bg-[#432f2a] px-6 py-3 text-sm font-semibold text-white hover:bg-[#624439]">Create an account</Link>}
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
