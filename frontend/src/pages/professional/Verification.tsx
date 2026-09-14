import { useAuth } from "@/hooks/use-auth";
import { KYCForm } from "@/components/verification/KYCForm";
import { KYBForm } from "@/components/verification/KYBForm";

export default function Verification() {
  const { user } = useAuth();

  return (
    <div className="flex max-w-sm flex-col gap-8">
      <h1 className="font-display text-xl text-ink">Verification</h1>
      <div>
        <h2 className="mb-3 text-sm font-medium text-ink-soft">Identity (KYC)</h2>
        <KYCForm />
      </div>
      {user?.role === "tailor" && (
        <div>
          <h2 className="mb-3 text-sm font-medium text-ink-soft">Business (KYB) — optional</h2>
          <KYBForm />
        </div>
      )}
    </div>
  );
}
