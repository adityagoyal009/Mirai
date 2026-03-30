import type {
  AnyAgentTool,
  MiraiPluginApi,
  MiraiPluginToolFactory,
} from "openclaw/plugin-sdk/lobster";
import { createLobsterTool } from "./src/lobster-tool.js";

export default function register(api: MiraiPluginApi) {
  api.registerTool(
    ((ctx) => {
      if (ctx.sandboxed) {
        return null;
      }
      return createLobsterTool(api) as AnyAgentTool;
    }) as MiraiPluginToolFactory,
    { optional: true },
  );
}
