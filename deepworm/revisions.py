"""Document revision tracking and version history.

Track changes between document versions, manage revision history,
compute diffs, and generate change summaries.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Revision:
    """A single document revision."""

    content: str
    version: str = ""
    author: str = ""
    message: str = ""
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now()

    @property
    def hash(self) -> str:
        """SHA-256 hash of the content."""
        return hashlib.sha256(self.content.encode("utf-8")).hexdigest()[:12]

    @property
    def short_hash(self) -> str:
        """First 7 characters of the hash."""
        return self.hash[:7]

    @property
    def word_count(self) -> int:
        return len(self.content.split())

    @property
    def line_count(self) -> int:
        return len(self.content.splitlines()) if self.content else 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "author": self.author,
            "message": self.message,
            "hash": self.hash,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "word_count": self.word_count,
            "line_count": self.line_count,
            "metadata": self.metadata,
        }


@dataclass
class Change:
    """A single change between two revisions."""

    type: str  # "add", "delete", "modify"
    line_number: int = 0
    old_text: str = ""
    new_text: str = ""
    context: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "line_number": self.line_number,
            "old_text": self.old_text,
            "new_text": self.new_text,
            "context": self.context,
        }


@dataclass
class RevisionDiff:
    """Diff between two revisions."""

    from_version: str
    to_version: str
    changes: List[Change] = field(default_factory=list)
    additions: int = 0
    deletions: int = 0
    modifications: int = 0

    @property
    def total_changes(self) -> int:
        return self.additions + self.deletions + self.modifications

    @property
    def summary(self) -> str:
        parts = []
        if self.additions:
            parts.append(f"+{self.additions} added")
        if self.deletions:
            parts.append(f"-{self.deletions} deleted")
        if self.modifications:
            parts.append(f"~{self.modifications} modified")
        return ", ".join(parts) if parts else "no changes"

    def to_markdown(self) -> str:
        lines = [
            f"## Diff: {self.from_version} → {self.to_version}",
            "",
            f"**Summary:** {self.summary}",
            "",
        ]
        if self.changes:
            lines.append("### Changes")
            lines.append("")
            for ch in self.changes:
                if ch.type == "add":
                    lines.append(f"- **Line {ch.line_number}** (added): `{ch.new_text.strip()}`")
                elif ch.type == "delete":
                    lines.append(f"- **Line {ch.line_number}** (deleted): ~~`{ch.old_text.strip()}`~~")
                elif ch.type == "modify":
                    lines.append(
                        f"- **Line {ch.line_number}** (modified): "
                        f"`{ch.old_text.strip()}` → `{ch.new_text.strip()}`"
                    )
            lines.append("")
        return "\n".join(lines)

    def to_unified_diff(self) -> str:
        """Generate unified diff format."""
        lines = [
            f"--- {self.from_version}",
            f"+++ {self.to_version}",
        ]
        for ch in self.changes:
            if ch.type == "add":
                lines.append(f"@@ +{ch.line_number} @@")
                lines.append(f"+{ch.new_text}")
            elif ch.type == "delete":
                lines.append(f"@@ -{ch.line_number} @@")
                lines.append(f"-{ch.old_text}")
            elif ch.type == "modify":
                lines.append(f"@@ -{ch.line_number} +{ch.line_number} @@")
                lines.append(f"-{ch.old_text}")
                lines.append(f"+{ch.new_text}")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_version": self.from_version,
            "to_version": self.to_version,
            "additions": self.additions,
            "deletions": self.deletions,
            "modifications": self.modifications,
            "total_changes": self.total_changes,
            "summary": self.summary,
            "changes": [c.to_dict() for c in self.changes],
        }


class RevisionHistory:
    """Manage a sequence of document revisions."""

    def __init__(self, title: str = "") -> None:
        self.title = title
        self.revisions: List[Revision] = []

    @property
    def current(self) -> Optional[Revision]:
        return self.revisions[-1] if self.revisions else None

    @property
    def version_count(self) -> int:
        return len(self.revisions)

    def add(self, revision: Revision) -> None:
        """Add a revision to history."""
        if not revision.version:
            revision.version = f"v{self.version_count + 1}"
        self.revisions.append(revision)

    def get(self, version: str) -> Optional[Revision]:
        """Get a revision by version string."""
        for rev in self.revisions:
            if rev.version == version:
                return rev
        return None

    def get_by_hash(self, hash_prefix: str) -> Optional[Revision]:
        """Get a revision by hash prefix."""
        for rev in self.revisions:
            if rev.hash.startswith(hash_prefix):
                return rev
        return None

    def diff(self, from_version: str, to_version: str) -> RevisionDiff:
        """Compute diff between two versions."""
        rev_a = self.get(from_version)
        rev_b = self.get(to_version)
        if not rev_a or not rev_b:
            return RevisionDiff(from_version=from_version, to_version=to_version)
        return compute_diff(rev_a, rev_b)

    def changelog(self) -> str:
        """Generate changelog from revision messages."""
        lines = []
        if self.title:
            lines.append(f"# Changelog: {self.title}")
        else:
            lines.append("# Changelog")
        lines.append("")
        for rev in reversed(self.revisions):
            ts = rev.timestamp.strftime("%Y-%m-%d %H:%M") if rev.timestamp else "unknown"
            msg = rev.message or "no message"
            author = f" by {rev.author}" if rev.author else ""
            lines.append(f"- **{rev.version}** ({ts}{author}): {msg}")
        lines.append("")
        return "\n".join(lines)

    def statistics(self) -> Dict[str, Any]:
        """Compute statistics across all revisions."""
        if not self.revisions:
            return {
                "version_count": 0,
                "total_authors": 0,
                "authors": [],
                "word_count_trend": [],
                "line_count_trend": [],
            }
        authors = list(set(r.author for r in self.revisions if r.author))
        return {
            "version_count": self.version_count,
            "total_authors": len(authors),
            "authors": sorted(authors),
            "word_count_trend": [
                {"version": r.version, "words": r.word_count}
                for r in self.revisions
            ],
            "line_count_trend": [
                {"version": r.version, "lines": r.line_count}
                for r in self.revisions
            ],
            "first_version": self.revisions[0].version,
            "latest_version": self.revisions[-1].version,
        }

    def rollback(self, version: str) -> Optional[Revision]:
        """Create a new revision that rolls back to a previous version's content."""
        target = self.get(version)
        if not target:
            return None
        new_rev = Revision(
            content=target.content,
            author=target.author,
            message=f"Rollback to {version}",
        )
        self.add(new_rev)
        return new_rev

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "version_count": self.version_count,
            "revisions": [r.to_dict() for r in self.revisions],
        }


