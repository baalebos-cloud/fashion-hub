import { LegalPage, Section, SupportEmail } from "@/components/legal/LegalPage";

/**
 * DRAFT for legal review. It describes how Tailora works today; bracketed items ([...]) must be filled
 * in by the owner or a lawyer before this is published.
 */
export default function Terms() {
  return (
    <LegalPage title="Terms of Service" updated="[date]"
      intro="These terms explain how Tailora works and what we expect from everyone who uses it. Please read them before you create an account.">
      <Section title="1. Who we are">
        <p>Tailora is operated by [Company legal name], a company registered in Nigeria (RC [number]), with its office at [registered address]. "Tailora", "we" and "us" mean that company.</p>
      </Section>
      <Section title="2. What Tailora is">
        <p>Tailora is a marketplace. It connects customers with tailors and fashion designers who make clothes, with vendors who sell fabrics and accessories, and with delivery partners who carry orders. The tailor, designer or vendor you order from makes or sells the item; Tailora runs the platform, takes payments and pays sellers.</p>
      </Section>
      <Section title="3. Your account">
        <ul className="list-disc pl-5">
          <li>You must be at least [18] years old and give true, current information, including your name exactly as on your NIN.</li>
          <li>Keep your password and authenticator codes private. You are responsible for activity on your account.</li>
          <li>Tailors, designers, vendors and delivery partners must verify their identity (NIN, a live selfie and an ID document) and, where asked, their business (CAC) before they can take orders or jobs. We may refuse or remove verification if the details don't match.</li>
        </ul>
      </Section>
      <Section title="4. Orders and measurements">
        <ul className="list-disc pl-5">
          <li>A custom order is made to the measurements you provide. Please check them carefully. Measurements Tailora reads from a photo or a written sheet are estimates for you to confirm.</li>
          <li>Prices are set by the seller and shown before you pay. Delivery fees are shown separately.</li>
          <li>A seller may decline an order. If they do, or if an order is cancelled before work starts, you are refunded under section 6.</li>
        </ul>
      </Section>
      <Section title="5. Payments and payouts">
        <ul className="list-disc pl-5">
          <li>Payments are processed by our payment partners (such as Paystack and Interswitch). Tailora never sees or stores your full card details.</li>
          <li>We hold the payment while your order is made and delivered. The seller is paid after you confirm you received it, less Tailora's commission (see Pricing).</li>
          <li>A payout may be held while a refund, a delivery problem or a dispute on the order is open.</li>
        </ul>
      </Section>
      <Section title="6. Problems, disputes and refunds">
        <ul className="list-disc pl-5">
          <li>If something is wrong with a paid order (not delivered, wrong size, wrong item, damaged or poor quality), report it from the order page. The seller is told and isn't paid for that order until we've reviewed it.</li>
          <li>We review both sides and decide on a remake or alteration, a full or partial refund, or no action, and explain the decision to both of you.</li>
          <li>Refunds go back to the original payment method. How long that takes depends on your bank and our payment partner.</li>
          <li>Please report problems within [7] days of delivery.</li>
        </ul>
      </Section>
      <Section title="7. Delivery">
        <p>Delivery partners collect and deliver orders. A one-time code confirms each pickup and handover, so only give your handover code to the rider once you have the package. While a rider is delivering your order they may share their location with you; it is shown only until handover.</p>
      </Section>
      <Section title="8. Things you must not do">
        <ul className="list-disc pl-5">
          <li>Use someone else's identity, NIN, photo or account.</li>
          <li>Take payment outside Tailora for an order arranged on Tailora, or ask others to.</li>
          <li>List counterfeit, unsafe or illegal goods, or post content that is abusive, misleading or infringes others' rights.</li>
          <li>Interfere with the platform, other users, or our security.</li>
        </ul>
        <p>We may suspend or close accounts that break these terms.</p>
      </Section>
      <Section title="9. The Tailora assistant">
        <p>Tailora's AI assistant gives guidance and may occasionally be wrong. It does not book jobs or take payments on your behalf.</p>
      </Section>
      <Section title="10. Our responsibility">
        <p>[Limitation of liability, warranties and indemnities: to be written by your lawyer.]</p>
      </Section>
      <Section title="11. Closing your account">
        <p>You can delete your account in Settings once nothing involving money or another person is still in progress. Records we must keep by law (orders, payments, invoices) are kept without your personal details; see the Privacy Policy.</p>
      </Section>
      <Section title="12. Changes and governing law">
        <p>We may update these terms and will tell you about important changes in the app. These terms are governed by the laws of the Federal Republic of Nigeria, and disputes go to the courts of [Lagos State].</p>
      </Section>
      <Section title="13. Contact">
        <p>Questions about these terms: email <SupportEmail />.</p>
      </Section>
    </LegalPage>
  );
}
