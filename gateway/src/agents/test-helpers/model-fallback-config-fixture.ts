import type { MiraiConfig } from "../../config/config.js";

export function makeModelFallbackCfg(overrides: Partial<MiraiConfig> = {}): MiraiConfig {
  return {
    agents: {
      defaults: {
        model: {
          primary: "openai/gpt-4.1-mini",
          fallbacks: ["anthropic/claude-haiku-3-5"],
        },
      },
    },
    ...overrides,
  } as MiraiConfig;
}
