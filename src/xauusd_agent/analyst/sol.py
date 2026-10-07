"""Named Sol boundary with no provider transport implementation.

``SolAnalystAdapter`` deliberately adds no capability to ``AnalystClient``.  It
exists so composition code can name the frozen role without importing or
depending on an OpenAI SDK.  Its default transport remains disabled; only the
offline fake transport is available in this package.
"""

from .client import AnalystClient


class SolAnalystAdapter(AnalystClient):
    """Non-authoritative Sol adapter; unavailable by default."""
