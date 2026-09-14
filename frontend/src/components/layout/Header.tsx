import { Link } from "react-router-dom";
import { useAuth } from "@/hooks/use-auth";
import { useNotifications } from "@/hooks/use-notifications";
import { Avatar } from "@/components/ui/avatar";
import { Dropdown } from "@/components/ui/dropdown";
import { NotificationBell } from "@/components/notifications/NotificationBell";
import { ROLE_HOME_PATH } from "@/constants/roles";

export function Header() {
  const { user, logOut } = useAuth();
  const { unreadCount } = useNotifications();

  return (
    <header
      className="flex h-16 flex-shrink-0 items-center justify-between border-b border-line bg-paper px-4 lg:px-6"
      style={{ height: "var(--header-height)" }}
    >
      <Link to={user ? ROLE_HOME_PATH[user.role] : "/"} className="font-display text-lg text-ink">
        Fashion Hub
      </Link>

      <div className="flex items-center gap-3">
        <NotificationBell unreadCount={unreadCount} />

        {user && (
          <Dropdown trigger={<Avatar name={user.full_name} src={user.profile_photo_url} size="sm" />}>
            <div className="px-3 py-2 text-sm text-ink-soft">{user.email}</div>
            <Link to={`${ROLE_HOME_PATH[user.role]}/profile`} className="block px-3 py-2 text-sm hover:bg-muslin">
              Profile
            </Link>
            <button onClick={() => logOut()} className="block w-full px-3 py-2 text-left text-sm text-thread hover:bg-muslin">
              Log out
            </button>
          </Dropdown>
        )}
      </div>
    </header>
  );
}
