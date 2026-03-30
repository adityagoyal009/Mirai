import type { MiraiConfig } from "./config.js";

export function ensurePluginAllowlisted(cfg: MiraiConfig, pluginId: string): MiraiConfig {
  const allow = cfg.plugins?.allow;
  if (!Array.isArray(allow) || allow.includes(pluginId)) {
    return cfg;
  }
  return {
    ...cfg,
    plugins: {
      ...cfg.plugins,
      allow: [...allow, pluginId],
    },
  };
}
