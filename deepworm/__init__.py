"""DeepWorm - AI-powered deep research agent."""

__version__ = "0.1.0"

from .researcher import DeepResearcher

__all__ = ["DeepResearcher", "__version__"]


def research(topic: str, **kwargs) -> str:
    """Quick research function. Returns a markdown report.

    Usage:
        from deepworm import research
        report = research("quantum computing advances in 2024")
    """
    researcher = DeepResearcher(**kwargs)
    return researcher.research(topic)
