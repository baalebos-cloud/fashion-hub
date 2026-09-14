import { AuthLayout } from "@/components/layout/AuthLayout";
import { VerifyEmail as VerifyEmailComponent } from "@/components/auth/VerifyEmail";

export default function VerifyEmail() {
  return (
    <AuthLayout>
      <VerifyEmailComponent />
    </AuthLayout>
  );
}
