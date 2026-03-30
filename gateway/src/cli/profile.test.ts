import path from "node:path";
import { describe, expect, it } from "vitest";
import { formatCliCommand } from "./command-format.js";
import { applyCliProfileEnv, parseCliProfileArgs } from "./profile.js";

describe("parseCliProfileArgs", () => {
  it("leaves gateway --dev for subcommands", () => {
    const res = parseCliProfileArgs([
      "node",
      "mirai",
      "gateway",
      "--dev",
      "--allow-unconfigured",
    ]);
    if (!res.ok) {
      throw new Error(res.error);
    }
    expect(res.profile).toBeNull();
    expect(res.argv).toEqual(["node", "mirai", "gateway", "--dev", "--allow-unconfigured"]);
  });

  it("still accepts global --dev before subcommand", () => {
    const res = parseCliProfileArgs(["node", "mirai", "--dev", "gateway"]);
    if (!res.ok) {
      throw new Error(res.error);
    }
    expect(res.profile).toBe("dev");
    expect(res.argv).toEqual(["node", "mirai", "gateway"]);
  });

  it("parses --profile value and strips it", () => {
    const res = parseCliProfileArgs(["node", "mirai", "--profile", "work", "status"]);
    if (!res.ok) {
      throw new Error(res.error);
    }
    expect(res.profile).toBe("work");
    expect(res.argv).toEqual(["node", "mirai", "status"]);
  });

  it("rejects missing profile value", () => {
    const res = parseCliProfileArgs(["node", "mirai", "--profile"]);
    expect(res.ok).toBe(false);
  });

  it.each([
    ["--dev first", ["node", "mirai", "--dev", "--profile", "work", "status"]],
    ["--profile first", ["node", "mirai", "--profile", "work", "--dev", "status"]],
  ])("rejects combining --dev with --profile (%s)", (_name, argv) => {
    const res = parseCliProfileArgs(argv);
    expect(res.ok).toBe(false);
  });
});

describe("applyCliProfileEnv", () => {
  it("fills env defaults for dev profile", () => {
    const env: Record<string, string | undefined> = {};
    applyCliProfileEnv({
      profile: "dev",
      env,
      homedir: () => "/home/peter",
    });
    const expectedStateDir = path.join(path.resolve("/home/peter"), ".mirai-dev");
    expect(env.MIRAI_PROFILE).toBe("dev");
    expect(env.MIRAI_STATE_DIR).toBe(expectedStateDir);
    expect(env.MIRAI_CONFIG_PATH).toBe(path.join(expectedStateDir, "mirai.json"));
    expect(env.MIRAI_GATEWAY_PORT).toBe("19001");
  });

  it("does not override explicit env values", () => {
    const env: Record<string, string | undefined> = {
      MIRAI_STATE_DIR: "/custom",
      MIRAI_GATEWAY_PORT: "19099",
    };
    applyCliProfileEnv({
      profile: "dev",
      env,
      homedir: () => "/home/peter",
    });
    expect(env.MIRAI_STATE_DIR).toBe("/custom");
    expect(env.MIRAI_GATEWAY_PORT).toBe("19099");
    expect(env.MIRAI_CONFIG_PATH).toBe(path.join("/custom", "mirai.json"));
  });

  it("uses MIRAI_HOME when deriving profile state dir", () => {
    const env: Record<string, string | undefined> = {
      MIRAI_HOME: "/srv/mirai-home",
      HOME: "/home/other",
    };
    applyCliProfileEnv({
      profile: "work",
      env,
      homedir: () => "/home/fallback",
    });

    const resolvedHome = path.resolve("/srv/mirai-home");
    expect(env.MIRAI_STATE_DIR).toBe(path.join(resolvedHome, ".mirai-work"));
    expect(env.MIRAI_CONFIG_PATH).toBe(
      path.join(resolvedHome, ".mirai-work", "mirai.json"),
    );
  });
});

describe("formatCliCommand", () => {
  it.each([
    {
      name: "no profile is set",
      cmd: "mirai doctor --fix",
      env: {},
      expected: "mirai doctor --fix",
    },
    {
      name: "profile is default",
      cmd: "mirai doctor --fix",
      env: { MIRAI_PROFILE: "default" },
      expected: "mirai doctor --fix",
    },
    {
      name: "profile is Default (case-insensitive)",
      cmd: "mirai doctor --fix",
      env: { MIRAI_PROFILE: "Default" },
      expected: "mirai doctor --fix",
    },
    {
      name: "profile is invalid",
      cmd: "mirai doctor --fix",
      env: { MIRAI_PROFILE: "bad profile" },
      expected: "mirai doctor --fix",
    },
    {
      name: "--profile is already present",
      cmd: "mirai --profile work doctor --fix",
      env: { MIRAI_PROFILE: "work" },
      expected: "mirai --profile work doctor --fix",
    },
    {
      name: "--dev is already present",
      cmd: "mirai --dev doctor",
      env: { MIRAI_PROFILE: "dev" },
      expected: "mirai --dev doctor",
    },
  ])("returns command unchanged when $name", ({ cmd, env, expected }) => {
    expect(formatCliCommand(cmd, env)).toBe(expected);
  });

  it("inserts --profile flag when profile is set", () => {
    expect(formatCliCommand("mirai doctor --fix", { MIRAI_PROFILE: "work" })).toBe(
      "mirai --profile work doctor --fix",
    );
  });

  it("trims whitespace from profile", () => {
    expect(formatCliCommand("mirai doctor --fix", { MIRAI_PROFILE: "  jbmirai  " })).toBe(
      "mirai --profile jbmirai doctor --fix",
    );
  });

  it("handles command with no args after mirai", () => {
    expect(formatCliCommand("mirai", { MIRAI_PROFILE: "test" })).toBe(
      "mirai --profile test",
    );
  });

  it("handles pnpm wrapper", () => {
    expect(formatCliCommand("pnpm mirai doctor", { MIRAI_PROFILE: "work" })).toBe(
      "pnpm mirai --profile work doctor",
    );
  });
});
