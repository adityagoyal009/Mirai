// Narrow plugin-sdk surface for the bundled diffs plugin.
// Keep this list additive and scoped to symbols used under extensions/diffs.

export { definePluginEntry } from "./core.js";
export type { MiraiConfig } from "../config/config.js";
export { resolvePreferredMiraiTmpDir } from "../infra/tmp-mirai-dir.js";
export type {
  AnyAgentTool,
  MiraiPluginApi,
  MiraiPluginConfigSchema,
  MiraiPluginToolContext,
  PluginLogger,
} from "../plugins/types.js";
