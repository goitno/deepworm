"""Example: Using the async API for concurrent research.

This example shows how to run multiple research tasks concurrently
using Python's asyncio, which is much faster than sequential research.
"""

import asyncio

from deepworm import async_research
from deepworm.config import Config


async def main():
    config = Config.auto()
    config.depth = 1  # keep it fast for the example

    topics = [
        "Quantum computing applications in drug discovery",
        "Latest advances in fusion energy",
        "Impact of AI on software engineering jobs",
    ]

    print(f"Researching {len(topics)} topics concurrently...\n")

    # Launch all research tasks concurrently
    tasks = [async_research(topic, config=config) for topic in topics]
    reports = await asyncio.gather(*tasks)

    for topic, report in zip(topics, reports):
        print(f"{'=' * 60}")
        print(f"Topic: {topic}")
        print(f"{'=' * 60}")
        # Print first 300 chars of each report
        print(report[:300] + "...\n")


if __name__ == "__main__":
    asyncio.run(main())
