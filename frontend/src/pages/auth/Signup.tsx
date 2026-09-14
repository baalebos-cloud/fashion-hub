import { AuthLayout } from "@/components/layout/AuthLayout";
import { SignupForm } from "@/components/auth/SignupForm";

export default function Signup() {
  return (
    <AuthLayout>
      <SignupForm />
    </AuthLayout>
  );
}
