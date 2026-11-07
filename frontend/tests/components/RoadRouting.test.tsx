import { describe, expect, it } from "vitest";
import { describeRoute } from "@/lib/utils/route";

describe("route labels", () => {
  it("names real road routes and flags estimates", () => {
    expect(describeRoute({ distance_km: 14.2, duration_minutes: 33, source: "google_routes", verified: true, traffic_aware: true }))
      .toBe("14.2 km by road · about 33 min in current traffic");
    expect(describeRoute({ distance_km: 9.8, duration_minutes: 21, source: "osrm", verified: true }))
      .toBe("9.8 km by road · about 21 min");
    expect(describeRoute({ distance_km: 12.04, duration_minutes: 30, source: "straight_line_estimate", verified: false }))
      .toBe("≈ 12.0 km (estimate)");
    expect(describeRoute(null, 7.3)).toBe("≈ 7.3 km (estimate)");
    expect(describeRoute(undefined, null)).toBeNull();
  });
});
