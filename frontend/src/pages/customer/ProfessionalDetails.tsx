import { useEffect, useState } from "react";
import { trackView, viewSource } from "@/lib/tracking/interactions";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { professionalsApi } from "@/api/professionals.api";
import { useAuth } from "@/hooks/use-auth";
import { ProfessionalProfile } from "@/components/professionals/ProfessionalProfile";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import { customerRoutes } from "@/config/routes.config";
import type { Professional } from "@/types/professional";
import type { User } from "@/types/user";

export default function ProfessionalDetails() {
  const { professionalId } = useParams<{ professionalId: string }>();
  const [search] = useSearchParams();
  const from = search.get("from");
  const { user } = useAuth();
  const navigate = useNavigate();
  const [professional, setProfessional] = useState<Professional | null>(null);

  useEffect(() => {
    if (professionalId) professionalsApi.getById(professionalId).then(setProfessional);
  }, [professionalId]);
  // Only `professional` should re-record a view; `from` is read once with it.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { if (professional) trackView("professional", professional.id, viewSource(from, "profile")); }, [professional]);

  if (!professional) return <LoadingScreen label="Loading profile…" />;

  const displayUser: User = {
    id: professional.user_id,
    email: "",
    full_name: professional.business_name ?? "Professional",
    role: professional.professional_type,
    is_email_verified: true,
    is_phone_verified: true,
    timezone: user?.timezone ?? "UTC",
  };

  return (
    <ProfessionalProfile
      professional={professional}
      user={displayUser}
      onOrder={() => navigate(customerRoutes.createOrder(professional.id))}
    />
  );
}
