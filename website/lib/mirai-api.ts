export const MIRAI_API_INTERNAL =
  process.env.MIRAI_API_INTERNAL_URL || "http://127.0.0.1:5000";

export const MIRAI_API_PUBLIC =
  process.env.MIRAI_API_PUBLIC_URL ||
  process.env.MIRAI_API_URL ||
  MIRAI_API_INTERNAL;

export function getMiraiInternalApiKey(): string {
  return (process.env.MIRAI_INTERNAL_API_KEY || "").trim();
}

export function miraiInternalHeaders(): Record<string, string> {
  const internalKey = getMiraiInternalApiKey();
  return internalKey ? { "x-internal-key": internalKey } : {};
}

export function miraiJsonHeaders(): Record<string, string> {
  return {
    "Content-Type": "application/json",
    ...miraiInternalHeaders(),
  };
}
