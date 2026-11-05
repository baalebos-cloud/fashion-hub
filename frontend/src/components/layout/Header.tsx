import { useState } from "react";
import { Link, NavLink } from "react-router-dom";
import { useAuth } from "@/hooks/use-auth";
import { useNotifications } from "@/hooks/use-notifications";
import { Avatar } from "@/components/ui/avatar";
import { Dropdown } from "@/components/ui/dropdown";
import { NotificationBell } from "@/components/notifications/NotificationBell";
import { Button } from "@/components/ui/button";
import { ROLE_HOME_PATH } from "@/constants/roles";
import { publicRoutes, authRoutes } from "@/config/routes.config";
import { cn } from "@/lib/utils/cn";

const PUBLIC_NAV = [
  { label: "Find a Tailor", to: publicRoutes.findTailor },
  { label: "Find a Designer", to: publicRoutes.findDesigner },
  { label: "Marketplace", to: publicRoutes.vendorMarketplace },
  { label: "How it works", to: publicRoutes.howItWorks },
];

export function Header() {
  const { user, logOut } = useAuth();
  const { unreadCount } = useNotifications(Boolean(user));
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-paper/95 backdrop-blur-sm">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 lg:px-6">
        {/* Brand */}
        <Link
          to={user ? ROLE_HOME_PATH[user.role] : publicRoutes.home}
          className="font-display text-xl text-ink"
        >
          Tailora
        </Link>

        {/* Desktop nav — public only */}
        {!user && (
          <nav className="hidden items-center gap-1 md:flex" aria-label="Main navigation">
            {PUBLIC_NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  cn(
                    "rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    isActive ? "text-ink" : "text-ink-soft hover:text-ink"
                  )
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        )}

        {/* Right actions */}
        <div className="flex items-center gap-2">
          {user ? (
            <>
              <NotificationBell unreadCount={unreadCount} />
              <Dropdown
                trigger={
                  <Avatar name={user.full_name} src={user.profile_photo_url} size="sm" />
                }
              >
                <div className="px-3 py-2 text-sm text-ink-soft">{user.email}</div>
                <Link
                  to={`${ROLE_HOME_PATH[user.role]}/profile`}
                  className="block px-3 py-2 text-sm hover:bg-muslin"
                >
                  Profile
                </Link>
                <button
                  onClick={() => logOut()}
                  className="block w-full px-3 py-2 text-left text-sm text-thread hover:bg-muslin"
                >
                  Log out
                </button>
              </Dropdown>
            </>
          ) : (
            <>
              <Link to={authRoutes.login} className="hidden text-sm font-medium text-ink-soft hover:text-ink md:block">
                Sign in
              </Link>
              <Link to={authRoutes.signup}>
                <Button size="sm" className="bg-brass text-ink hover:bg-brass-deep">
                  Get started
                </Button>
              </Link>
              {/* Mobile hamburger */}
              <button
                aria-label={mobileOpen ? "Close menu" : "Open menu"}
                aria-expanded={mobileOpen}
                onClick={() => setMobileOpen((v) => !v)}
                className="ml-1 flex h-9 w-9 items-center justify-center rounded-lg text-ink-soft hover:bg-muslin md:hidden"
              >
                {mobileOpen ? (
                  <svg width="20" height="20" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M18 6 6 18M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                  </svg>
                ) : (
                  <svg width="20" height="20" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                  </svg>
                )}
              </button>
            </>
          )}
        </div>
      </div>

      {/* Mobile nav drawer */}
      {mobileOpen && !user && (
        <nav
          className="border-t border-line bg-paper px-4 pb-4 md:hidden"
          aria-label="Mobile navigation"
        >
          {PUBLIC_NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) =>
                cn(
                  "block rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive ? "text-ink" : "text-ink-soft hover:text-ink"
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
          <Link
            to={authRoutes.login}
            onClick={() => setMobileOpen(false)}
            className="mt-1 block rounded-lg px-3 py-2.5 text-sm font-medium text-ink-soft hover:text-ink"
          >
            Sign in
          </Link>
        </nav>
      )}
    </header>
  );
}
