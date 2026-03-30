"""
Source credibility utilities for search result scoring.

Used by agentic_researcher.py and brave_search.py.
SearXNG SearchEngine class removed — all search goes through
the Agentic Researcher + Gateway Brave API.
"""

from ..utils.logger import get_logger

logger = get_logger('mirofish.search_engine')

# Source credibility weighting — premium sources get boosted scores
SOURCE_CREDIBILITY = {
    # Tier 1: Premium research/data (3x)
    'gartner.com': 3.0, 'forrester.com': 3.0, 'mckinsey.com': 3.0,
    'pitchbook.com': 3.0, 'crunchbase.com': 2.5, 'cbinsights.com': 3.0,
    'sec.gov': 3.0, 'bloomberg.com': 3.0, 'reuters.com': 2.5,
    'techcrunch.com': 2.0, 'theinformation.com': 2.5,
    # Tier 2: Established (2x)
    'harvard.edu': 2.0, 'mit.edu': 2.0, 'stanford.edu': 2.0,
    'wsj.com': 2.0, 'ft.com': 2.0, 'economist.com': 2.0,
    'nature.com': 2.0, 'science.org': 2.0,
    'statista.com': 2.0, 'ibisworld.com': 2.0,
    # Tier 3: Good general (1.5x)
    'wikipedia.org': 1.5, 'investopedia.com': 1.5,
    'forbes.com': 1.5, 'inc.com': 1.5, 'wired.com': 1.5,
    # Tier 4: Government/regulatory (2.5x)
    'epa.gov': 2.5, 'fda.gov': 2.5, 'usda.gov': 2.5,
    'regulations.gov': 2.5, 'congress.gov': 2.0,
}


def _extract_root_domain(url: str) -> str:
    """Extract root domain from URL using urlparse for exact matching."""
    try:
        from urllib.parse import urlparse
        hostname = urlparse(url).hostname or ''
        if hostname.startswith('www.'):
            hostname = hostname[4:]
        return hostname
    except Exception:
        return ''


def _apply_credibility_weights(results: list) -> list:
    """Apply domain-based credibility weighting to search results."""
    total = len(results) or 1
    for i, r in enumerate(results):
        domain = _extract_root_domain(r.get('url', ''))
        weight = 1.0
        for known_domain, w in SOURCE_CREDIBILITY.items():
            if domain == known_domain or domain.endswith('.' + known_domain):
                weight = w
                break
        r['credibility_weight'] = weight

        raw_score = r.get('score', 0) or 0
        if raw_score > 0:
            r['score'] = raw_score * weight
        else:
            base_score = 1.0 - (i / total) * 0.5
            r['score'] = base_score * weight

    results.sort(key=lambda x: x.get('score', 0), reverse=True)
    return results


# Stub for backward compatibility — any code that tries SearchEngine()
# will get an object that returns empty results instead of crashing.
class SearchEngine:
    """Stub — SearXNG removed. Returns empty results."""
    def __init__(self, *a, **kw):
        logger.warning(
            "[SearchEngine] SearchEngine is a stub — SearXNG has been removed. "
            "Use BraveSearchEngine instead. All search calls will return empty results."
        )
    def is_available(self):
        return False
    def search(self, *a, **kw):
        return []
    def search_news(self, *a, **kw):
        return []
    def search_batch(self, *a, **kw):
        return {}
    def get_urls_for_query(self, *a, **kw):
        return []
