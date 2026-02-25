"""Example: Export research to HTML with dark mode.

Shows how to generate a polished HTML report with responsive CSS
and automatic dark mode support.
"""

from deepworm import DeepResearcher
from deepworm.config import Config


def main():
    config = Config.auto()
    config.output_format = "html"
    config.output_file = "research_report.html"

    researcher = DeepResearcher(config=config)
    report = researcher.research("The future of WebAssembly")

    # The report is saved automatically to research_report.html
    # but you can also save it programmatically:
    from deepworm.report import save_report

    save_report(
        content=report,
        output_file="custom_report.html",
        output_format="html",
    )
    print("Reports saved!")
    print("  → research_report.html")
    print("  → custom_report.html")


if __name__ == "__main__":
    main()
