export const MIRAI_API = process.env.MIRAI_API_URL || "http://127.0.0.1:5000";

export function getMiraiInternalApiKey(): string {
  return (
    process.env.MIRAI_INTERNAL_API_KEY ||
    process.env.NEXTAUTH_SECRET ||
    ""
  ).trim();
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
