"""Built-in web UI for deepworm.

A minimal, zero-dependency web interface served via Python's http.server.
Launch with:  deepworm --serve
"""

from __future__ import annotations

import json
import logging
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger("deepworm")

# ── HTML Templates ──────────────────────────────────────────────

INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>deepworm</title>
    <style>
        :root {
            --bg: #0a0a0a;
            --surface: #141414;
            --surface2: #1e1e1e;
            --border: #2a2a2a;
            --text: #e5e5e5;
            --muted: #737373;
            --accent: #22c55e;
            --accent-dim: #166534;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem 1.5rem;
        }
        header {
            text-align: center;
            margin-bottom: 3rem;
        }
        header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--accent);
            margin-bottom: 0.5rem;
        }
        header p {
            color: var(--muted);
            font-size: 1.1rem;
        }
        .search-form {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 2rem;
        }
        .search-row {
            display: flex;
            gap: 0.75rem;
            margin-bottom: 1rem;
        }
        .search-input {
            flex: 1;
            background: var(--surface2);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 0.75rem 1rem;
            color: var(--text);
            font-size: 1rem;
            outline: none;
            transition: border-color 0.2s;
        }
        .search-input:focus {
            border-color: var(--accent);
        }
        .search-input::placeholder {
            color: var(--muted);
        }
        .btn {
            background: var(--accent);
            color: #000;
            border: none;
            border-radius: 8px;
            padding: 0.75rem 1.5rem;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: opacity 0.2s;
            white-space: nowrap;
        }
        .btn:hover { opacity: 0.9; }
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .options {
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
        }
        .option-group {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .option-group label {
            color: var(--muted);
            font-size: 0.85rem;
        }
        .option-group select, .option-group input[type="number"] {
            background: var(--surface2);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 0.4rem 0.6rem;
            color: var(--text);
            font-size: 0.85rem;
            outline: none;
        }
        .option-group input[type="number"] { width: 60px; }
        .progress {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            display: none;
        }
        .progress.active { display: block; }
        .progress-title {
            font-weight: 600;
            margin-bottom: 0.75rem;
            color: var(--accent);
        }
        .progress-log {
            font-family: 'SF Mono', 'Fira Code', monospace;
            font-size: 0.85rem;
            color: var(--muted);
            max-height: 200px;
            overflow-y: auto;
            line-height: 1.6;
        }
        .progress-log .item {
            padding: 0.15rem 0;
        }
        .spinner {
            display: inline-block;
            width: 14px;
            height: 14px;
            border: 2px solid var(--border);
            border-top: 2px solid var(--accent);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin-right: 0.5rem;
            vertical-align: middle;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        .result {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 2rem;
            display: none;
            line-height: 1.7;
        }
        .result.active { display: block; }
        .result h1, .result h2, .result h3 {
            color: var(--text);
            margin: 1.5rem 0 0.75rem;
        }
        .result h1 { font-size: 1.5rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; }
        .result h2 { font-size: 1.25rem; }
        .result h3 { font-size: 1.1rem; }
        .result p { margin-bottom: 0.75rem; }
        .result ul, .result ol { padding-left: 1.5rem; margin-bottom: 0.75rem; }
        .result li { margin-bottom: 0.25rem; }
        .result code {
            background: var(--surface2);
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
            font-size: 0.9em;
        }
        .result pre {
            background: var(--surface2);
            padding: 1rem;
            border-radius: 8px;
            overflow-x: auto;
            margin-bottom: 1rem;
        }
        .result pre code { background: none; padding: 0; }
        .result a { color: var(--accent); }
        .result blockquote {
            border-left: 3px solid var(--accent-dim);
            padding-left: 1rem;
            color: var(--muted);
            margin-bottom: 0.75rem;
        }
        .result-actions {
            display: flex;
            gap: 0.75rem;
            margin-top: 1.5rem;
            padding-top: 1rem;
            border-top: 1px solid var(--border);
        }
        .btn-secondary {
            background: var(--surface2);
            color: var(--text);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 0.5rem 1rem;
            font-size: 0.85rem;
            cursor: pointer;
            transition: background 0.2s;
        }
        .btn-secondary:hover { background: var(--border); }
        .history {
            margin-top: 2rem;
        }
        .history-title {
            color: var(--muted);
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.75rem;
        }
        .history-item {
            display: flex;
            justify-content: space-between;
            padding: 0.75rem 1rem;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            margin-bottom: 0.5rem;
            cursor: pointer;
            transition: border-color 0.2s;
        }
        .history-item:hover { border-color: var(--accent-dim); }
        .history-topic { font-weight: 500; }
        .history-meta { color: var(--muted); font-size: 0.85rem; }
        footer {
            text-align: center;
            margin-top: 3rem;
            color: var(--muted);
            font-size: 0.8rem;
        }
        footer a { color: var(--accent); text-decoration: none; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>deepworm</h1>
            <p>AI-powered deep research agent</p>
        </header>

        <div class="search-form">
            <div class="search-row">
                <input type="text" class="search-input" id="topic"
                       placeholder="What do you want to research?"
                       autofocus autocomplete="off">
                <button class="btn" id="research-btn" onclick="startResearch()">Research</button>
            </div>
            <div class="options">
                <div class="option-group">
                    <label>Depth</label>
                    <input type="number" id="depth" value="2" min="1" max="5">
                </div>
                <div class="option-group">
                    <label>Breadth</label>
                    <input type="number" id="breadth" value="4" min="1" max="10">
                </div>
                <div class="option-group">
                    <label>Persona</label>
                    <input type="text" class="search-input" id="persona"
                           placeholder="e.g. startup founder" style="width:180px;padding:0.4rem 0.6rem;font-size:0.85rem">
                </div>
            </div>
        </div>

        <div class="progress" id="progress">
            <div class="progress-title"><span class="spinner"></span> Researching...</div>
            <div class="progress-log" id="progress-log"></div>
        </div>

        <div class="result" id="result"></div>

        <div class="history" id="history-section" style="display:none">
            <div class="history-title">Recent Research</div>
            <div id="history-list"></div>
        </div>

        <footer>
            <a href="https://github.com/bysiber/deepworm" target="_blank">deepworm</a> &mdash; open-source deep research
        </footer>
    </div>

    <script>
        const topicInput = document.getElementById('topic');
        const btn = document.getElementById('research-btn');
        const progressEl = document.getElementById('progress');
        const progressLog = document.getElementById('progress-log');
        const resultEl = document.getElementById('result');

        topicInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') startResearch();
        });

        let rawReport = '';

        async function startResearch() {
            const topic = topicInput.value.trim();
            if (!topic) return;

            btn.disabled = true;
            btn.textContent = 'Researching...';
            progressEl.classList.add('active');
            resultEl.classList.remove('active');
            progressLog.innerHTML = '';
            rawReport = '';

            try {
                const params = new URLSearchParams({
                    topic,
                    depth: document.getElementById('depth').value,
                    breadth: document.getElementById('breadth').value,
                    persona: document.getElementById('persona').value || '',
                });

                const res = await fetch('/api/research?' + params.toString());
                const reader = res.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';

                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;
                    buffer += decoder.decode(value, { stream: true });

                    const lines = buffer.split('\\n');
                    buffer = lines.pop() || '';

                    for (const line of lines) {
                        if (!line.trim()) continue;
                        try {
                            const msg = JSON.parse(line);
                            if (msg.type === 'progress') {
                                progressLog.innerHTML += '<div class="item">' + escapeHtml(msg.message) + '</div>';
                                progressLog.scrollTop = progressLog.scrollHeight;
                            } else if (msg.type === 'report') {
                                rawReport = msg.content;
                                resultEl.innerHTML = msg.html +
                                    '<div class="result-actions">' +
                                    '<button class="btn-secondary" onclick="copyReport()">Copy Markdown</button>' +
                                    '<button class="btn-secondary" onclick="downloadReport()">Download</button>' +
                                    '</div>';
                                resultEl.classList.add('active');
                                progressEl.classList.remove('active');
                            }
                        } catch (e) {}
                    }
                }
            } catch (e) {
                progressLog.innerHTML += '<div class="item" style="color:#ef4444">Error: ' + escapeHtml(e.message) + '</div>';
            }

            btn.disabled = false;
            btn.textContent = 'Research';
            loadHistory();
        }

        function copyReport() {
            navigator.clipboard.writeText(rawReport);
        }

        function downloadReport() {
            const blob = new Blob([rawReport], { type: 'text/markdown' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'research-report.md';
            a.click();
            URL.revokeObjectURL(url);
        }

        function escapeHtml(s) {
            return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
        }

        async function loadHistory() {
            try {
                const res = await fetch('/api/history');
                const entries = await res.json();
                const section = document.getElementById('history-section');
                const list = document.getElementById('history-list');

                if (entries.length > 0) {
                    section.style.display = 'block';
                    list.innerHTML = entries.slice(0, 5).map(e =>
                        '<div class="history-item" onclick="document.getElementById(\\'topic\\').value=\\'' +
                        escapeHtml(e.topic).replace(/'/g, "\\\\'") + '\\'">' +
                        '<span class="history-topic">' + escapeHtml(e.topic) + '</span>' +
                        '<span class="history-meta">' + e.sources + ' sources &middot; ' +
                        Math.round(e.elapsed) + 's</span></div>'
                    ).join('');
                }
            } catch(e) {}
        }

        loadHistory();
    </script>
</body>
</html>"""


class ResearchHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the web UI."""

    server_version = "deepworm"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        logger.debug(format, *args)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self._respond(200, "text/html", INDEX_HTML)
        elif path == "/api/research":
            self._handle_research(parse_qs(parsed.query))
        elif path == "/api/history":
            self._handle_history()
        else:
            self._respond(404, "text/plain", "Not Found")

    def _respond(self, status: int, content_type: str, body: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def _handle_research(self, params: dict[str, list[str]]) -> None:
        """Stream research progress and results."""
        from .config import Config
        from .events import Event, EventEmitter, EventType
        from .report import markdown_to_html
        from .researcher import DeepResearcher

        topic = (params.get("topic", [""])[0]).strip()
        if not topic:
            self._respond(400, "application/json", '{"error":"No topic provided"}')
            return

        depth = int(params.get("depth", ["2"])[0])
        breadth = int(params.get("breadth", ["4"])[0])
        persona = params.get("persona", [""])[0] or None

        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.send_header("Transfer-Encoding", "chunked")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        def send_json(data: dict[str, Any]) -> None:
            line = json.dumps(data, ensure_ascii=False) + "\n"
            chunk = f"{len(line.encode()):X}\r\n{line}\r\n"
            try:
                self.wfile.write(chunk.encode("utf-8"))
                self.wfile.flush()
            except Exception:
                pass

        # Set up progress callback
        emitter = EventEmitter()

        @emitter.on_all
        def on_event(event: Event) -> None:
            send_json({"type": "progress", "message": event.message})

        config = Config.auto()
        config.depth = depth
        config.breadth = breadth

        try:
            researcher = DeepResearcher(config=config, events=emitter)
            report = researcher.research(topic, verbose=False, persona=persona)

            # Convert to HTML for display
            from .report import _md_to_html_body
            html_body = _md_to_html_body(report)

            send_json({
                "type": "report",
                "content": report,
                "html": html_body,
            })
        except Exception as e:
            send_json({"type": "progress", "message": f"Error: {e}"})

        # Send final empty chunk
        try:
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()
        except Exception:
            pass

    def _handle_history(self) -> None:
        """Return recent research history."""
        from .history import list_entries

        entries = list_entries(limit=10)
        data = [
            {
                "topic": e.topic,
                "elapsed": e.elapsed_seconds,
                "sources": e.total_sources,
                "model": e.model,
                "created": e.created_iso,
            }
            for e in entries
        ]
        self._respond(200, "application/json", json.dumps(data))


def serve(host: str = "127.0.0.1", port: int = 8888) -> None:
    """Start the web UI server.

    Args:
        host: Bind address (default: localhost).
        port: Port number (default: 8888).
    """
    server = HTTPServer((host, port), ResearchHandler)
    url = f"http://{host}:{port}"
    print(f"\n  deepworm web UI running at {url}\n")
    print(f"  Press Ctrl+C to stop.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()
