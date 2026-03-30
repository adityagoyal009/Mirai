import { vi } from "vitest";
import { installChromeUserDataDirHooks } from "./chrome-user-data-dir.test-harness.js";

const chromeUserDataDir = { dir: "/tmp/mirai" };
installChromeUserDataDirHooks(chromeUserDataDir);

vi.mock("./chrome.js", () => ({
  isChromeCdpReady: vi.fn(async () => true),
  isChromeReachable: vi.fn(async () => true),
  launchMiraiChrome: vi.fn(async () => {
    throw new Error("unexpected launch");
  }),
  resolveMiraiUserDataDir: vi.fn(() => chromeUserDataDir.dir),
  stopMiraiChrome: vi.fn(async () => {}),
}));
