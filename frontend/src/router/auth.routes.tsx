import type { RouteObject } from "react-router-dom";
import Login from "@/pages/auth/Login";
import Signup from "@/pages/auth/Signup";
import ForgotPassword from "@/pages/auth/ForgotPassword";
import ResetPassword from "@/pages/auth/ResetPassword";
import VerifyEmail from "@/pages/auth/VerifyEmail";
import AuthCallback from "@/pages/auth/AuthCallback";
import { authRoutes } from "@/config/routes.config";

export const authRouteObjects: RouteObject[] = [
  { path: authRoutes.login, element: <Login /> },
  { path: authRoutes.signup, element: <Signup /> },
  { path: authRoutes.forgotPassword, element: <ForgotPassword /> },
  { path: authRoutes.resetPassword, element: <ResetPassword /> },
  { path: authRoutes.verifyEmail, element: <VerifyEmail /> },
  { path: authRoutes.callback, element: <AuthCallback /> },
];
