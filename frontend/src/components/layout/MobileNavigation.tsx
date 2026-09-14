import { useState } from "react";
import { Drawer } from "@/components/ui/drawer";
import { Sidebar } from "./Sidebar";
import type { UserRole } from "@/types/auth";

/** Below the lg breakpoint, Sidebar hides (see styles/responsive.css) and
 * this hamburger + drawer takes over, reusing the exact same nav list so
 * the two never drift apart. */
export function MobileNavigation({ role }: { role: UserRole }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="lg:hidden">
      <button
        type="button"
        aria-label="Open menu"
        onClick={() => setIsOpen(true)}
        className="flex h-10 w-10 items-center justify-center rounded-lg text-ink hover:bg-muslin"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
      </button>

      <Drawer isOpen={isOpen} onClose={() => setIsOpen(false)} side="left" title="Menu">
        <Sidebar role={role} />
      </Drawer>
    </div>
  );
}
