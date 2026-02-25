"""DeepWorm - AI-powered deep research agent."""

import logging

__version__ = "0.1.0"

from .researcher import DeepResearcher

__all__ = ["DeepResearcher", "__version__"]

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
