# Email delivery (confirmation and password-reset emails)

## How it works

- Sign-up, "send a new link" and "forgot password" queue an email in the database. The API then
  sends it **straight after responding**, so no background worker is needed. The Celery beat job
  `drain-authentication-email-outbox` retries anything the provider refused.
- Confirmation links are created **when the email is sent**, so a link never arrives already
  expired (they last `EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES`, 24 hours by default).
- If one address keeps failing, its email backs off (2, 4, 8 … minutes, up to 6 hours) and stops
  after 8 attempts. That way it never blocks anyone else's email. Asking for a new link restarts it.
- Signed-in people who haven't confirmed see a banner with **Send a new link**. An expired link
  opens a page where they can request another one.

## Setting it up on Railway (API service)

Email only works with a real provider. **Resend** is already built in:

1. Create a Resend account and verify a domain you own (for example `tailora.ng`) by adding the
   DNS records Resend shows. Resend won't send from an unverified domain, and won't send to
   anyone but you from its test domain.
2. Set:
   ```
   EMAIL_PROVIDER=resend
   EMAIL_API_KEY=<your Resend API key>
   EMAIL_FROM_ADDRESS=Tailora <hello@your-verified-domain>
   FRONTEND_URL=https://<your live site address>
   ```
3. Deploy, then open **Admin → Users**. The *Email confirmation* card says whether email is
   working and, if anything is wrong, which setting to fix.

Any SMTP relay also works instead (`EMAIL_PROVIDER=smtp` with `EMAIL_HOST`, `EMAIL_PORT`,
`EMAIL_USERNAME`, `EMAIL_PASSWORD`, `EMAIL_FROM_ADDRESS`).

## Emailing people who registered earlier

Once the card shows email is working, click **Email everyone who hasn't confirmed**. Each
unconfirmed, active account gets one fresh link; running it again doesn't send duplicates to
people still waiting. The same thing from a Railway shell:

```bash
python scripts/resend_verification_emails.py
```

## Profile photos

Riders, vendors, tailors and designers must add a profile photo before they can submit identity
or business verification, and an admin can't approve them without one. They also can't remove
the photo afterwards (they can replace it). Customers may add or remove a photo freely.
Everyone without a photo sees a reminder on their dashboard.
