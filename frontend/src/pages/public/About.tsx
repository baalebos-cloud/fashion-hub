import { Link } from "react-router-dom";
import { LegalPage, Section } from "@/components/legal/LegalPage";
import { publicRoutes } from "@/config/routes.config";

export default function About() {
  return (
    <LegalPage title="About Tailora"
      intro="Custom clothing, made by people who know their craft. Tailora brings everyone who makes a Nigerian outfit happen into one app.">
      <Section title="What we do">
        <p>Getting clothes made usually means phone calls, lost measurements and paying upfront on trust. On Tailora, customers find verified tailors and designers near them, save their measurements once, order with a design picture, and follow the outfit from the workshop to their door. Tailors buy fabrics from vendors in the same app, and delivery partners carry orders across the city.</p>
      </Section>
      <Section title="Built on trust">
        <ul className="list-disc pl-5">
          <li>Every tailor, designer, vendor and rider verifies their NIN with a live selfie matched to their government photo, plus an ID check. Businesses can also verify their CAC registration.</li>
          <li>Your payment is held safely and the seller is paid only after you confirm you received your order.</li>
          <li>If something goes wrong, you can report it from the order and our team reviews it.</li>
        </ul>
      </Section>
      <Section title="Who it's for">
        <p>Customers who want clothes made to fit; tailors and designers who want more customers and less admin; fabric and accessory vendors; and delivery partners who want steady jobs.</p>
        <p><Link to={publicRoutes.howItWorks} className="font-medium text-indigo underline">See how it works</Link></p>
      </Section>
      <Section title="The company">
        <p>Tailora is operated by [Company legal name], RC [number], [city], Nigeria.</p>
      </Section>
    </LegalPage>
  );
}
