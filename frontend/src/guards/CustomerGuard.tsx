import { RoleGuard } from "./RoleGuard";

export function CustomerGuard() {
  return <RoleGuard allowedRoles={["customer"]} />;
}
