import { useEffect, useState } from "react";
import { professionalsApi } from "@/api/professionals.api";
import { useAuth } from "@/hooks/use-auth";
import { useDesigns } from "@/hooks/use-designs";
import { DesignGallery } from "@/components/designs/DesignGallery";
import { DesignUpload } from "@/components/designs/DesignUpload";
import { Button } from "@/components/ui/button";
import type { Design } from "@/types/design";

export default function Designs() {
  const { user } = useAuth();
  const [professionalId, setProfessionalId] = useState<string | undefined>();
  const [profileError, setProfileError] = useState(false);
  useEffect(() => {
    if (!user?.id) return;
    let active = true;
    professionalsApi.mine()
      .then((profile) => {
        if (active) {
          setProfessionalId(profile?.id);
          setProfileError(!profile);
        }
      })
      .catch(() => { if (active) setProfileError(true); });
    return () => { active = false; };
  }, [user?.id]);
  const { designs: fetchedDesigns, isLoading } = useDesigns(professionalId);
  const [localDesigns, setLocalDesigns] = useState<Design[]>([]);
  const [isAdding, setIsAdding] = useState(false);

  const designs = [...fetchedDesigns, ...localDesigns];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-xl text-ink">Designs</h1>
        {!isAdding && <Button onClick={() => setIsAdding(true)}>Add design</Button>}
      </div>
      {isAdding && (
        <DesignUpload
          onCreated={(design) => {
            setLocalDesigns((prev) => [...prev, design]);
            setIsAdding(false);
          }}
        />
      )}
      {profileError && <p role="alert" className="text-sm text-thread">Your professional profile could not be loaded. Check your profile details.</p>}
      <DesignGallery designs={designs} isLoading={isLoading || (!professionalId && !profileError)} />
    </div>
  );
}
