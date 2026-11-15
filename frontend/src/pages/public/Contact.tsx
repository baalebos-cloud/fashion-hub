import { Link } from "react-router-dom";
import { LegalPage, Section, SupportEmail } from "@/components/legal/LegalPage";
import { publicRoutes } from "@/config/routes.config";

export default function Contact() {
  return (
    <LegalPage title="Contact us" intro="We're here to help.">
      <Section title="About an order">
        <p>The quickest way is from the order itself: open it in the app and use <span className="font-medium text-ink">Problem with this order?</span> to report what went wrong. Our team reviews it, and the seller isn't paid until we have.</p>
      </Section>
      <Section title="Anything else">
        <p>Email <SupportEmail /> with your question and, if it's about an order, the order number. [Phone or WhatsApp line and support hours.]</p>
        <p>Common questions are answered in the <Link to={publicRoutes.help} className="font-medium text-indigo underline">Help centre</Link>.</p>
      </Section>
      <Section title="Company">
        <p>[Company legal name], RC [number], [registered address].</p>
      </Section>
    </LegalPage>
  );
}
