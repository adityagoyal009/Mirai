import { afterEach, describe, expect, it, vi } from "vitest";

type LoggerModule = typeof import("./logger.js");

const originalGetBuiltinModule = (
  process as NodeJS.Process & { getBuiltinModule?: (id: string) => unknown }
).getBuiltinModule;

async function importBrowserSafeLogger(params?: {
  resolvePreferredMiraiTmpDir?: ReturnType<typeof vi.fn>;
}): Promise<{
  module: LoggerModule;
  resolvePreferredMiraiTmpDir: ReturnType<typeof vi.fn>;
}> {
  vi.resetModules();
  const resolvePreferredMiraiTmpDir =
    params?.resolvePreferredMiraiTmpDir ??
    vi.fn(() => {
      throw new Error("resolvePreferredMiraiTmpDir should not run during browser-safe import");
    });

  vi.doMock("../infra/tmp-mirai-dir.js", async () => {
    const actual = await vi.importActual<typeof import("../infra/tmp-mirai-dir.js")>(
      "../infra/tmp-mirai-dir.js",
    );
    return {
      ...actual,
      resolvePreferredMiraiTmpDir,
    };
  });

  Object.defineProperty(process, "getBuiltinModule", {
    configurable: true,
    value: undefined,
  });

  const module = await import("./logger.js");
  return { module, resolvePreferredMiraiTmpDir };
}

describe("logging/logger browser-safe import", () => {
  afterEach(() => {
    vi.resetModules();
    vi.doUnmock("../infra/tmp-mirai-dir.js");
    Object.defineProperty(process, "getBuiltinModule", {
      configurable: true,
      value: originalGetBuiltinModule,
    });
  });

  it("does not resolve the preferred temp dir at import time when node fs is unavailable", async () => {
    const { module, resolvePreferredMiraiTmpDir } = await importBrowserSafeLogger();

    expect(resolvePreferredMiraiTmpDir).not.toHaveBeenCalled();
    expect(module.DEFAULT_LOG_DIR).toBe("/tmp/mirai");
    expect(module.DEFAULT_LOG_FILE).toBe("/tmp/mirai/mirai.log");
  });

  it("disables file logging when imported in a browser-like environment", async () => {
    const { module, resolvePreferredMiraiTmpDir } = await importBrowserSafeLogger();

    expect(module.getResolvedLoggerSettings()).toMatchObject({
      level: "silent",
      file: "/tmp/mirai/mirai.log",
    });
    expect(module.isFileLogLevelEnabled("info")).toBe(false);
    expect(() => module.getLogger().info("browser-safe")).not.toThrow();
    expect(resolvePreferredMiraiTmpDir).not.toHaveBeenCalled();
  });
});
