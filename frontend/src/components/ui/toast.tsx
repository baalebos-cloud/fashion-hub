import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { cn } from "@/lib/utils/cn";

interface Toast {
  id: string;
  message: string;
  tone: "success" | "error" | "info";
}

interface ToastContextValue {
  showToast: (message: string, tone?: Toast["tone"]) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const TONE_CLASSES: Record<Toast["tone"], string> = {
  success: "bg-ink text-paper",
  error: "bg-thread text-paper",
  info: "bg-ink text-paper",
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(0);
  const timers = useRef(new Set<ReturnType<typeof setTimeout>>());

  useEffect(() => {
    const pending = timers.current;
    return () => {
      for (const timer of pending) clearTimeout(timer);
      pending.clear();
    };
  }, []);

  const showToast = useCallback((message: string, tone: Toast["tone"] = "info") => {
    // A sequence avoids duplicate React keys from two notifications in the same ms.
    const id = "toast-" + ++nextId.current;
    setToasts((previous) => [...previous, { id, message, tone }]);
    const timer = setTimeout(() => {
      setToasts((previous) => previous.filter((toast) => toast.id !== id));
      timers.current.delete(timer);
    }, 4000);
    timers.current.add(timer);
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {createPortal(
        <div
          role="status"
          aria-live="polite"
          aria-atomic="false"
          className="fixed bottom-6 left-1/2 z-[2000] flex -translate-x-1/2 flex-col gap-2"
        >
          {toasts.map((toast) => (
            <div key={toast.id} className={cn("rounded-lg px-4 py-2.5 text-sm shadow-lg", TONE_CLASSES[toast.tone])}>
              {toast.message}
            </div>
          ))}
        </div>,
        document.body,
      )}
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within a <ToastProvider>.");
  return ctx;
}
