#!/usr/bin/env python3
"""Demo: Full research pipeline (search + analyze + polish + graph).

This script runs REAL web research using DuckDuckGo + LLM API.
Requires: API key environment variable (GOOGLE_API_KEY, OPENAI_API_KEY, etc.)

Usage:
    export GOOGLE_API_KEY="your_key"
    python3 scripts/demo_research.py "bitcoin price prediction 2027"
    python3 scripts/demo_research.py "AI safety" gemini-2.0-flash
    python3 scripts/demo_research.py "WebAssembly" gemini-2.5-flash 2

Args:
    $1  Topic to research (required)
    $2  Model name (default: gemini-2.5-flash)
    $3  Depth (default: 1, higher = more iterations = more API calls)

Output saved to: scripts/outputs/research_<topic>.md
Polish analysis:  scripts/outputs/polish_research_<topic>.txt
Knowledge graph:  scripts/outputs/graph_research_<topic>.{mmd,dot,json}

Tip: depth=1 breadth=1 uses ~5 API calls. Free tier = 20/day.
"""
import subprocess, sys, os, time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

sys.path.insert(0, ROOT_DIR)

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# --- Args ---
if len(sys.argv) < 2:
    console.print(Panel(
        "[bold]Usage:[/bold]\n"
        "  python3 scripts/demo_research.py \"your topic\" [model] [depth]\n\n"
        "[bold]Examples:[/bold]\n"
        '  python3 scripts/demo_research.py "bitcoin price 2027"\n'
        '  python3 scripts/demo_research.py "AI safety" gemini-2.0-flash\n'
        '  python3 scripts/demo_research.py "WebAssembly" gemini-2.5-flash 2\n\n'
        "[bold]Requires:[/bold] export GOOGLE_API_KEY=your_key",
        title="deepworm research demo",
        border_style="blue",
    ))
    sys.exit(1)

topic = sys.argv[1]
model = sys.argv[2] if len(sys.argv) > 2 else "gemini-2.5-flash"
depth = sys.argv[3] if len(sys.argv) > 3 else "1"

if not os.environ.get("GOOGLE_API_KEY") and not os.environ.get("OPENAI_API_KEY") and not os.environ.get("ANTHROPIC_API_KEY"):
    console.print("[red]Error: No API key found[/red]")
    console.print("[dim]Set one of: GOOGLE_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY[/dim]")
    sys.exit(1)

label = topic.replace(" ", "_")[:40]
report_file = os.path.join(OUTPUT_DIR, f"research_{label}.md")

# Header
config_tbl = Table(show_header=False, box=None, padding=(0, 2))
config_tbl.add_column(style="bold")
config_tbl.add_column()
config_tbl.add_row("Topic", topic)
config_tbl.add_row("Model", model)
config_tbl.add_row("Depth", depth)
config_tbl.add_row("Output", report_file)
console.print()
console.print(Panel(config_tbl, title="[bold]deepworm research[/bold]", border_style="blue"))
console.print()

t_start = time.time()

# --- Step 1: Run research ---
cmd = [
    sys.executable, "-m", "deepworm",
    topic,
    "-d", depth,
    "-b", "2",
    "-m", model,
    "-o", report_file,
    "--score",
    "--stats",
    "--metrics",
]

console.print("[bold cyan]Step 1/3[/bold cyan] Running research...")
console.print()
result = subprocess.run(cmd, env={**os.environ})

if not os.path.exists(report_file):
    t_elapsed = time.time() - t_start
    console.print(f"\n[red]Research failed[/red] (exit code: {result.returncode}, {t_elapsed:.1f}s)")
    console.print("[dim]Possible causes:[/dim]")
    console.print("[dim]  - API quota exhausted (20 req/day on free tier)[/dim]")
    console.print("[dim]  - Try different model: gemini-2.0-flash or gemini-3-flash-preview[/dim]")
    sys.exit(1)

report = open(report_file, encoding="utf-8").read()
console.print(f"\n[green]Report saved:[/green] {len(report):,} chars, {len(report.splitlines())} lines")

