export const MIRAI_CLI_ENV_VAR = "MIRAI_CLI";
export const MIRAI_CLI_ENV_VALUE = "1";

export function markMiraiExecEnv<T extends Record<string, string | undefined>>(env: T): T {
  return {
    ...env,
    [MIRAI_CLI_ENV_VAR]: MIRAI_CLI_ENV_VALUE,
  };
}

export function ensureMiraiExecMarkerOnProcess(
  env: NodeJS.ProcessEnv = process.env,
): NodeJS.ProcessEnv {
  env[MIRAI_CLI_ENV_VAR] = MIRAI_CLI_ENV_VALUE;
  return env;
}
