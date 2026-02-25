"""Example: Save research to file with custom settings."""

import sys
from deepworm import DeepResearcher
from deepworm.config import Config
from deepworm.report import save_report

topic = sys.argv[1] if len(sys.argv) > 1 else "latest trends in AI agents 2024"

config = Config.auto()
config.depth = 3  # deeper research

researcher = DeepResearcher(config=config)

print(f"Researching: {topic}")
print(f"Using: {config.provider} / {config.model}")

report = researcher.research(topic)

path = save_report(report, topic=topic)
print(f"\nSaved to: {path}")
