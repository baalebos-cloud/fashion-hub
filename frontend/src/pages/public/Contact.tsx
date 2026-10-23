import { appConfig } from "@/config/app.config";

export default function Contact() {
  return (
    <div className="mx-auto max-w-lg px-4 py-16">
      <h1 className="font-display text-2xl text-ink">Contact us</h1>
      <p className="mt-2 text-sm text-ink-soft">Email our support team with your question and, if applicable, your order number.</p>
      <a className="mt-6 inline-block underline" href={`mailto:${appConfig.supportEmail}`}>{appConfig.supportEmail}</a>
      <p className="mt-3 text-sm text-ink-soft">Your email application will open. Send your message there to contact us.</p>
    </div>
  );
}
