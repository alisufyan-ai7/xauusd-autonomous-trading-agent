"""Execution-disabled XAUUSD production candidate.

The package intentionally contains no live order capability.  A separately
packaged and separately approved adapter would be required for any future
demo or live execution.
"""

from .config import RuntimeConfig, RuntimeMode

__all__ = ["RuntimeConfig", "RuntimeMode"]
__version__ = "0.1.0.dev0"
