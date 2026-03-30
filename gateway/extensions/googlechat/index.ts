import type { MiraiPluginApi } from "openclaw/plugin-sdk/googlechat";
import { emptyPluginConfigSchema } from "openclaw/plugin-sdk/googlechat";
import { googlechatDock, googlechatPlugin } from "./src/channel.js";
import { setGoogleChatRuntime } from "./src/runtime.js";

const plugin = {
  id: "googlechat",
  name: "Google Chat",
  description: "Mirai Google Chat channel plugin",
  configSchema: emptyPluginConfigSchema(),
  register(api: MiraiPluginApi) {
    setGoogleChatRuntime(api.runtime);
    api.registerChannel({ plugin: googlechatPlugin, dock: googlechatDock });
  },
};

export default plugin;
