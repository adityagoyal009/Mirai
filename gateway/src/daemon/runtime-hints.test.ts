import { describe, expect, it } from "vitest";
import { buildPlatformRuntimeLogHints, buildPlatformServiceStartHints } from "./runtime-hints.js";

describe("buildPlatformRuntimeLogHints", () => {
  it("renders launchd log hints on darwin", () => {
    expect(
      buildPlatformRuntimeLogHints({
        platform: "darwin",
        env: {
          MIRAI_STATE_DIR: "/tmp/mirai-state",
          MIRAI_LOG_PREFIX: "gateway",
        },
        systemdServiceName: "mirai-gateway",
        windowsTaskName: "Mirai Gateway",
      }),
    ).toEqual([
      "Launchd stdout (if installed): /tmp/mirai-state/logs/gateway.log",
      "Launchd stderr (if installed): /tmp/mirai-state/logs/gateway.err.log",
    ]);
  });

  it("renders systemd and windows hints by platform", () => {
    expect(
      buildPlatformRuntimeLogHints({
        platform: "linux",
        systemdServiceName: "mirai-gateway",
        windowsTaskName: "Mirai Gateway",
      }),
    ).toEqual(["Logs: journalctl --user -u mirai-gateway.service -n 200 --no-pager"]);
    expect(
      buildPlatformRuntimeLogHints({
        platform: "win32",
        systemdServiceName: "mirai-gateway",
        windowsTaskName: "Mirai Gateway",
      }),
    ).toEqual(['Logs: schtasks /Query /TN "Mirai Gateway" /V /FO LIST']);
  });
});

describe("buildPlatformServiceStartHints", () => {
  it("builds platform-specific service start hints", () => {
    expect(
      buildPlatformServiceStartHints({
        platform: "darwin",
        installCommand: "mirai gateway install",
        startCommand: "mirai gateway",
        launchAgentPlistPath: "~/Library/LaunchAgents/com.mirai.gateway.plist",
        systemdServiceName: "mirai-gateway",
        windowsTaskName: "Mirai Gateway",
      }),
    ).toEqual([
      "mirai gateway install",
      "mirai gateway",
      "launchctl bootstrap gui/$UID ~/Library/LaunchAgents/com.mirai.gateway.plist",
    ]);
    expect(
      buildPlatformServiceStartHints({
        platform: "linux",
        installCommand: "mirai gateway install",
        startCommand: "mirai gateway",
        launchAgentPlistPath: "~/Library/LaunchAgents/com.mirai.gateway.plist",
        systemdServiceName: "mirai-gateway",
        windowsTaskName: "Mirai Gateway",
      }),
    ).toEqual([
      "mirai gateway install",
      "mirai gateway",
      "systemctl --user start mirai-gateway.service",
    ]);
  });
});
