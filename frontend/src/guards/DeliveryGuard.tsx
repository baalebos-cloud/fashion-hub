import { RoleGuard } from "./RoleGuard";

export function DeliveryGuard() {
  return <RoleGuard allowedRoles={["delivery_partner"]} />;
}
