"""DeepWorm - AI-powered deep research agent."""

import logging

__version__ = "0.1.0"

from .async_api import AsyncResearcher, async_research
from .events import Event, EventEmitter, EventType
from .researcher import DeepResearcher

__all__ = [
    "AsyncResearcher",
    "DeepResearcher",
    "Event",
    "EventEmitter",
    "EventType",
    "__version__",
    "async_research",
    "research",
]

# Set up default logging (NullHandler to avoid "No handlers" warnings)
logging.getLogger("deepworm").addHandler(logging.NullHandler())


def research(topic: str, **kwargs) -> str:
    """Quick research function. Returns a markdown report.

    Usage:
        from deepworm import research
        report = research("quantum computing advances in 2024")
    """
    researcher = DeepResearcher(**kwargs)
    return researcher.research(topic)
