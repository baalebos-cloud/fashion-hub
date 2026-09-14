import { RoleGuard } from "./RoleGuard";

export function VendorGuard() {
  return <RoleGuard allowedRoles={["vendor"]} />;
}
