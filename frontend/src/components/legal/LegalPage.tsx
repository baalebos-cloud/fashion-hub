import type { ReactNode } from "react";
import { appConfig } from "@/config/app.config";

/** Layout for the public information pages (Terms, Privacy, About, Pricing, Contact). */
export function LegalPage({ title, updated, intro, children }: { title: string; updated?: string; intro?: ReactNode; children: ReactNode }) {
  return (
    <article className="mx-auto flex max-w-2xl flex-col gap-4 px-4 py-16 text-sm leading-relaxed text-ink-soft">
      <header className="flex flex-col gap-2">
        <h1 className="font-display text-2xl text-ink">{title}</h1>
        {updated && <p className="text-xs">Last updated: {updated}</p>}
        {intro && <p className="text-base text-ink">{intro}</p>}
      </header>
      {children}
    </article>
  );
}

export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-2">
      <h2 className="mt-2 font-display text-lg text-ink">{title}</h2>
      {children}
    </section>
  );
}

/** The support inbox as a link, or a pointer to the Contact page while none is configured. */
export function SupportEmail() {
  return appConfig.supportEmail
    ? <a className="font-medium text-indigo underline" href={`mailto:${appConfig.supportEmail}`}>{appConfig.supportEmail}</a>
    : <span>our support team (see the Contact page)</span>;
}
