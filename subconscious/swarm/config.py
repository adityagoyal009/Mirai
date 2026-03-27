"""
Configuration Management
Loads configuration from the project root .env file
"""

import os
from dotenv import load_dotenv

# Load the .env file from the project root
# Path: MiroFish/.env (relative to backend/app/config.py)
project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(project_root_env):
    load_dotenv(project_root_env, override=True)
else:
    # If root .env does not exist, try loading environment variables (for production)
    load_dotenv(override=True)


class Config:
    """Flask Configuration Class"""

    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mirofish-secret-key')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'

    # JSON configuration - disable ASCII escaping to display CJK characters directly (instead of \uXXXX format)
    JSON_AS_ASCII = False

    # LLM configuration (unified OpenAI format)
    # Auto-discovered from gateway config (~/.openclaw/openclaw.json)
    # Override with env vars if needed
    @staticmethod
    def _discover_gateway_llm():
        """Read gateway config to get auth token, port, and default model."""
        import json as _json
        config_path = os.path.join(os.path.expanduser('~'), '.openclaw', 'openclaw.json')
        try:
            with open(config_path, 'r') as f:
                config = _json.load(f)
            gw = config.get('gateway', {})
            port = gw.get('port', 3000)
            token = gw.get('auth', {}).get('token', '')
            model = config.get('agents', {}).get('defaults', {}).get('model', '')
            if token:
                return token, f'http://localhost:{port}/v1', model or 'anthropic/claude-opus-4-6'
        except (IOError, _json.JSONDecodeError, KeyError):
            pass
        return '', '', ''

    _gw_token, _gw_url, _gw_model = _discover_gateway_llm.__func__()

    LLM_API_KEY = os.environ.get('LLM_API_KEY', '') or _gw_token or 'openclaw'
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', '') or _gw_url or 'http://localhost:3000/v1'
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', '') or _gw_model or 'anthropic/claude-opus-4-6'

    # ChromaDB configuration (replaces Zep Cloud)
    CHROMADB_PERSIST_PATH = os.environ.get(
        'CHROMADB_PERSIST_PATH',
        os.path.join(os.path.dirname(__file__), '../../memory/.chromadb_data')
    )

    # ── SearXNG configuration ────────────────────────────────────
    SEARXNG_URL = os.environ.get('SEARXNG_URL', 'http://localhost:8888')

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
        "tier1": [  # Premium — Wave 1 individual calls
            {"model": "anthropic/claude-opus-4-6", "label": "Claude Opus 4.6", "cost_per_1k": 0.075},
            {"model": "openai/gpt-4o", "label": "GPT-4o", "cost_per_1k": 0.025},
        ],
        "tier2": [  # Standard — Wave 2 batches
            {"model": "anthropic/claude-sonnet-4-6", "label": "Claude Sonnet 4.6", "cost_per_1k": 0.015},
            {"model": "openai/gpt-4o-mini", "label": "GPT-4o-mini", "cost_per_1k": 0.0075},
            {"model": "google/gemini-2.5-pro", "label": "Gemini 2.5 Pro", "cost_per_1k": 0.01},
            {"model": "mistralai/mistral-large", "label": "Mistral Large", "cost_per_1k": 0.012},
            {"model": "x-ai/grok-3", "label": "Grok 3", "cost_per_1k": 0.01},
            {"model": "together/meta-llama/Meta-Llama-3.1-70B", "label": "Llama 3.1 70B", "cost_per_1k": 0.009},
        ],
        "tier3": [  # Cheap — volume batch agents
            {"model": "anthropic/claude-haiku-4-5", "label": "Claude Haiku 4.5", "cost_per_1k": 0.005},
            {"model": "google/gemini-2.5-flash", "label": "Gemini 2.5 Flash", "cost_per_1k": 0.003},
            {"model": "mistralai/mistral-small", "label": "Mistral Small", "cost_per_1k": 0.005},
        ],
    }

    @classmethod
    def get_tiered_models(cls) -> dict:
        """Get models per tier, filtered to only those available in gateway config."""
        available = cls.get_council_models()
        if not available:
            # Fallback: use gateway default for all tiers
            default = {
                'model': cls.LLM_MODEL_NAME, 'label': 'Default',
                'base_url': cls.LLM_BASE_URL, 'api_key': cls.LLM_API_KEY,
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
        except (json.JSONDecodeError, IOError):
            return []

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
                base_url = provider_cfg.get('baseUrl', cls.LLM_BASE_URL)
                api_key = cls._resolve_api_key(provider_cfg)
                result.append({
                    'model': model_id if '/' in model_id else f"{provider_key}/{model_id}",
                    'label': label,
                    'base_url': base_url,
                    'api_key': api_key,
                })
        else:
            # Fallback: use ALL providers with their first model
            for provider_key, provider_cfg in providers.items():
                base_url = provider_cfg.get('baseUrl', '')
                api_key = cls._resolve_api_key(provider_cfg)
                for model_def in provider_cfg.get('models', []):
                    model_id = model_def.get('id', '')
                    if model_id:
                        result.append({
                            'model': f"{provider_key}/{model_id}",
                            'label': model_def.get('name', model_id),
                            'base_url': base_url,
                            'api_key': api_key,
                        })

        return result

    @classmethod
    def get_swarm_models(cls) -> list:
        """
        Read swarm-specific models (fast models for persona agents).
        Falls back to council models if no swarm config exists.
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

        result = []
        for cm in swarm_models_raw:
            model_id = cm.get('model', '')
            label = cm.get('label', model_id)
            result.append({
                'model': model_id,
                'label': label,
                'base_url': cls.LLM_BASE_URL,
                'api_key': cls.LLM_API_KEY,
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
