import hashlib
import logging
from typing import Dict, Tuple, Optional

_registry_logger = logging.getLogger('mirofish.prompt_registry')

_registry: Dict[str, Tuple[str, str, str]] = {}  # name -> (text, version, hash)

def _compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]

def register(name: str, text: str, version: str):
    _registry[name] = (text, version, _compute_hash(text))

def get_prompt(name: str) -> Tuple[str, str, str]:
    """Returns (text, version, hash) or raises KeyError."""
    return _registry[name]

def get_all_hashes() -> Dict[str, str]:
    """Returns {name: hash} for all registered prompts. Used in backtest logging."""
    return {name: h for name, (_, _, h) in _registry.items()}

def get_snapshot() -> Dict[str, Dict]:
    """Full snapshot for logging: {name: {version, hash}}."""
    return {name: {"version": v, "hash": h} for name, (_, v, h) in _registry.items()}

# Auto-register all prompts on import
def _auto_register():
    from ..prompts import council_scoring, research_synthesis, fact_check, oasis_event, swarm_persona, deliberation
    for mod in [council_scoring, research_synthesis, fact_check, oasis_event, swarm_persona, deliberation]:
        name = mod.__name__.rsplit('.', 1)[-1]
        register(name, mod.PROMPT, mod.VERSION)

try:
    _auto_register()
except Exception as e:
    _registry_logger.error(
        f"[PromptRegistry] Auto-registration failed: {e}. "
        "All prompts will be unavailable — any call to get_prompt() will raise KeyError."
    )