def compute_diff(rev_a: Revision, rev_b: Revision) -> RevisionDiff:
    """Compute detailed diff between two revisions.

    Uses line-by-line comparison with LCS (Longest Common Subsequence)
    for accurate change detection.
    """
    lines_a = rev_a.content.splitlines()
    lines_b = rev_b.content.splitlines()

    diff = RevisionDiff(
        from_version=rev_a.version,
        to_version=rev_b.version,
    )

    # Build LCS table
    m, n = len(lines_a), len(lines_b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if lines_a[i - 1] == lines_b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    # Backtrack to find changes
    changes: List[Change] = []
    i, j = m, n
    while i > 0 or j > 0:
        if i > 0 and j > 0 and lines_a[i - 1] == lines_b[j - 1]:
            i -= 1
            j -= 1
        elif j > 0 and (i == 0 or dp[i][j - 1] >= dp[i - 1][j]):
            changes.append(Change(
                type="add",
                line_number=j,
                new_text=lines_b[j - 1],
            ))
            diff.additions += 1
            j -= 1
        elif i > 0:
            changes.append(Change(
                type="delete",
                line_number=i,
                old_text=lines_a[i - 1],
            ))
            diff.deletions += 1
            i -= 1

    changes.reverse()

    # Detect modifications (adjacent delete+add pairs on same conceptual line)
    merged: List[Change] = []
    skip = set()
    for idx in range(len(changes) - 1):
        if idx in skip:
            continue
        cur = changes[idx]
        nxt = changes[idx + 1]
        if cur.type == "delete" and nxt.type == "add":
            merged.append(Change(
                type="modify",
                line_number=cur.line_number,
                old_text=cur.old_text,
                new_text=nxt.new_text,
            ))
            diff.deletions -= 1
            diff.additions -= 1
            diff.modifications += 1
            skip.add(idx + 1)
        else:
            merged.append(cur)
    # Add remaining
    for idx in range(len(changes)):
        if idx not in skip and idx >= len(changes) - 1 and changes[idx] not in merged:
            merged.append(changes[idx])

    diff.changes = merged
    return diff


def create_revision(
    content: str,
    version: str = "",
    author: str = "",
    message: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> Revision:
    """Create a new revision."""
    return Revision(
        content=content,
        version=version,
        author=author,
        message=message,
        metadata=metadata or {},
    )


def create_history(
    title: str = "",
    revisions: Optional[List[Dict[str, Any]]] = None,
) -> RevisionHistory:
    """Create a revision history from a list of revision dicts."""
    history = RevisionHistory(title=title)
    if revisions:
        for rev_data in revisions:
            rev = Revision(
                content=rev_data.get("content", ""),
                version=rev_data.get("version", ""),
                author=rev_data.get("author", ""),
                message=rev_data.get("message", ""),
            )
            history.add(rev)
    return history


def track_changes(
    original: str,
    revised: str,
    original_version: str = "v1",
    revised_version: str = "v2",
) -> RevisionDiff:
    """Quick comparison of two text versions.

    Args:
        original: The original text.
        revised: The revised text.
        original_version: Label for original version.
        revised_version: Label for revised version.

    Returns:
        RevisionDiff with changes between the two versions.
    """
    rev_a = Revision(content=original, version=original_version)
    rev_b = Revision(content=revised, version=revised_version)
    return compute_diff(rev_a, rev_b)


def merge_revisions(
    history_a: RevisionHistory,
    history_b: RevisionHistory,
    title: str = "",
) -> RevisionHistory:
    """Merge two revision histories chronologically."""
    merged = RevisionHistory(title=title or f"{history_a.title} + {history_b.title}")
    all_revisions = history_a.revisions + history_b.revisions
    all_revisions.sort(key=lambda r: r.timestamp or datetime.min)

    seen_hashes = set()
    for rev in all_revisions:
        if rev.hash not in seen_hashes:
            seen_hashes.add(rev.hash)
            merged.add(Revision(
                content=rev.content,
                version=rev.version,
                author=rev.author,
                message=rev.message,
                timestamp=rev.timestamp,
                metadata=rev.metadata,
            ))
    return merged
