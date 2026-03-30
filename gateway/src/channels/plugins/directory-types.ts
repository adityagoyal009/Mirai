import type { MiraiConfig } from "../../config/types.js";

export type DirectoryConfigParams = {
  cfg: MiraiConfig;
  accountId?: string | null;
  query?: string | null;
  limit?: number | null;
};
