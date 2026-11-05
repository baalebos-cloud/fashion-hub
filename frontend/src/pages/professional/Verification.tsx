import { VerificationCenter } from "@/components/verification/VerificationCenter";

export default function Verification() {
  return (
    <div className="mx-auto flex w-full max-w-xl flex-col gap-6">
      <h1 className="font-display text-xl text-ink">Verification</h1>
      <VerificationCenter />
    </div>
  );
}
