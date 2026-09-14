import { LogoutButton } from "@/components/auth/LogoutButton";

export default function Settings() {
  return (
    <div className="flex max-w-md flex-col gap-8">
      <h1 className="font-display text-xl text-ink">Platform settings</h1>
      <p className="text-sm text-ink-soft">Platform-wide configuration (fee rates, supported currencies, feature flags) goes here as those become configurable server-side.</p>
      <LogoutButton className="self-start" />
    </div>
  );
}
