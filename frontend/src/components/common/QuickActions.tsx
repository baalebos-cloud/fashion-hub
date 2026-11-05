import { Link } from "react-router-dom";

export interface QuickAction { label: string; description: string; to: string }

/** Large tap targets for the 2-4 most common next steps on a dashboard. */
export function QuickActions({ actions }: { actions: QuickAction[] }) {
  return (
    <nav aria-label="Quick actions" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {actions.map((action) => (
        <Link key={action.to} to={action.to}
          className="group rounded-card border border-line bg-paper p-4 transition-colors hover:border-brass focus-visible:border-brass">
          <span className="flex items-center justify-between text-sm font-medium text-ink">
            {action.label}
            <span aria-hidden="true" className="text-brass transition-transform group-hover:translate-x-0.5">→</span>
          </span>
          <span className="mt-1 block text-xs text-ink-soft">{action.description}</span>
        </Link>
      ))}
    </nav>
  );
}
