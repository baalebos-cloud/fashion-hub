import { useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";
import type { ButtonProps } from "@/components/ui/button";

export function LogoutButton(props: Omit<ButtonProps, "onClick">) {
  const { logOut } = useAuth();
  const navigate = useNavigate();

  async function handleClick() {
    await logOut();
    navigate("/");
  }

  return (
    <Button variant="ghost" onClick={handleClick} {...props}>
      Log out
    </Button>
  );
}
