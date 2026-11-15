import { LegalPage, Section } from "@/components/legal/LegalPage";

/** Reflects the platform's current settings (PLATFORM_COMMISSION_RATE = 15%). Update both together. */
export default function Pricing() {
  return (
    <LegalPage title="Pricing" intro="Tailora is free to join and free to browse. Here's who pays what.">
      <Section title="Customers">
        <ul className="list-disc pl-5">
          <li>You pay the price the tailor, designer or vendor sets, plus the delivery fee for your order. Both are shown before you pay.</li>
          <li>No subscription and no extra Tailora charge on your order.</li>
          <li>Your payment is held until you confirm you received the order. If something goes wrong, report it from the order page.</li>
        </ul>
      </Section>
      <Section title="Tailors, designers and vendors">
        <ul className="list-disc pl-5">
          <li>Listing your services, designs or products is free.</li>
          <li>Tailora keeps a 15% commission on each completed order. You receive the rest in your bank account after the customer confirms they received it.</li>
          <li>Payment processing is included in the commission.</li>
        </ul>
      </Section>
      <Section title="Delivery partners">
        <p>You earn the fare agreed for each job: accept the suggested fare or offer your own. Your earnings are shown in the app.</p>
      </Section>
    </LegalPage>
  );
}
