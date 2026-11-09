import { matchRoutes, redirect, type LoaderFunctionArgs, type RouteObject } from "react-router-dom";

/**
 * Links built from a site address that ends in "/app" (for example FRONTEND_URL set to
 * https://…/app/) come out as /app/reset-password, /app/verify-email, /app/track/…, /app/s/…, or
 * /app/app/customer/… . Send each one to the page it meant; anything else is still "Page not found".
 */
export function appPrefixLoader(knownRoutes: () => RouteObject[]) {
  return ({ request }: LoaderFunctionArgs) => {
    const url = new URL(request.url);
    const target = url.pathname.replace(/^\/app(?=\/)/, "") || "/";
    if (target !== url.pathname && (target.startsWith("/app/") || matchRoutes(knownRoutes(), target))) {
      return redirect(`${target}${url.search}${url.hash}`);
    }
    throw new Response("Not Found", { status: 404 });
  };
}
