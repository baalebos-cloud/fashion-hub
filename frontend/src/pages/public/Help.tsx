import { Link } from "react-router-dom";
import { publicRoutes } from "@/config/routes.config";

const FAQS = [
  { q: "How do I find a tailor near me?", a: "Use Find a Tailor and allow location access, or search by name or specialty." },
  { q: "How do I track my order?", a: "Open Orders from your dashboard, select the order, then choose Track." },
  { q: "When can I leave a review?", a: "Once you've confirmed you received your order." },
];

export default function Help() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-16">
      <h1 className="font-display text-2xl text-ink">Help center</h1>
      <div className="mt-6 flex flex-col gap-4">
        {FAQS.map((faq) => (
          <div key={faq.q}>
            <h3 className="font-medium text-ink">{faq.q}</h3>
            <p className="mt-1 text-sm text-ink-soft">{faq.a}</p>
          </div>
        ))}
      </div>
      <p className="mt-8 text-sm text-ink-soft">
        Still stuck? <Link to={publicRoutes.contact} className="text-brass-deep hover:underline">Contact us</Link> or use the Ask Seam assistant once you're signed in.
      </p>
    </div>
  );
}
