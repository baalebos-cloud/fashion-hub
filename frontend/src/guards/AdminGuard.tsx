import { RoleGuard } from "./RoleGuard";

export function AdminGuard() {
  return <RoleGuard allowedRoles={["admin"]} />;
}
