import { describe, expect, it } from "vitest";
import { resolveIrcInboundTarget } from "./monitor.js";

describe("irc monitor inbound target", () => {
  it("keeps channel target for group messages", () => {
    expect(
      resolveIrcInboundTarget({
        target: "#mirai",
        senderNick: "alice",
      }),
    ).toEqual({
      isGroup: true,
      target: "#mirai",
      rawTarget: "#mirai",
    });
  });

  it("maps DM target to sender nick and preserves raw target", () => {
    expect(
      resolveIrcInboundTarget({
        target: "mirai-bot",
        senderNick: "alice",
      }),
    ).toEqual({
      isGroup: false,
      target: "alice",
      rawTarget: "mirai-bot",
    });
  });

  it("falls back to raw target when sender nick is empty", () => {
    expect(
      resolveIrcInboundTarget({
        target: "mirai-bot",
        senderNick: " ",
      }),
    ).toEqual({
      isGroup: false,
      target: "mirai-bot",
      rawTarget: "mirai-bot",
    });
  });
});
