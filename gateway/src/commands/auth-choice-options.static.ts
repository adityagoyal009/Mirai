import { AUTH_CHOICE_LEGACY_ALIASES_FOR_CLI } from "./auth-choice-legacy.js";
import type { AuthChoice, AuthChoiceGroupId } from "./onboard-types.js";

export type { AuthChoiceGroupId };

export type AuthChoiceOption = {
  value: AuthChoice;
  label: string;
  hint?: string;
  groupId?: AuthChoiceGroupId;
  groupLabel?: string;
  groupHint?: string;
};

export type AuthChoiceGroup = {
  value: AuthChoiceGroupId;
  label: string;
  hint?: string;
  options: AuthChoiceOption[];
};

// Matches Mirai's provider groups — Anthropic, OpenAI, Google as top-level choices
export const CORE_AUTH_CHOICE_OPTIONS: ReadonlyArray<AuthChoiceOption> = [
  // ── Anthropic ──
  {
    value: "setup-token" as AuthChoice,
    label: "Anthropic token (paste setup-token)",
    hint: "run `claude setup-token` elsewhere, then paste the token here",
    groupId: "anthropic" as AuthChoiceGroupId,
    groupLabel: "Anthropic",
    groupHint: "setup-token + API key",
  },
  {
    value: "apiKey" as AuthChoice,
    label: "Anthropic API key",
    hint: "sk-ant-... key from console.anthropic.com",
    groupId: "anthropic" as AuthChoiceGroupId,
    groupLabel: "Anthropic",
    groupHint: "setup-token + API key",
  },
  // ── OpenAI ──
  {
    value: "openai-codex" as AuthChoice,
    label: "OpenAI Codex OAuth",
    hint: "Browser login — no API key needed",
    groupId: "openai" as AuthChoiceGroupId,
    groupLabel: "OpenAI",
    groupHint: "Codex OAuth + API key",
  },
  {
    value: "openai-api-key" as AuthChoice,
    label: "OpenAI API key",
    hint: "sk-... key from platform.openai.com",
    groupId: "openai" as AuthChoiceGroupId,
    groupLabel: "OpenAI",
    groupHint: "Codex OAuth + API key",
  },
  // ── Google ──
  {
    value: "google-gemini-cli" as AuthChoice,
    label: "Google Gemini CLI OAuth",
    hint: "Browser login — no API key needed",
    groupId: "google" as AuthChoiceGroupId,
    groupLabel: "Google",
    groupHint: "Gemini API key + OAuth",
  },
  {
    value: "gemini-api-key" as AuthChoice,
    label: "Gemini API key",
    hint: "API key from aistudio.google.com",
    groupId: "google" as AuthChoiceGroupId,
    groupLabel: "Google",
    groupHint: "Gemini API key + OAuth",
  },
  // ── Other providers ──
  {
    value: "chutes",
    label: "Chutes (OAuth)",
    groupId: "chutes",
    groupLabel: "Chutes",
    groupHint: "OAuth",
  },
  {
    value: "ollama" as AuthChoice,
    label: "Ollama (local)",
    hint: "Local LLM server",
    groupId: "ollama" as AuthChoiceGroupId,
    groupLabel: "Ollama",
    groupHint: "Local models",
  },
  {
    value: "litellm-api-key",
    label: "LiteLLM API key",
    hint: "Unified gateway for 100+ LLM providers",
    groupId: "litellm",
    groupLabel: "LiteLLM",
    groupHint: "Unified LLM gateway (100+ providers)",
  },
  {
    value: "custom-api-key",
    label: "Custom Provider",
    hint: "Any OpenAI or Anthropic compatible endpoint",
    groupId: "custom",
    groupLabel: "Custom Provider",
    groupHint: "Any OpenAI or Anthropic compatible endpoint",
  },
];

export function formatStaticAuthChoiceChoicesForCli(params?: {
  includeSkip?: boolean;
  includeLegacyAliases?: boolean;
}): string {
  const includeSkip = params?.includeSkip ?? true;
  const includeLegacyAliases = params?.includeLegacyAliases ?? false;
  const values = CORE_AUTH_CHOICE_OPTIONS.map((opt) => opt.value);

  if (includeSkip) {
    values.push("skip");
  }
  if (includeLegacyAliases) {
    values.push(...AUTH_CHOICE_LEGACY_ALIASES_FOR_CLI);
  }

  return values.join("|");
}
