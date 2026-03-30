"""
Configuration Management
Loads configuration from the project root .env file
"""

import logging
import os
from dotenv import load_dotenv

_config_logger = logging.getLogger('mirofish.config')

# Load the .env file from the project root
# Path: MiroFish/.env (relative to backend/app/config.py)
project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(project_root_env):
    load_dotenv(project_root_env, override=True)
else:
    # If root .env does not exist, try loading environment variables (for production)
    load_dotenv(override=True)


class Config:
    """Mirai Configuration Class"""

    # App configuration
    _secret_key_raw = os.environ.get('MIRAI_SECRET_KEY') or os.environ.get('SECRET_KEY')
    if _secret_key_raw:
        SECRET_KEY = _secret_key_raw
    else:
        SECRET_KEY = os.urandom(32).hex()
        _config_logger.warning(
            "[Config] SECRET_KEY not set — using random key. "
            "All sessions WILL be invalidated on every server restart. "
            "Set MIRAI_SECRET_KEY env var to fix this."
        )
    DEBUG = os.environ.get('MIRAI_DEBUG', os.environ.get('DEBUG', 'True')).lower() == 'true'

    # JSON configuration - disable ASCII escaping to display CJK characters directly (instead of \uXXXX format)
    JSON_AS_ASCII = False

    # LLM configuration — uses CLI headless calls (no proxy server needed)
    # Routes through Claude Code CLI, Codex CLI, and Gemini CLI subscriptions
    LLM_API_KEY = os.environ.get('LLM_API_KEY', '') or 'cli-mode'
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', '') or 'cli://local'
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', '') or 'claude-opus-4-6'

    # ChromaDB configuration (replaces Zep Cloud)
    CHROMADB_PERSIST_PATH = os.environ.get(
        'CHROMADB_PERSIST_PATH',
        os.path.join(os.path.dirname(__file__), '../../memory/.chromadb_data')
    )

    # SearXNG + Brave Search removed — all search via Claude CLI web search through gateway

    # ── Jina Grounding API (optional, for fact-checking) ──────
    JINA_API_KEY = os.environ.get('JINA_API_KEY', '')

    # ── Mem0 configuration ───────────────────────────────────────
    MEM0_API_KEY = os.environ.get('MEM0_API_KEY', '')
    MEM0_ORG_ID = os.environ.get('MEM0_ORG_ID', '')
    MEM0_USER_ID = os.environ.get('MEM0_USER_ID', 'mirai_bi')

    # ── OpenBB configuration ─────────────────────────────────────
    # OpenBB uses its own provider credentials (set via openbb CLI or env vars)
    OPENBB_ENABLED = os.environ.get('OPENBB_ENABLED', 'true').lower() == 'true'

    # ── E2B Sandbox configuration ────────────────────────────────
    E2B_API_KEY = os.environ.get('E2B_API_KEY', '')

    # ── Neo4j configuration (optional, for Mem0 graph store) ─────
    NEO4J_URL = os.environ.get('NEO4J_URL', '')
    NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
    NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', '')

    # ── Mirai Gateway configuration ───────────────────────────────
    MIRAI_GATEWAY_PORT = int(os.environ.get('MIRAI_GATEWAY_PORT',
                             os.environ.get('OPENCLAW_GATEWAY_PORT', '3000')))
    MIRAI_GATEWAY_URL = os.environ.get(
        'MIRAI_GATEWAY_URL',
        os.environ.get('OPENCLAW_GATEWAY_URL',
                       f'http://localhost:{os.environ.get("MIRAI_GATEWAY_PORT", os.environ.get("OPENCLAW_GATEWAY_PORT", "3000"))}')
    )

    # File upload configuration
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}

    # ── Model tiering for swarm cost optimization ──────────────
    # Tier 1 (premium): best reasoning, used for Wave 1 individual agents
    # Tier 2 (standard): good quality, used for Wave 2 batches
    # Tier 3 (cheap): volume diversity, used for large batch runs
    MODEL_TIERS = {
        "tier1": [  # Premium — Wave 1 individual calls (best quality)
            {"model": "claude-opus-4-6", "label": "Claude Opus 4.6", "cost_per_1k": 0},
            {"model": "gpt-5.4", "label": "GPT-5.4", "cost_per_1k": 0},
            {"model": "claude-sonnet-4-6", "label": "Claude Sonnet 4.6", "cost_per_1k": 0},
        ],
        "tier2": [  # Standard — Wave 2 batches
            {"model": "claude-sonnet-4-6", "label": "Claude Sonnet 4.6", "cost_per_1k": 0},
            {"model": "gpt-5.4", "label": "GPT-5.4", "cost_per_1k": 0},
        ],
        "tier3": [  # Volume batch agents
            {"model": "claude-sonnet-4-6", "label": "Claude Sonnet 4.6", "cost_per_1k": 0},
        ],
    }

    @classmethod
    def get_tiered_models(cls) -> dict:
        """Get models per tier, filtered to only those available in gateway config."""
        available = cls.get_council_models()
        if not available:
            # Fallback: use default model via CLI
            default = {
                'model': cls.LLM_MODEL_NAME, 'label': 'Default',
                'provider': 'claude', 'cli': 'claude',
            }
            return {"tier1": [default], "tier2": [default], "tier3": [default]}

        available_ids = {m['model'] for m in available}
        available_map = {m['model']: m for m in available}

        result = {}
        for tier, models in cls.MODEL_TIERS.items():
            matched = [available_map[m['model']] for m in models if m['model'] in available_ids]
            if not matched:
                # Fallback: use all available models for this tier
                matched = available
            result[tier] = matched

        return result

    @classmethod
    def estimate_cost(cls, agent_count: int) -> dict:
        """Estimate API cost for a swarm run."""
        wave1 = min(agent_count, 100)
        wave2 = agent_count - wave1
        batches = (wave2 + 24) // 25 if wave2 > 0 else 0

        tier1_cost = sum(m.get('cost_per_1k', 0.05) for m in cls.MODEL_TIERS['tier1']) / len(cls.MODEL_TIERS['tier1'])
        tier2_cost = sum(m.get('cost_per_1k', 0.01) for m in cls.MODEL_TIERS['tier2']) / len(cls.MODEL_TIERS['tier2'])

        est_wave1 = wave1 * tier1_cost * 2  # ~2K tokens per call
        est_wave2 = batches * tier2_cost * 4  # ~4K tokens per batch

        return {
            "wave1_calls": wave1,
            "wave2_batches": batches,
            "estimated_cost_usd": round(est_wave1 + est_wave2, 2),
            "breakdown": {"wave1": round(est_wave1, 2), "wave2": round(est_wave2, 2)},
        }

    # Text processing configuration
    DEFAULT_CHUNK_SIZE = 500  # Default chunk size
    DEFAULT_CHUNK_OVERLAP = 50  # Default overlap size

    # OASIS simulation configuration
    OASIS_DEFAULT_MAX_ROUNDS = int(os.environ.get('OASIS_DEFAULT_MAX_ROUNDS', '10'))
    OASIS_SIMULATION_DATA_DIR = os.path.join(os.path.dirname(__file__), '../uploads/simulations')

    # OASIS platform available actions configuration
    OASIS_TWITTER_ACTIONS = [
        'CREATE_POST', 'LIKE_POST', 'REPOST', 'FOLLOW', 'DO_NOTHING', 'QUOTE_POST'
    ]
    OASIS_REDDIT_ACTIONS = [
        'LIKE_POST', 'DISLIKE_POST', 'CREATE_POST', 'CREATE_COMMENT',
        'LIKE_COMMENT', 'DISLIKE_COMMENT', 'SEARCH_POSTS', 'SEARCH_USER',
        'TREND', 'REFRESH', 'DO_NOTHING', 'FOLLOW', 'MUTE'
    ]

    # Report Agent configuration
    REPORT_AGENT_MAX_TOOL_CALLS = int(os.environ.get('REPORT_AGENT_MAX_TOOL_CALLS', '5'))
    REPORT_AGENT_MAX_REFLECTION_ROUNDS = int(os.environ.get('REPORT_AGENT_MAX_REFLECTION_ROUNDS', '2'))
    REPORT_AGENT_TEMPERATURE = float(os.environ.get('REPORT_AGENT_TEMPERATURE', '0.5'))

    # ── Council model discovery ──────────────────────────────────
    GATEWAY_CONFIG_PATH = os.path.join(
        os.path.expanduser('~'), '.mirai', 'mirai.json'
    )
    COUNCIL_CONFIG_PATH = os.path.join(
        os.path.expanduser('~'), '.mirai', 'council.json'
    )

    @classmethod
    def get_council_models(cls) -> list:
        """
        Read council models from gateway config (~/.openclaw/openclaw.json).
        Checks models.council.models first (explicit list).
        Falls back to all models.providers entries.
        Returns list of dicts: [{model, label, base_url, api_key}, ...]
        """
        import json
        # Read council config from dedicated council.json
        config = {}
        try:
            if os.path.exists(cls.COUNCIL_CONFIG_PATH):
                with open(cls.COUNCIL_CONFIG_PATH, 'r') as f:
                    config = json.load(f)
            elif os.path.exists(cls.GATEWAY_CONFIG_PATH):
                with open(cls.GATEWAY_CONFIG_PATH, 'r') as f:
                    config = json.load(f)
            else:
                return []
        except (json.JSONDecodeError, IOError) as e:
            _config_logger.error(
                f"[Config] Failed to parse council config — analysis will have no council models. "
                f"Error: {e}"
            )
            raise

        models_cfg = config.get('models', config)
        providers = models_cfg.get('providers', {})

        # Explicit council list
        council_cfg = models_cfg.get('council', {})
        council_models_raw = council_cfg.get('models', [])

        result = []
        if council_models_raw:
            for cm in council_models_raw:
                provider_key = cm.get('provider', '')
                model_id = cm.get('model', '')
                label = cm.get('label', f"{provider_key}/{model_id}")
                provider_cfg = providers.get(provider_key, {})
                entry = {
                    'model': model_id,
                    'label': label,
                    'provider': provider_key,
                    'cli': provider_cfg.get('cli', provider_key),
                }
                # Pass through optional fields
                if cm.get('system_prompt_suffix'):
                    entry['system_prompt_suffix'] = cm['system_prompt_suffix']
                result.append(entry)
        else:
            # Fallback: use ALL providers with their first model
            for provider_key, provider_cfg in providers.items():
                for model_def in provider_cfg.get('models', []):
                    model_id = model_def.get('id', '')
                    if model_id:
                        result.append({
                            'model': model_id,
                            'label': model_def.get('name', model_id),
                            'provider': provider_key,
                            'cli': provider_cfg.get('cli', provider_key),
                        })

        return result

    @classmethod
    def get_swarm_models(cls) -> list:
        """
        Read swarm-specific models (fast models for persona agents).
        Falls back to council models if no swarm config exists.
        Resolves provider base_url and api_key from council.json providers.
        """
        import json
        try:
            if os.path.exists(cls.COUNCIL_CONFIG_PATH):
                with open(cls.COUNCIL_CONFIG_PATH, 'r') as f:
                    config = json.load(f)
            else:
                return cls.get_council_models()
        except (json.JSONDecodeError, IOError):
            return cls.get_council_models()

        swarm_cfg = config.get('swarm', {})
        swarm_models_raw = swarm_cfg.get('models', [])
        if not swarm_models_raw:
            return cls.get_council_models()

        # Build provider lookup from council.json for base_url / api_key resolution
        providers = config.get('models', config).get('providers', {})

        result = []
        for cm in swarm_models_raw:
            model_id = cm.get('model', '')
            label = cm.get('label', model_id)
            provider_key = cm.get('provider', '')
            provider_cfg = providers.get(provider_key, {})
            result.append({
                'model': model_id,
                'label': label,
                'provider': provider_key,
                'cli': provider_cfg.get('cli', provider_key),
            })
        return result

    @classmethod
    def _resolve_api_key(cls, provider_cfg: dict) -> str:
        """Resolve apiKey from provider config, handling SecretRef env sources."""
        api_key = provider_cfg.get('apiKey', '')
        if isinstance(api_key, dict):
            if api_key.get('source') == 'env':
                return os.environ.get(api_key.get('id', ''), cls.LLM_API_KEY)
            return cls.LLM_API_KEY
        return str(api_key) if api_key else cls.LLM_API_KEY

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []
        if not cls.LLM_API_KEY:
            errors.append("LLM_API_KEY not configured (set env var or start the gateway: cd gateway && node mirai.mjs gateway run)")
        return errors


