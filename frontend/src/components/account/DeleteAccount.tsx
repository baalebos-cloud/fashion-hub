import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { usersApi } from "@/api/users.api";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { useToast } from "@/components/ui/toast";
import { useAuth } from "@/hooks/use-auth";
import { getDisplayErrorMessage } from "@/lib/utils/errors";

/**
 * Settings → Delete account (required by the App Store and Google Play).
 * First checks nothing is still in progress (open orders, deliveries, payouts, refunds), then asks
 * for the password. The backend decides what is erased and what is kept.
 */
export function DeleteAccount() {
  const { logOut } = useAuth();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [open, setOpen] = useState(false);
  const [checking, setChecking] = useState(false);
  const [blockers, setBlockers] = useState<string[] | null>(null);
  const [password, setPassword] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function start() {
    setChecking(true);
    setError(null);
    setPassword("");
    try {
      const status = await usersApi.deletionStatus();
      setBlockers(status.blockers);
      setOpen(true);
    } catch (err) {
      setError(getDisplayErrorMessage(err, "Couldn't check your account. Try again."));
    } finally {
      setChecking(false);
    }
  }

  function close() {
    if (deleting) return;
    setOpen(false);
    setError(null);
  }

  async function confirm() {
    setDeleting(true);
    setError(null);
    try {
      await usersApi.deleteAccount(password);
    } catch (err) {
      setError(getDisplayErrorMessage(err, "Couldn't delete your account. Try again."));
      setDeleting(false);
      return;
    }
    await logOut().catch(() => {});
    showToast("Your account has been deleted.", "success");
    navigate("/", { replace: true });
  }

  const canDelete = blockers !== null && blockers.length === 0;

  return (
    <section aria-labelledby="delete-account-heading" className="flex flex-col gap-2 border-t border-line pt-6">
      <h2 id="delete-account-heading" className="text-sm font-medium text-ink-soft">Delete account</h2>
      <p className="text-xs text-ink-soft">
        Permanently deletes your account and personal details. Records we must keep by law, such as
        orders, payments and invoices, stay without your name or contact details.
      </p>
      {!open && error && <p role="alert" className="text-xs text-thread">{error}</p>}
      <Button variant="danger" size="sm" className="self-start" isLoading={checking} onClick={() => void start()}>
        Delete account
      </Button>

      <Modal isOpen={open} onClose={close} title={canDelete ? "Delete your account?" : "You can't delete your account yet"}>
        {canDelete ? (
          <form className="flex flex-col gap-4" onSubmit={(e) => { e.preventDefault(); void confirm(); }}>
            <div className="text-sm text-ink">
              <p>This can't be undone. We will:</p>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-ink-soft">
                <li>sign you out on every device and stop notifications;</li>
                <li>remove your name, email, phone number and photo;</li>
                <li>erase your addresses, measurements, favourites, cart and chats with the assistant;</li>
                <li>take down any listings, designs or products you offer.</li>
              </ul>
              <p className="mt-2 text-ink-soft">
                Past orders, payments and invoices are kept for legal reasons, shown as "Deleted user".
              </p>
            </div>
            <Field label="Enter your password to confirm" htmlFor="delete-account-password" error={error ?? undefined}>
              <Input id="delete-account-password" type="password" autoComplete="current-password" value={password}
                onChange={(e) => setPassword(e.target.value)} aria-describedby={error ? "delete-account-password-hint" : undefined}
                disabled={deleting} />
            </Field>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="ghost" onClick={close} disabled={deleting}>Keep my account</Button>
              <Button type="submit" variant="danger" isLoading={deleting} disabled={!password}>Delete my account</Button>
            </div>
          </form>
        ) : (
          <div className="flex flex-col gap-4">
            <p className="text-sm text-ink">Some things still need to finish first:</p>
            <ul className="list-disc space-y-1 pl-5 text-sm text-ink-soft">
              {(blockers ?? []).map((reason) => <li key={reason}>{reason}</li>)}
            </ul>
            <div className="flex justify-end">
              <Button type="button" variant="secondary" onClick={close}>OK</Button>
            </div>
          </div>
        )}
      </Modal>
    </section>
  );
}
