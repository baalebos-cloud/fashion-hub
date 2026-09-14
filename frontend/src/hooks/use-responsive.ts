import { useEffect, useState } from "react";

const BREAKPOINTS = { sm: 640, md: 768, lg: 1024, xl: 1280, "2xl": 1536 } as const;
type Breakpoint = keyof typeof BREAKPOINTS;

/** JS-side breakpoint check for components that can't rely on Tailwind's
 * CSS-only responsive classes (canvas/map components, conditional
 * mounting rather than conditional styling). Mirrors styles/responsive.css. */
export function useResponsive(breakpoint: Breakpoint = "lg") {
  const [isAboveBreakpoint, setIsAboveBreakpoint] = useState(
    () => window.innerWidth >= BREAKPOINTS[breakpoint]
  );

  useEffect(() => {
    const mediaQuery = window.matchMedia(`(min-width: ${BREAKPOINTS[breakpoint]}px)`);
    const handler = (e: MediaQueryListEvent) => setIsAboveBreakpoint(e.matches);
    mediaQuery.addEventListener("change", handler);
    return () => mediaQuery.removeEventListener("change", handler);
  }, [breakpoint]);

  return isAboveBreakpoint;
}