# ── Researcher model config helper ───────────────────────────────────────────
# Allows model strings to be overridden via ~/.mirai/research.json without
# code edits. Useful for swapping to newer models as they become available.
_RESEARCHER_MODEL_DEFAULTS = {
    "researcher_a": "claude-opus-4-6",
    "researcher_b": "claude-sonnet-4-6",
    "verifier": "gpt-5.4",
    "chairman": "claude-opus-4-6",
}

_RESEARCH_CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".mirai", "research.json")


def get_researcher_models() -> dict:
    """
    Return the researcher model configuration.

    Loads from ~/.mirai/research.json if it exists; otherwise returns defaults.
    Expected JSON format:
        {
            "researcher_a": "claude-opus-4-6",
            "researcher_b": "claude-sonnet-4-6",
            "verifier": "gpt-5.4",
            "chairman": "claude-opus-4-6"
        }

    Returns:
        dict with keys: researcher_a, researcher_b, verifier, chairman
    """
    import json
    config = dict(_RESEARCHER_MODEL_DEFAULTS)
    try:
        if os.path.exists(_RESEARCH_CONFIG_PATH):
            with open(_RESEARCH_CONFIG_PATH, "r") as f:
                overrides = json.load(f)
            # Only override known keys; ignore unknown entries
            for key in _RESEARCHER_MODEL_DEFAULTS:
                if key in overrides and isinstance(overrides[key], str) and overrides[key].strip():
                    config[key] = overrides[key].strip()
    except (json.JSONDecodeError, IOError, OSError) as e:
        logging.getLogger('mirofish.config').info(
            f"[Config] Using default researcher models (research.json unreadable: {e})"
        )
    return config
