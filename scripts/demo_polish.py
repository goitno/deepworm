#!/usr/bin/env python3
"""Demo: --polish pipeline (readability + compliance + scoring + annotations).

Usage:
    python3 scripts/demo_polish.py                    # Uses sample report
    python3 scripts/demo_polish.py report.md          # Uses your file
    python3 scripts/demo_polish.py --topic "AI safety" # Creates sample & analyzes
"""
import sys, os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "outputs")
sys.path.insert(0, ROOT_DIR)

os.makedirs(OUTPUT_DIR, exist_ok=True)

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from deepworm.readability import analyze_readability
from deepworm.compliance import check_compliance
from deepworm.scoring import score_report
from deepworm.annotations import auto_annotate

console = Console()

# --- Input handling ---
report_text = None
label = "sample"

if len(sys.argv) > 1:
    if sys.argv[1] == "--topic":
        topic = sys.argv[2] if len(sys.argv) > 2 else "sample topic"
        label = topic.replace(" ", "_")[:30]
        report_text = f"""# Research: {topic}

## Introduction

{topic} is a subject of growing interest among researchers and practitioners.
Many experts believe it will significantly impact the field in coming years.

## Key Findings

Recent studies suggest that {topic} has several important dimensions.
Some research indicates approximately 65% adoption rate in certain sectors.
The implications are being studied across multiple disciplines.

## Analysis

The current state of {topic} reveals both opportunities and challenges.
It is generally accepted that more research is needed in this area.

## Conclusion

{topic} remains an active area of investigation with significant potential.

## Sources

1. [Example Study](https://example.com/study1)
2. [Research Paper](https://example.com/paper2)
"""
    else:
        filepath = sys.argv[1]
        if os.path.exists(filepath):
            report_text = open(filepath, encoding="utf-8").read()
            label = os.path.splitext(os.path.basename(filepath))[0]
        else:
            console.print(f"[red]Error: File not found: {filepath}[/red]")
            sys.exit(1)

if report_text is None:
    sample = os.path.join(OUTPUT_DIR, "sample_report.md")
    if os.path.exists(sample):
        report_text = open(sample, encoding="utf-8").read()
    elif os.path.exists("/tmp/sample_report.md"):
        report_text = open("/tmp/sample_report.md", encoding="utf-8").read()
    else:
        console.print("[red]Error: No report file found. Use: python3 demo_polish.py <file.md>[/red]")
        sys.exit(1)

out = []

def p(text=""):
    out.append(text)


# Header
console.print()
console.print(Panel("[bold]deepworm --polish demo[/bold]", border_style="blue", expand=False))
console.print()

# Step 1: Readability
ra = analyze_readability(report_text)
r_color = "green" if ra.flesch_reading_ease >= 60 else ("yellow" if ra.flesch_reading_ease >= 30 else "red")
console.print(f"  [bold]1.[/bold] Readability   [{r_color}]{ra.reading_level}[/{r_color}] (Flesch {ra.flesch_reading_ease:.0f})")
console.print(
    f"     Grade: {ra.grade_level} | "
    f"Fog: {ra.gunning_fog:.1f} | "
    f"Words: {ra.total_words:,} | "
    f"Vocab: {ra.vocabulary_richness:.0%}"
)
p(f"Readability: {ra.reading_level} (Flesch {ra.flesch_reading_ease:.0f})")
p(f"Grade: {ra.grade_level} | Fog: {ra.gunning_fog:.1f} | Words: {ra.total_words} | Vocab: {ra.vocabulary_richness:.0%}")

# Step 2: Compliance
cr = check_compliance(report_text)
status_text = "PASS" if cr.is_compliant else "FAIL"
status = "[green]PASS[/green]" if cr.is_compliant else "[red]FAIL[/red]"
console.print(f"\n  [bold]2.[/bold] Compliance   {status} ({cr.score:.0f}/100)")
p(f"\nCompliance: {status_text} ({cr.score:.0f}/100)")
p(f"Errors: {cr.error_count} | Warnings: {cr.warning_count}")
if cr.issues:
    console.print(
        f"     [red]{cr.error_count} errors[/red] | "
        f"[yellow]{cr.warning_count} warnings[/yellow] | "
        f"[dim]{len(cr.issues) - cr.error_count - cr.warning_count} info[/dim]"
    )
    for i in cr.issues[:5]:
        sev_color = {"error": "red", "warning": "yellow", "info": "dim", "suggestion": "cyan"}
        color = sev_color.get(i.severity.value, "dim")
        console.print(f"     [{color}]* {i.message}[/{color}]")
        p(f"  [{i.severity.value}] {i.message}")
    if len(cr.issues) > 5:
        console.print(f"     [dim]... +{len(cr.issues)-5} more[/dim]")

# Step 3: Quality
qs = score_report(report_text)
grade_color = "green" if qs.overall >= 0.8 else ("yellow" if qs.overall >= 0.6 else "red")
console.print(f"\n  [bold]3.[/bold] Quality      [{grade_color}]{qs.grade}[/{grade_color}] ({qs.overall:.0%})")
p(f"\nQuality: {qs.grade} ({qs.overall:.0%})")

dims = [
    ("Structure", qs.structure),
    ("Depth", qs.depth),
    ("Sources", qs.sources),
    ("Readability", qs.readability),
    ("Complete", qs.completeness),
]
for name, val in dims:
    bar_len = int(val * 20)
    bar = "#" * bar_len + "." * (20 - bar_len)
    bar_color = "green" if val >= 0.8 else ("yellow" if val >= 0.6 else "red")
    console.print(f"     {name:<12} [{bar_color}]{bar}[/{bar_color}] {val:.0%}")
    p(f"  {name}: {val:.0%}")

if qs.suggestions:
    p("")
    for s in qs.suggestions[:3]:
        p(f"  > {s}")

# Step 4: Annotations
anns = auto_annotate(report_text)
ann_count = len(anns.annotations)
if ann_count > 0:
    console.print(f"\n  [bold]4.[/bold] Annotations  [yellow]{ann_count} findings[/yellow]")
    p(f"\nAnnotations: {ann_count} findings")
    for a in anns.annotations:
        type_color = {
            "fact_check": "red", "warning": "yellow",
            "question": "cyan", "todo": "magenta",
        }
        color = type_color.get(a.annotation_type.value, "dim")
        target_str = ""
        if a.target:
            target_str = f" -> {a.target[:60]}"
        console.print(f"     [{color}]* [{a.annotation_type.value}] {a.text}{target_str}[/{color}]")
        p(f"  [{a.annotation_type.value}] {a.text}{target_str}")
else:
    console.print(f"\n  [bold]4.[/bold] Annotations  [green]No issues[/green]")
    p(f"\nAnnotations: 0 findings")

# Summary panel
console.print()
summary_tbl = Table(show_header=False, box=None, padding=(0, 2))
summary_tbl.add_column(style="bold")
summary_tbl.add_column()
summary_tbl.add_row("Quality", f"{qs.grade} ({qs.overall:.0%})")
summary_tbl.add_row("Compliance", f"{status_text} ({cr.score:.0f}/100)")
summary_tbl.add_row("Readability", f"{ra.reading_level} (Flesch {ra.flesch_reading_ease:.0f})")
summary_tbl.add_row("Annotations", f"{ann_count} findings")
console.print(Panel(summary_tbl, title="[bold cyan]Summary[/bold cyan]", border_style="cyan", expand=False))

outpath = os.path.join(OUTPUT_DIR, f"polish_{label}.txt")
with open(outpath, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
console.print(f"\n[green]Saved to {outpath}[/green]")
