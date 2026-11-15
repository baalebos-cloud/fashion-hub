import { BrowserTrackingChoice } from "@/components/recommendations/BrowserTrackingChoice";
import { LegalPage, Section, SupportEmail } from "@/components/legal/LegalPage";

/**
 * DRAFT for legal review (Nigeria Data Protection Act 2023). It describes what Tailora actually collects
 * today; bracketed items ([...]) must be filled in by the owner or a lawyer before publication.
 */
export default function Privacy() {
  return (
    <LegalPage title="Privacy Policy" updated="[date]"
      intro="This policy explains what personal information Tailora collects, why, who sees it, how long we keep it, and your rights.">
      <Section title="Who is responsible">
        <p>[Company legal name] (RC [number]), [registered address], is the data controller for Tailora. Contact us about privacy at <SupportEmail />. [Data Protection Officer: name and contact, if required.]</p>
      </Section>
      <Section title="What we collect and why">
        <ul className="list-disc pl-5">
          <li><span className="font-medium text-ink">Account:</span> your name (first, middle and surname), email, phone and WhatsApp number, password (stored only as a secure hash) and profile photo. Needed to run your account and orders.</li>
          <li><span className="font-medium text-ink">Orders:</span> what you order, prices, delivery addresses (including a map pin, LGA, landmark and nearest bus stop) and messages with the people involved.</li>
          <li><span className="font-medium text-ink">Measurements:</span> the measurements you save, and photos of a measurement sheet or a full-length photo if you ask Tailora to read measurements from them.</li>
          <li><span className="font-medium text-ink">Identity checks (tailors, designers, vendors, riders):</span> your NIN (stored encrypted), date of birth, a live selfie and a photo of your ID. We check them with a licensed identity-verification provider against your NIMC record, to stop anyone using someone else's identity. Businesses also give CAC details.</li>
          <li><span className="font-medium text-ink">Payouts (sellers):</span> your bank account details (the account number is stored encrypted) to pay you.</li>
          <li><span className="font-medium text-ink">Location:</span> when you use "Use my current location" to fill an address; and, for riders, their live location only while they choose to share it during a delivery. A rider's shared location is visible to the customer until handover and is not kept afterwards.</li>
          <li><span className="font-medium text-ink">Payments:</span> handled by our payment partners. We receive a payment reference and status, never your full card details.</li>
          <li><span className="font-medium text-ink">AI assistant:</span> what you ask the Tailora assistant and its answers, to help you and improve it.</li>
        </ul>
      </Section>
      <Section title="Who sees your information">
        <ul className="list-disc pl-5">
          <li>The people on your order see only what they need: the seller sees your measurements and order while they work on it; the rider sees the pickup and drop-off details once assigned. Calls go through masked numbers.</li>
          <li>Service providers who work for us: payment partners (Paystack, Interswitch), identity verification ([Prembly]), maps and addresses (Google Maps, OpenStreetMap), AI (Groq, Google), email, and hosting (Railway, Vercel). They may only use your data to provide their service to us. [Confirm the list and any transfers outside Nigeria.]</li>
          <li>Authorities, where the law requires it.</li>
        </ul>
        <p>We never sell your personal information.</p>
      </Section>
      <Section title="Security records and recommendations">
        <h3 className="font-medium text-ink">Security records</h3>
        <p>
          To protect customers' money and accounts and to investigate fraud, we record when you sign in (including failed
          attempts) and when you make changes such as placing or updating an order. Each record holds the time, your
          account, the action, your IP address, a description of your browser and device, and a random device identifier
          stored in your browser. We do not record passwords, codes or message contents.
        </p>
        <p>
          These records are visible only to Tailora's administrator, are used solely for security and fraud prevention,
          and are deleted automatically after 180 days unless they are needed for an open investigation or legal claim.
          We process them on the basis of our legitimate interest in keeping the platform safe, as permitted by the
          Nigeria Data Protection Act 2023. You can ask us what we hold about you through the Contact page.
        </p>
        <h3 className="font-medium text-ink">Shopping activity and recommendations</h3>
        <p>
          To suggest products, designs and tailors you're likely to want, we record what you view, search for, save,
          add to your cart, start booking and buy on Tailora. Each record holds only the item, the kind of action, the
          page it happened on and the time, linked to your account or, if you're signed out, to a random identifier
          stored in your browser. We do not record your IP address, location or messages with it, and it is separate
          from the security records above.
        </p>
        <p>
          This information is used only for recommendations on Tailora, is never sold or shared with advertisers, and is
          deleted automatically after 180 days. We process it on the basis of our legitimate interest in showing you
          relevant items, as permitted by the Nigeria Data Protection Act 2023. Signed-in customers can switch
          personalised recommendations off in Settings, which also deletes what we've recorded. We also respect your
          browser's Global Privacy Control and Do Not Track settings, and you can stop it on this browser here:
        </p>
        <BrowserTrackingChoice />
      </Section>
      <Section title="How long we keep it">
        <ul className="list-disc pl-5">
          <li>Account, measurements and addresses: while your account is open.</li>
          <li>Security records and shopping activity: 180 days.</li>
          <li>Orders, payments, invoices, payouts, refunds and identity-check results: [number] years, as tax and anti-fraud law requires.</li>
        </ul>
        <p>When you delete your account (Settings), your name, email, phone, photo, addresses, measurements, favourites, cart, AI chats and activity are erased. Records we must keep stay, showing "Deleted user" instead of your details.</p>
      </Section>
      <Section title="Your rights">
        <p>Under the Nigeria Data Protection Act 2023 you can ask to see the personal information we hold about you, correct it, delete it, object to or restrict how we use it, receive a copy, and withdraw consent where we rely on it. Email <SupportEmail />; we reply within [30] days. You can also complain to the Nigeria Data Protection Commission.</p>
      </Section>
      <Section title="Keeping it safe">
        <p>We encrypt sensitive data (NINs and bank account numbers), use secure connections, limit staff access (admins sign in with an authenticator app), and keep audit records of sensitive actions.</p>
      </Section>
      <Section title="Children">
        <p>Tailora is for people aged [18] and over.</p>
      </Section>
      <Section title="Changes">
        <p>We'll tell you in the app about important changes to this policy.</p>
      </Section>
    </LegalPage>
  );
}
