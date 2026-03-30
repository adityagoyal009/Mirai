import { describe, expect, it } from "vitest";
import {
  ensureMiraiExecMarkerOnProcess,
  markMiraiExecEnv,
  MIRAI_CLI_ENV_VALUE,
  MIRAI_CLI_ENV_VAR,
} from "./mirai-exec-env.js";

describe("markMiraiExecEnv", () => {
  it("returns a cloned env object with the exec marker set", () => {
    const env = { PATH: "/usr/bin", MIRAI_CLI: "0" };
    const marked = markMiraiExecEnv(env);

    expect(marked).toEqual({
      PATH: "/usr/bin",
      MIRAI_CLI: MIRAI_CLI_ENV_VALUE,
    });
    expect(marked).not.toBe(env);
    expect(env.MIRAI_CLI).toBe("0");
  });
});

describe("ensureMiraiExecMarkerOnProcess", () => {
  it("mutates and returns the provided process env", () => {
    const env: NodeJS.ProcessEnv = { PATH: "/usr/bin" };

    expect(ensureMiraiExecMarkerOnProcess(env)).toBe(env);
    expect(env[MIRAI_CLI_ENV_VAR]).toBe(MIRAI_CLI_ENV_VALUE);
  });

  it("defaults to mutating process.env when no env object is provided", () => {
    const previous = process.env[MIRAI_CLI_ENV_VAR];
    delete process.env[MIRAI_CLI_ENV_VAR];

    try {
      expect(ensureMiraiExecMarkerOnProcess()).toBe(process.env);
      expect(process.env[MIRAI_CLI_ENV_VAR]).toBe(MIRAI_CLI_ENV_VALUE);
    } finally {
      if (previous === undefined) {
        delete process.env[MIRAI_CLI_ENV_VAR];
      } else {
        process.env[MIRAI_CLI_ENV_VAR] = previous;
      }
    }
  });
});
