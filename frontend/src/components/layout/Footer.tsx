import { Link } from "react-router-dom";
import { publicRoutes } from "@/config/routes.config";

/** Public-site footer only — authenticated dashboard layouts intentionally
 * omit this in favor of maximizing working area (see DashboardLayout.tsx). */
export function Footer() {
  return (
    <footer className="border-t border-line bg-paper px-6 py-8 text-sm text-ink-soft">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <span>© {new Date().getFullYear()} Fashion Hub</span>
        <nav className="flex gap-5">
          <Link to={publicRoutes.about} className="hover:text-ink">About</Link>
          <Link to={publicRoutes.help} className="hover:text-ink">Help</Link>
          <Link to={publicRoutes.terms} className="hover:text-ink">Terms</Link>
          <Link to={publicRoutes.privacy} className="hover:text-ink">Privacy</Link>
        </nav>
      </div>
    </footer>
  );
}
