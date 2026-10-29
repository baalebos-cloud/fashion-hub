import { Link } from "react-router-dom";
import { publicRoutes, authRoutes } from "@/config/routes.config";

const LINKS = {
  Platform: [
    { label: "Find a Tailor", to: publicRoutes.findTailor },
    { label: "Find a Designer", to: publicRoutes.findDesigner },
    { label: "Marketplace", to: publicRoutes.vendorMarketplace },
    { label: "How it works", to: publicRoutes.howItWorks },
  ],
  Company: [
    { label: "About", to: publicRoutes.about },
    { label: "Pricing", to: publicRoutes.pricing },
    { label: "Contact", to: publicRoutes.contact },
    { label: "Help", to: publicRoutes.help },
  ],
  Legal: [
    { label: "Terms", to: publicRoutes.terms },
    { label: "Privacy", to: publicRoutes.privacy },
  ],
};

export function Footer() {
  return (
    <footer className="border-t border-line bg-paper">
      <div className="mx-auto max-w-6xl px-6 py-12">
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
          {/* Brand column */}
          <div className="flex flex-col gap-3">
            <Link to={publicRoutes.home} className="font-display text-xl text-ink">
              Fashion Hub
            </Link>
            <p className="text-sm text-ink-soft leading-relaxed">
              Nigeria's marketplace for custom clothing — connecting customers, tailors,
              designers, and vendors.
            </p>
            <div className="mt-2 flex gap-2">
              <Link
                to={authRoutes.signup}
                className="rounded-lg bg-brass px-3 py-1.5 text-xs font-medium text-ink hover:bg-brass-deep"
              >
                Get started
              </Link>
            </div>
          </div>

          {/* Link columns */}
          {Object.entries(LINKS).map(([heading, items]) => (
            <div key={heading} className="flex flex-col gap-3">
              <p className="text-xs font-semibold uppercase tracking-widest text-ink-soft/60">
                {heading}
              </p>
              <ul className="flex flex-col gap-2">
                {items.map((item) => (
                  <li key={item.to}>
                    <Link
                      to={item.to}
                      className="text-sm text-ink-soft transition-colors hover:text-ink"
                    >
                      {item.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-10 flex flex-col items-center justify-between gap-3 border-t border-line pt-6 sm:flex-row">
          <p className="text-xs text-ink-soft">
            © {new Date().getFullYear()} Fashion Hub. All rights reserved.
          </p>
          <p className="text-xs text-ink-soft">Made with care in Nigeria 🇳🇬</p>
        </div>
      </div>
    </footer>
  );
}