# --- Step 2: Polish analysis ---
from deepworm.readability import analyze_readability
from deepworm.compliance import check_compliance
from deepworm.scoring import score_report
from deepworm.annotations import auto_annotate

console.print(f"\n[bold cyan]Step 2/3[/bold cyan] Polish pipeline...")

ra = analyze_readability(report)
cr = check_compliance(report)
qs = score_report(report)
anns = auto_annotate(report)

status_text = "PASS" if cr.is_compliant else "FAIL"
r_color = "green" if ra.flesch_reading_ease >= 60 else ("yellow" if ra.flesch_reading_ease >= 30 else "red")
grade_color = "green" if qs.overall >= 0.8 else ("yellow" if qs.overall >= 0.6 else "red")

console.print(f"  Readability:  [{r_color}]{ra.reading_level}[/{r_color}] (Flesch {ra.flesch_reading_ease:.0f})")
console.print(f"  Compliance:   {'[green]PASS[/green]' if cr.is_compliant else '[red]FAIL[/red]'} ({cr.score:.0f}/100)")
console.print(f"  Quality:      [{grade_color}]{qs.grade}[/{grade_color}] ({qs.overall:.0%})")
console.print(f"  Annotations:  {len(anns.annotations)} findings")

polish_file = os.path.join(OUTPUT_DIR, f"polish_research_{label}.txt")
with open(polish_file, "w", encoding="utf-8") as f:
    f.write(f"Quality: {qs.grade} ({qs.overall:.0%})\n")
    f.write(f"Compliance: {status_text} ({cr.score:.0f}/100)\n")
    f.write(f"Readability: {ra.reading_level}\n")
    f.write(f"Annotations: {len(anns.annotations)}\n\n")
    f.write(ra.to_markdown() + "\n\n")
    f.write(cr.to_markdown() + "\n")

# --- Step 3: Knowledge graph ---
from deepworm.graph import extract_concept_graph, extract_link_graph, merge_graphs
import json

console.print(f"\n[bold cyan]Step 3/3[/bold cyan] Knowledge graph...")

cg = extract_concept_graph(report)
lg = extract_link_graph(report)
graph = merge_graphs(cg, lg)
graph.name = label
gs = graph.stats()

console.print(f"  Nodes: {gs.node_count} | Edges: {gs.edge_count} | Components: {gs.components}")

mmd_file = os.path.join(OUTPUT_DIR, f"graph_research_{label}.mmd")
dot_file = os.path.join(OUTPUT_DIR, f"graph_research_{label}.dot")
json_file = os.path.join(OUTPUT_DIR, f"graph_research_{label}.json")

with open(mmd_file, "w") as f:
    f.write(graph.to_mermaid())
with open(dot_file, "w") as f:
    f.write(graph.to_dot())
with open(json_file, "w") as f:
    json.dump(graph.to_dict(), f, indent=2)

# --- Final summary ---
t_total = time.time() - t_start

summary_tbl = Table(show_header=False, box=None, padding=(0, 2))
summary_tbl.add_column(style="bold")
summary_tbl.add_column()
summary_tbl.add_row("Time", f"{t_total:.1f}s")
summary_tbl.add_row("Report", report_file)
summary_tbl.add_row("Quality", f"{qs.grade} ({qs.overall:.0%})")
summary_tbl.add_row("Compliance", f"{status_text} ({cr.score:.0f}/100)")
summary_tbl.add_row("Readability", ra.reading_level)
summary_tbl.add_row("Graph", f"{gs.node_count} nodes, {gs.edge_count} edges")
summary_tbl.add_row("", "")
summary_tbl.add_row("Files", report_file)
summary_tbl.add_row("", polish_file)
summary_tbl.add_row("", mmd_file)
summary_tbl.add_row("", dot_file)
summary_tbl.add_row("", json_file)

console.print()
console.print(Panel(summary_tbl, title="[bold green]Research Complete[/bold green]", border_style="green"))
