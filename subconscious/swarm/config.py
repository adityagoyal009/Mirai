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
        os.path.expanduser('~'), '.openclaw', 'openclaw.json'
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
        try:
            if not os.path.exists(cls.GATEWAY_CONFIG_PATH):
                return []
            with open(cls.GATEWAY_CONFIG_PATH, 'r') as f:
                config = json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

        models_cfg = config.get('models', {})
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
