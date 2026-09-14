import { RoleGuard } from "./RoleGuard";

export function ProfessionalGuard() {
  return <RoleGuard allowedRoles={["tailor", "designer"]} />;
}
