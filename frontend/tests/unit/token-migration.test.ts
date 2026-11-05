import { afterEach, describe, expect, it } from "vitest";
import { clearTokens, getAccessToken, getRefreshToken, hasSession } from "@/lib/auth/token";

describe("token storage rename", () => {
  afterEach(() => sessionStorage.clear());

  it("keeps a pre-rebrand session signed in and moves it to the new keys", () => {
    sessionStorage.setItem("fashionhub.access_token", "old-access");
    sessionStorage.setItem("fashionhub.refresh_token", "old-refresh");

    expect(hasSession()).toBe(true);
    expect(getAccessToken()).toBe("old-access");
    expect(getRefreshToken()).toBe("old-refresh");
    expect(sessionStorage.getItem("tailora.access_token")).toBe("old-access");
    expect(sessionStorage.getItem("fashionhub.access_token")).toBeNull();
  });

  it("prefers the new key and clears legacy keys on sign-out", () => {
    sessionStorage.setItem("tailora.access_token", "new");
    sessionStorage.setItem("fashionhub.access_token", "stale");
    expect(getAccessToken()).toBe("new");

    clearTokens();
    expect(sessionStorage.getItem("fashionhub.access_token")).toBeNull();
    expect(hasSession()).toBe(false);
  });
});
