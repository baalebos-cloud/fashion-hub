import { type ReactNode, useEffect } from "react";
import { createPortal } from "react-dom";
import { cn } from "@/lib/utils/cn";

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  className?: string;
}

/** Base modal used by PaymentModal, ConfirmDialog, CancelOrderDialog, etc.
 * Handles Escape-to-close and focus trapping at the container level;
 * individual dialogs only need to supply content. */
export function Modal({ isOpen, onClose, title, children, className }: ModalProps) {
  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return createPortal(
    <div className="fixed inset-0 z-[1000] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-ink/40" onClick={onClose} aria-hidden="true" />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={cn("relative w-full max-w-md rounded-card border border-line bg-paper p-6 shadow-xl", className)}
      >
        {title && <h2 className="mb-4 font-display text-lg text-ink">{title}</h2>}
        {children}
      </div>
    </div>,
    document.body
  );
}
