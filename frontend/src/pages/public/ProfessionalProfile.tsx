import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { professionalsApi } from "@/api/professionals.api";
import { ProfessionalProfile as ProfessionalProfileComponent } from "@/components/professionals/ProfessionalProfile";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import { authRoutes } from "@/config/routes.config";
import type { Professional } from "@/types/professional";
import type { User } from "@/types/user";

export default function ProfessionalProfile() {
  const { professionalId } = useParams<{ professionalId: string }>();
  const navigate = useNavigate();
  const [professional, setProfessional] = useState<Professional | null>(null);

  useEffect(() => {
    if (professionalId) professionalsApi.getById(professionalId).then(setProfessional);
  }, [professionalId]);

  if (!professional) return <LoadingScreen label="Loading profile…" />;

  // Public page has no User record to display (only Professional data is
  // public); a minimal placeholder covers the ProfileHeader's needs here.
  const placeholderUser: User = {
    id: professional.user_id,
    email: "",
    full_name: professional.business_name ?? "Professional",
    role: professional.professional_type,
    is_email_verified: true,
    is_phone_verified: true,
    timezone: "UTC",
  };

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <ProfessionalProfileComponent professional={professional} user={placeholderUser} onOrder={() => navigate(authRoutes.login)} />
    </div>
  );
}
