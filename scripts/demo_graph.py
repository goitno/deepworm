#!/usr/bin/env python3
"""Demo: --graph knowledge graph extraction.

Usage:
    python3 scripts/demo_graph.py                       # Uses sample report
    python3 scripts/demo_graph.py report.md             # Uses your file
    python3 scripts/demo_graph.py --topic "AI safety"   # Creates sample & graphs
"""
import sys, os, json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "outputs")
sys.path.insert(0, ROOT_DIR)

os.makedirs(OUTPUT_DIR, exist_ok=True)

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from deepworm.graph import extract_concept_graph, extract_link_graph, merge_graphs

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

{topic} is a subject of growing interest. This report examines the key aspects.

## Background

The history of {topic} spans several decades of development.

### Early Development

Initial work on {topic} began in academic institutions.
See [Original Paper](https://example.com/paper1) for details.

### Modern Era

Recent advances have transformed the field.
Key reference: [Modern Survey](https://example.com/survey2)

## Key Findings

### Finding 1: Performance

Performance improvements are significant ([Benchmark](https://example.com/bench)).

### Finding 2: Adoption

Adoption rates continue to grow ([Report](https://example.com/adoption)).

## Conclusion

{topic} has a promising future.

## Sources

1. [Source A](https://example.com/a)
2. [Source B](https://example.com/b)
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
        console.print("[red]Error: No report file found. Use: python3 demo_graph.py <file.md>[/red]")
        sys.exit(1)

# Header
console.print()
console.print(Panel("[bold]deepworm --graph demo[/bold]", border_style="blue", expand=False))
console.print()

# Extract graphs
cg = extract_concept_graph(report_text)
lg = extract_link_graph(report_text)
graph = merge_graphs(cg, lg)
graph.name = label

gs = graph.stats()

# Stats panel
stats_tbl = Table(show_header=False, box=None, padding=(0, 2))
stats_tbl.add_column(style="bold")
stats_tbl.add_column()
stats_tbl.add_row("Nodes", str(gs.node_count))
stats_tbl.add_row("Edges", str(gs.edge_count))
stats_tbl.add_row("Components", str(gs.components))
stats_tbl.add_row("Density", f"{gs.density:.3f}")
stats_tbl.add_row("Avg Degree", f"{gs.avg_degree:.1f}")
console.print(stats_tbl)

# Top connected nodes table
node_degrees = sorted(
    [(n, graph.degree(n.node_id)) for n in graph.nodes],
    key=lambda x: x[1], reverse=True
)
if node_degrees:
    console.print()
    top_tbl = Table(title="Top Connected Nodes", header_style="bold", padding=(0, 1))
    top_tbl.add_column("Node", style="cyan", max_width=40)
    top_tbl.add_column("Type", style="dim")
    top_tbl.add_column("Degree", justify="right")
    top_tbl.add_column("", style="green")
    for node, deg in node_degrees[:10]:
        bar = "#" * deg
        top_tbl.add_row(node.label[:40], node.node_type, str(deg), bar)
    console.print(top_tbl)

# Mermaid diagram
mermaid = graph.to_mermaid()
console.print(f"\n  [bold]Mermaid Diagram[/bold]")
console.print(f"  [dim]```mermaid[/dim]")
for line in mermaid.split("\n"):
    console.print(f"  [dim]{line}[/dim]")
console.print(f"  [dim]```[/dim]")

# Save all outputs
outpath = os.path.join(OUTPUT_DIR, f"graph_{label}.txt")
mmd_path = os.path.join(OUTPUT_DIR, f"graph_{label}.mmd")
dot_path = os.path.join(OUTPUT_DIR, f"graph_{label}.dot")
json_path = os.path.join(OUTPUT_DIR, f"graph_{label}.json")

dot = graph.to_dot()

out_text = []
out_text.append(f"Nodes: {gs.node_count}")
out_text.append(f"Edges: {gs.edge_count}")
out_text.append(f"Components: {gs.components}")
out_text.append(f"Density: {gs.density:.3f}")
out_text.append(f"Avg Degree: {gs.avg_degree:.1f}")
out_text.append("")
out_text.append("Top Connected Nodes:")
for node, deg in node_degrees[:10]:
    out_text.append(f"  {node.label} [{node.node_type}] degree={deg}")
out_text.append("")
out_text.append("Mermaid:")
out_text.append(mermaid)
out_text.append("")
out_text.append("DOT:")
out_text.append(dot)

with open(outpath, "w", encoding="utf-8") as f:
    f.write("\n".join(out_text))
with open(mmd_path, "w", encoding="utf-8") as f:
    f.write(mermaid)
with open(dot_path, "w", encoding="utf-8") as f:
    f.write(dot)
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(graph.to_dict(), f, indent=2)

# Files saved panel
files_tbl = Table(show_header=False, box=None, padding=(0, 1))
files_tbl.add_column(style="green")
files_tbl.add_column(style="dim")
files_tbl.add_row(os.path.basename(outpath), "full output")
files_tbl.add_row(os.path.basename(mmd_path), "Mermaid diagram")
files_tbl.add_row(os.path.basename(dot_path), "Graphviz DOT")
files_tbl.add_row(os.path.basename(json_path), "JSON data")
console.print()
console.print(Panel(files_tbl, title="[green]Saved to scripts/outputs/[/green]", border_style="green", expand=False))
