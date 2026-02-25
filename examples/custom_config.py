"""Example: Custom configuration with Ollama."""

from deepworm import DeepResearcher
from deepworm.config import Config

config = Config(
    provider="ollama",
    model="llama3.2",
    depth=3,       # 3 iterations of research
    breadth=5,     # 5 search queries per iteration
    max_sources=8, # fetch up to 8 sources per query batch
)

researcher = DeepResearcher(config=config)
report = researcher.research("comparison of Python web frameworks in 2024")

# Save to file
from deepworm.report import save_report
path = save_report(report, topic="python-web-frameworks")
print(f"Report saved to {path}")
