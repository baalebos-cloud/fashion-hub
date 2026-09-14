const STEPS = [
  "Find a tailor or designer near you, or browse by style",
  "Share your measurements and design requirements",
  "Choose a delivery location and pay securely",
  "Your professional accepts, produces, and ships your order",
  "Track delivery in real time, then confirm you've received it",
  "Leave a review once your order is complete",
];

export default function HowItWorks() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-16">
      <h1 className="font-display text-2xl text-ink">How it works</h1>
      <ol className="mt-6 flex flex-col gap-4">
        {STEPS.map((step, i) => (
          <li key={step} className="flex gap-3">
            <span className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-brass text-sm text-ink">{i + 1}</span>
            <span className="text-ink-soft">{step}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
