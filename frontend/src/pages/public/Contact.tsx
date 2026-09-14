import { useState, type FormEvent } from "react";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { appConfig } from "@/config/app.config";

export default function Contact() {
  const [isSent, setIsSent] = useState(false);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setIsSent(true);
  }

  return (
    <div className="mx-auto max-w-lg px-4 py-16">
      <h1 className="font-display text-2xl text-ink">Contact us</h1>
      <p className="mt-2 text-sm text-ink-soft">Or email us directly at {appConfig.supportEmail}.</p>

      {isSent ? (
        <p className="mt-6 text-sm text-ink-soft">Thanks — we'll get back to you shortly.</p>
      ) : (
        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
          <Input placeholder="Your name" required />
          <Input type="email" placeholder="Your email" required />
          <Textarea placeholder="How can we help?" rows={4} required />
          <Button type="submit" className="self-start">Send message</Button>
        </form>
      )}
    </div>
  );
}
