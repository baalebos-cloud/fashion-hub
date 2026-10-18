import { spawnSync } from "node:child_process";
import path from "node:path";
import process from "node:process";
import { describe, expect, it } from "vitest";

function check(value?: string) {
  return spawnSync(process.execPath, [path.resolve("scripts/check-vercel-env.mjs")], {
    encoding: "utf8",
    env: value === undefined ? {} : { VITE_API_BASE_URL: value },
  });
}

describe("Vercel backend API configuration", () => {
  it.each([
    undefined, "", "/api/v1", "//backend.example/api/v1",
    "fashion-hub-production-2661.up.railway.app",
    "fashion-hub-production-2661.up.railway.app/api/v1",
    "https:backend.example/api/v1", "https:/backend.example/api/v1",
    "http://backend.example/api/v1", "https://backend.example",
    "https://user:private-marker@backend.example/api/v1",
    "https://backend.example/api/v1?token=private-marker",
    "https://backend.example/api/v1#private-marker",
    " https://backend.example/api/v1 ",
  ])("rejects a value that cannot safely address the backend: %s", (value) => {
    const result = check(value);
    expect(result.status).toBe(1);
    expect(result.stderr).toContain("VITE_API_BASE_URL");
    expect(result.stderr).toContain("including the API prefix");
    expect(result.stderr).not.toContain("private-marker");
  });

  it.each([
    "https://backend.example/api/v1",
    "https://backend.example/api/v1/",
    "https://backend.example/custom/api/v2",
  ])("accepts a complete HTTPS API URL: %s", (value) => {
    const result = check(value);
    expect(result.status).toBe(0);
    expect(result.stderr).toBe("");
  });
});
