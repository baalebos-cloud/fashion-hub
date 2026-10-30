import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { publicRoutes, authRoutes } from "@/config/routes.config";

const FEATURES = [
  {
    icon: (
      <svg width="24" height="24" fill="none" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5A2.5 2.5 0 1 1 12 6a2.5 2.5 0 0 1 0 5.5z" fill="currentColor"/>
      </svg>
    ),
    title: "Find your tailor",
    body: "Browse verified professionals near you, filtered by specialty and style.",
  },
  {
    icon: (
      <svg width="24" height="24" fill="none" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M9 11H7v2h2v-2zm4 0h-2v2h2v-2zm4 0h-2v2h2v-2zm2-7h-1V2h-2v2H8V2H6v2H5c-1.11 0-1.99.9-1.99 2L3 20a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6c0-1.1-.89-2-2-2zm0 16H5V9h14v11z" fill="currentColor"/>
      </svg>
    ),
    title: "Order with confidence",
    body: "Submit your measurements, pick a delivery location, and pay securely.",
  },
  {
    icon: (
      <svg width="24" height="24" fill="none" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M20 8h-3V4H3c-1.1 0-2 .9-2 2v11h2a3 3 0 0 0 6 0h6a3 3 0 0 0 6 0h2v-5l-3-4zm-.5 1.5 1.96 2.5H17V9.5h2.5zM6 18a1 1 0 1 1 0-2 1 1 0 0 1 0 2zm13 0a1 1 0 1 1 0-2 1 1 0 0 1 0 2z" fill="currentColor"/>
      </svg>
    ),
    title: "Track every step",
    body: "From production to your doorstep, watch your order move in real time.",
  },
];

const TESTIMONIALS = [
  {
    quote: "My agbada was ready in 5 days and fit perfectly. The tailor communicated every step.",
    name: "Emeka O.",
    role: "Customer, Lagos",
  },
  {
    quote: "I've tripled my client base since joining. The measurement tools save me hours every week.",
    name: "Amara T.",
    role: "Tailor, Abuja",
  },
  {
    quote: "Sourcing ankara fabric used to take days. Now I find verified vendors in minutes.",
    name: "Chisom N.",
    role: "Designer, Port Harcourt",
  },
];

export default function Home() {
  return (
    <div className="flex flex-col">
      {/* Hero */}
      <section className="relative overflow-hidden bg-ink px-4 py-24 text-center sm:py-32">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 opacity-10"
          style={{
            backgroundImage:
              "repeating-linear-gradient(45deg,#ab8a52 0,#ab8a52 1px,transparent 0,transparent 50%)",
            backgroundSize: "24px 24px",
          }}
        />
        <div className="relative mx-auto max-w-3xl">
          <span className="mb-4 inline-block rounded-full border border-brass/40 px-4 py-1 text-xs font-medium tracking-widest text-brass uppercase">
            Nigeria's fashion marketplace
          </span>
          <h1 className="mt-4 font-display text-4xl leading-tight text-paper sm:text-5xl lg:text-6xl">
            Custom clothing,<br />made by people who<br />
            <em className="not-italic text-brass">know their craft.</em>
          </h1>
          <p className="mx-auto mt-6 max-w-xl text-base text-paper/70">
            Find verified tailors and designers near you, order custom pieces with your own
            measurements, and track everything from fitting to doorstep.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link to={publicRoutes.onboarding}>
              <Button size="lg" className="bg-brass text-ink hover:bg-brass-deep">
                Find your perfect tailor
              </Button>
            </Link>
            <Link to={authRoutes.signup}>
              <Button size="lg" variant="secondary" className="border-paper/30 text-paper hover:border-brass hover:text-brass">
                Join as a professional
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="border-t border-line bg-muslin/40 px-4 py-16">
        <div className="mx-auto max-w-4xl">
          <h2 className="mb-10 text-center font-display text-2xl text-ink">How it works</h2>
          <div className="grid gap-8 sm:grid-cols-3">
            {FEATURES.map((f, i) => (
              <div key={f.title} className="flex flex-col gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brass/10 text-brass">
                  {f.icon}
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-display text-3xl text-line">0{i + 1}</span>
                  <h3 className="font-display text-lg text-ink">{f.title}</h3>
                </div>
                <p className="text-sm text-ink-soft">{f.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Social proof */}
      <section className="px-4 py-16">
        <div className="mx-auto max-w-4xl">
          <h2 className="mb-10 text-center font-display text-2xl text-ink">What people are saying</h2>
          <div className="grid gap-5 sm:grid-cols-3">
            {TESTIMONIALS.map((t) => (
              <blockquote
                key={t.name}
                className="flex flex-col gap-4 rounded-card border border-line bg-paper p-5"
              >
                <p className="text-sm leading-relaxed text-ink-soft">"{t.quote}"</p>
                <footer className="mt-auto">
                  <div className="font-medium text-ink">{t.name}</div>
                  <div className="text-xs text-ink-soft">{t.role}</div>
                </footer>
              </blockquote>
            ))}
          </div>
        </div>
      </section>

      {/* CTA banner */}
      <section className="border-t border-line bg-brass px-4 py-14 text-center">
        <h2 className="font-display text-2xl text-ink sm:text-3xl">
          Ready to wear something made for you?
        </h2>
        <p className="mt-3 text-sm text-ink/70">
          Discover skilled fashion professionals and create your next custom outfit with Tailora.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Link to={authRoutes.signup}>
            <Button size="lg" className="bg-ink text-paper hover:bg-ink/90">
              Get started — it's free
            </Button>
          </Link>
          <Link to={publicRoutes.howItWorks}>
            <Button size="lg" variant="ghost" className="text-ink hover:bg-ink/10">
              Learn more
            </Button>
          </Link>
        </div>
      </section>
    </div>
  );
}
