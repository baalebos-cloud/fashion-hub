import type { ComponentType } from "react";
import type { RouteObject } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import Home from "@/pages/public/Home";
import About from "@/pages/public/About";
import HowItWorks from "@/pages/public/HowItWorks";
import FindTailor from "@/pages/public/FindTailor";
import FindDesigner from "@/pages/public/FindDesigner";
import VendorMarketplace from "@/pages/public/VendorMarketplace";
import ProductDetails from "@/pages/public/ProductDetails";
import ProfessionalProfile from "@/pages/public/ProfessionalProfile";
import Pricing from "@/pages/public/Pricing";
import Contact from "@/pages/public/Contact";
import Terms from "@/pages/public/Terms";
import Privacy from "@/pages/public/Privacy";
import Help from "@/pages/public/Help";
import { publicRoutes } from "@/config/routes.config";

const withLayout = (Page: ComponentType) => (
  <AppLayout>
    <Page />
  </AppLayout>
);

export const publicRouteObjects: RouteObject[] = [
  { path: publicRoutes.home, element: withLayout(Home) },
  { path: publicRoutes.about, element: withLayout(About) },
  { path: publicRoutes.howItWorks, element: withLayout(HowItWorks) },
  { path: publicRoutes.findTailor, element: withLayout(FindTailor) },
  { path: publicRoutes.findDesigner, element: withLayout(FindDesigner) },
  { path: publicRoutes.vendorMarketplace, element: withLayout(VendorMarketplace) },
  { path: "/products/:productId", element: withLayout(ProductDetails) },
  { path: "/professionals/:professionalId", element: withLayout(ProfessionalProfile) },
  { path: publicRoutes.pricing, element: withLayout(Pricing) },
  { path: publicRoutes.contact, element: withLayout(Contact) },
  { path: publicRoutes.terms, element: withLayout(Terms) },
  { path: publicRoutes.privacy, element: withLayout(Privacy) },
  { path: publicRoutes.help, element: withLayout(Help) },
];
