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
    # Default: route through OpenClaw gateway (local proxy → Claude Opus via OAuth, zero cost)
    # Override with env vars to use a different provider
    LLM_API_KEY = os.environ.get('LLM_API_KEY', 'openclaw')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'http://localhost:3000/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'anthropic/claude-opus-4-6')

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

    # ── OpenClaw configuration ───────────────────────────────────
    OPENCLAW_GATEWAY_PORT = int(os.environ.get('OPENCLAW_GATEWAY_PORT', '3000'))
    OPENCLAW_GATEWAY_URL = os.environ.get(
        'OPENCLAW_GATEWAY_URL',
        f'http://localhost:{os.environ.get("OPENCLAW_GATEWAY_PORT", "3000")}'
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

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []
        if not cls.LLM_API_KEY:
            errors.append("LLM_API_KEY not configured (set env var or run 'openclaw gateway')")
        return errors
