import type { UserRole } from "@/types/auth";

/**
 * Static, per-role suggestions shown before the first message. Kept in
 * sync with the backend's ROLE_APP_MAP
 * (backend/app/integrations/ai/navigation_agent.py) by convention: when a
 * new page/route ships, update both so the assistant is never suggested
 * a question about a screen the person's role can't actually reach.
 */
const QUICK_PROMPTS: Record<UserRole, string[]> = {
  customer: ["Where can I track my order?", "How do I find a tailor near me?", "Where is my invoice?"],
  tailor: ["How do I accept an order?", "Where do I buy materials from a vendor?", "How does verification work?"],
  designer: ["How do I upload my portfolio?", "Where do I manage incoming orders?"],
  vendor: ["How do I add a new product?", "Where do I see incoming orders?"],
  delivery_partner: ["How do I accept a delivery request?", "Where do I update my availability?"],
  admin: ["Where do I review a pending KYC submission?", "How do I see the audit log?"],
};

export function AIQuickActions({ role, onSelect }: { role: UserRole; onSelect: (prompt: string) => void }) {
  const prompts = QUICK_PROMPTS[role] ?? QUICK_PROMPTS.customer;

  return (
    <div className="mt-4 flex flex-wrap gap-2">
      {prompts.map((prompt) => (
        <button
          key={prompt}
          type="button"
          onClick={() => onSelect(prompt)}
          className="rounded-full border border-line bg-paper px-3 py-1.5 text-xs font-medium text-ink transition-colors hover:border-brass hover:bg-white"
        >
          {prompt}
        </button>
      ))}
    </div>
  );
}
