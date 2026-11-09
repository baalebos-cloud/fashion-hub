import { useEffect, useState, type FormEvent } from "react";
import { payoutsApi, type PayoutAccount } from "@/api/payouts.api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { getDisplayErrorMessage } from "@/lib/utils/errors";

/** Where a seller's payouts go. The bank checks the account and returns its name; changing it needs the
 * seller's password. Payouts only go automatically to an account in the seller's verified name. */
export function PayoutAccountForm({ onChange }: { onChange?: (enabled: boolean) => void }) {
  const [account, setAccount] = useState<PayoutAccount | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [banks, setBanks] = useState<{ code: string; name: string }[]>([]);
  const [bankCode, setBankCode] = useState("");
  const [number, setNumber] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    payoutsApi.account().then((r) => {
      if (!active) return;
      setAccount(r.account); setEditing(!r.account); setLoaded(true); onChange?.(r.payouts_enabled);
    }).catch(() => { if (active) { setLoaded(true); setError("Your payout account couldn't be loaded."); } });
    return () => { active = false; };
  }, [onChange]);

  useEffect(() => {
    if (!editing || banks.length) return;
    payoutsApi.banks().then(setBanks).catch(() => setError("The list of banks couldn't be loaded. Try again shortly."));
  }, [editing, banks.length]);

  async function save(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const saved = await payoutsApi.setAccount({ bank_code: bankCode, account_number: number, password });
      setAccount(saved); setEditing(false); setNumber(""); setPassword("");
    } catch (err) {
      setError(getDisplayErrorMessage(err, "The account couldn't be saved. Check the details and try again."));
    } finally {
      setBusy(false);
    }
  }

  if (!loaded) return null;
  return (
    <Card className="flex flex-col gap-3 p-5">
      <h2 className="font-semibold text-ink">Payout bank account</h2>
      {account && !editing && (
        <>
          <p className="text-sm text-ink">
            {account.bank_name} ••••{account.account_last4} · <span className="font-medium">{account.account_name}</span>
          </p>
          {account.name_matches ? (
            <p className="text-[13px] text-success">Matches your verified name. Payouts are sent here automatically.</p>
          ) : (
            <p className="text-[13px] text-warning">
              This account name doesn't match your verified name, so payouts wait for Tailora to check it.
              Use an account in your own name or your registered business name to be paid faster.
            </p>
          )}
          <Button size="sm" variant="secondary" className="self-start" onClick={() => setEditing(true)}>Change account</Button>
        </>
      )}
      {editing && (
        <form className="flex max-w-sm flex-col gap-3" onSubmit={(e) => void save(e)}>
          <Field label="Bank" htmlFor="payout-bank">
            <select id="payout-bank" value={bankCode} onChange={(e) => setBankCode(e.target.value)} required
              className="min-h-11 rounded-control border border-line-strong bg-surface px-3 text-base text-ink">
              <option value="">Choose your bank</option>
              {banks.map((b) => <option key={b.code} value={b.code}>{b.name}</option>)}
            </select>
          </Field>
          <Field label="Account number" htmlFor="payout-number" help="Your 10-digit NUBAN account number.">
            <Input id="payout-number" inputMode="numeric" autoComplete="off" maxLength={10} value={number}
              onChange={(e) => setNumber(e.target.value.replace(/\D/g, "").slice(0, 10))} />
          </Field>
          <Field label="Your Tailora password" htmlFor="payout-password" help="Needed to add or change where your money goes.">
            <Input id="payout-password" type="password" autoComplete="current-password" value={password}
              onChange={(e) => setPassword(e.target.value)} />
          </Field>
          <div className="flex gap-2">
            <Button type="submit" isLoading={busy} disabled={!bankCode || number.length !== 10 || !password}>Check and save</Button>
            {account && <Button type="button" variant="ghost" onClick={() => { setEditing(false); setError(null); }}>Cancel</Button>}
          </div>
        </form>
      )}
      {error && <p role="alert" className="text-sm text-thread">{error}</p>}
    </Card>
  );
}
