import { BrowserTrackingChoice } from "@/components/recommendations/BrowserTrackingChoice";

export default function Privacy() {
  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4 px-4 py-16 text-sm text-ink-soft">
      <h1 className="font-display text-2xl text-ink">Privacy Policy</h1>
      <p>
        We collect only the information needed to operate the platform: account details, order history, and, where
        relevant to fulfillment, location data. Precise location is only ever shared with the parties involved in
        completing a specific order.
      </p>
      <h2 className="font-display text-lg text-ink">Security records</h2>
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
      <h2 className="font-display text-lg text-ink">Shopping activity and recommendations</h2>
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
    </div>
  );
}
