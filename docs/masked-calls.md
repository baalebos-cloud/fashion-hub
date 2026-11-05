# Masked calls (Africa's Talking)

Customers, tailors/designers, vendors and riders can call each other about an
order without seeing each other's phone number.

## How a call works

1. A user taps **Call** on an order (or **Call rider** on tracking, or **Call
   customer / Call pickup contact** on a rider's trip).
2. `POST /api/v1/calls` checks that both people are on the same open order,
   then asks Africa's Talking to ring the **caller's own phone** from Tailora's
   number.
3. When the caller answers, Africa's Talking calls our webhook and we reply
   with `<Dial>` to the other person, showing Tailora's number as caller ID.
4. If the other person later rings Tailora's number back within
   `VOICE_CALLBACK_WINDOW_HOURS` (default 2), they are routed to whoever
   called them. Anyone else hears a message pointing them to the app.

Who can call whom (only while the order is not completed, cancelled,
rejected or refunded):

| Caller | Can call |
| --- | --- |
| Buyer (customer, or tailor/designer buying materials) | Seller, assigned rider |
| Seller (tailor/designer/vendor) | Buyer, assigned rider |
| Assigned rider (while the delivery is active) | Buyer (the delivery recipient's number), seller |

Phone numbers are looked up at dial time and are never returned by the API
or stored on call records. Calls are not recorded. Each user can start at
most 6 calls per 10 minutes.

## Setup

1. Create an account at <https://africastalking.com>, then an app.
2. Buy a voice number for Nigeria under **Voice → Phone numbers**.
3. Generate a long random secret, for example `openssl rand -hex 24`.
4. In the number's settings, set the **callback URL** to
   `https://<your-railway-api-domain>/api/v1/calls/voice/<that secret>`.
5. Set these variables in Railway:

   ```
   VOICE_PROVIDER=africastalking
   AT_USERNAME=<your app username>
   AT_API_KEY=<your API key>
   AT_VOICE_NUMBER=+234...        # the number from step 2
   AT_ENVIRONMENT=production
   VOICE_WEBHOOK_SECRET=<the secret from step 3>
   ```

6. Users need a phone number on their profile (Settings) to place or receive
   calls. The app explains this when it's missing.

For local development, `VOICE_PROVIDER=sandbox` makes the whole flow work
without placing real calls.
