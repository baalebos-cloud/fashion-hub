import { describe, expect, it } from "vitest";
import { applyToIosProject, nextVersion } from "../../scripts/app-version.mjs";

describe("app:version", () => {
  it("bumps the build number and keeps the version by default", () => {
    expect(nextVersion({ version: "1.0.0", build: 4 })).toEqual({ version: "1.0.0", build: 5 });
  });

  it("sets a new version and still bumps the build", () => {
    expect(nextVersion({ version: "1.0.0", build: 4 }, "1.1.0")).toEqual({ version: "1.1.0", build: 5 });
  });

  it("rejects versions the stores won't accept", () => {
    expect(() => nextVersion({ version: "1.0.0", build: 1 }, "v2")).toThrow(/1\.2\.3/);
  });

  it("writes both Debug and Release settings of the iOS project", () => {
    const project = "MARKETING_VERSION = 1.0;\nCURRENT_PROJECT_VERSION = 1;\nMARKETING_VERSION = 1.0;\nCURRENT_PROJECT_VERSION = 1;";
    const out = applyToIosProject(project, { version: "2.0.0", build: 7 });
    expect(out.match(/MARKETING_VERSION = 2\.0\.0;/g)).toHaveLength(2);
    expect(out.match(/CURRENT_PROJECT_VERSION = 7;/g)).toHaveLength(2);
  });
});
