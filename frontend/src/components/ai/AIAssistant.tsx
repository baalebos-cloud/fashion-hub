import { createPortal } from "react-dom";
import { AIHelpButton } from "./AIHelpButton";
import { AIChatWindow } from "./AIChatWindow";
import type { UserRole } from "@/types/auth";

export interface AIAssistantProps {
  role: UserRole;
}

/**
 * Mount point for the entire assistant feature. This is the ONE component
 * App.tsx imports — everything else in this folder is an implementation
 * detail of it. Rendering through a portal into document.body means its
 * fixed position is unaffected by any individual page's own layout,
 * overflow, or z-index, which is what makes it genuinely global rather
 * than accidentally clipped by whatever page happens to be active.
 *
 * `role` is passed in from the authenticated user (see App.tsx) purely so
 * AIChatWindow/AIQuickActions/AINavigationGuide can scope their content —
 * it has no bearing on what the assistant is authorized to do, which is
 * enforced entirely server-side (backend/app/integrations/ai/prompts.py)
 * regardless of what this prop says.
 */
export function AIAssistant({ role }: AIAssistantProps) {
  return createPortal(
    <>
      <AIHelpButton />
      <AIChatWindow role={role} />
    </>,
    document.body
  );
}
