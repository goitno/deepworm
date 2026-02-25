"""Document audit trail and change logging.

Track who changed what, when, and why across document lifecycle.
Generate audit reports and enforce change policies.
"""

from __future__ import annotations

import datetime
import hashlib
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


class AuditAction(Enum):
    """Types of auditable actions."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    READ = "read"
    EXPORT = "export"
    VALIDATE = "validate"
    APPROVE = "approve"
    REJECT = "reject"
    ARCHIVE = "archive"
    RESTORE = "restore"


class AuditLevel(Enum):
    """Severity/importance of an audit entry."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEntry:
    """A single audit log entry."""

    action: AuditAction
    target: str
    actor: str = "system"
    timestamp: str = ""
    details: str = ""
    level: AuditLevel = AuditLevel.INFO
    entry_id: str = ""
    checksum: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.datetime.utcnow().isoformat() + "Z"
        if not self.entry_id:
            self.entry_id = uuid.uuid4().hex[:12]
        if not self.checksum:
            data = f"{self.action.value}:{self.target}:{self.actor}:{self.timestamp}"
            self.checksum = hashlib.sha256(data.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "id": self.entry_id,
            "action": self.action.value,
            "target": self.target,
            "actor": self.actor,
            "timestamp": self.timestamp,
            "level": self.level.value,
            "checksum": self.checksum,
        }
        if self.details:
            d["details"] = self.details
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    def to_log_line(self) -> str:
        return (
            f"[{self.timestamp}] [{self.level.value.upper()}] "
            f"{self.action.value}: {self.target} by {self.actor}"
            + (f" - {self.details}" if self.details else "")
        )


@dataclass
class AuditPolicy:
    """Policy rules for the audit system."""

    require_actor: bool = True
    require_details_for: Set[AuditAction] = field(
        default_factory=lambda: {AuditAction.DELETE, AuditAction.APPROVE, AuditAction.REJECT}
    )
    allowed_actors: Optional[Set[str]] = None
    max_entries: int = 10000
    min_level: AuditLevel = AuditLevel.INFO

    def check(self, entry: AuditEntry) -> List[str]:
        """Check an entry against policy. Returns list of violations."""
        violations: List[str] = []
        if self.require_actor and entry.actor == "system":
            violations.append("Actor must be specified (not 'system')")
        if entry.action in self.require_details_for and not entry.details:
            violations.append(
                f"Details required for action '{entry.action.value}'"
            )
        if self.allowed_actors and entry.actor not in self.allowed_actors:
            violations.append(f"Actor '{entry.actor}' not in allowed list")
        return violations


@dataclass
class AuditReport:
    """Summary report of audit activity."""

    total_entries: int = 0
    by_action: Dict[str, int] = field(default_factory=dict)
    by_actor: Dict[str, int] = field(default_factory=dict)
    by_level: Dict[str, int] = field(default_factory=dict)
    time_range: str = ""
    policy_violations: int = 0

    def to_markdown(self) -> str:
        lines = ["## Audit Report", ""]
        lines.append(f"**Total entries:** {self.total_entries}")
        if self.time_range:
            lines.append(f"**Time range:** {self.time_range}")
        if self.policy_violations:
            lines.append(f"**Policy violations:** {self.policy_violations}")
        lines.append("")

        if self.by_action:
            lines.append("### By Action")
            for action, count in sorted(self.by_action.items()):
                lines.append(f"- {action}: {count}")
            lines.append("")

        if self.by_actor:
            lines.append("### By Actor")
            for actor, count in sorted(self.by_actor.items()):
                lines.append(f"- {actor}: {count}")
            lines.append("")

        if self.by_level:
            lines.append("### By Level")
            for level, count in sorted(self.by_level.items()):
                lines.append(f"- {level}: {count}")
            lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_entries": self.total_entries,
            "by_action": self.by_action,
            "by_actor": self.by_actor,
            "by_level": self.by_level,
            "policy_violations": self.policy_violations,
        }


class AuditLog:
    """Central audit log for tracking document changes."""

    def __init__(
        self,
        policy: Optional[AuditPolicy] = None,
    ) -> None:
        self._entries: List[AuditEntry] = []
        self._policy = policy or AuditPolicy(require_actor=False)
        self._listeners: List[Callable[[AuditEntry], None]] = []
        self._violations: List[str] = []

    def log(
        self,
        action: AuditAction,
        target: str,
        actor: str = "system",
        details: str = "",
        level: AuditLevel = AuditLevel.INFO,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEntry:
        """Log an audit entry.

        Returns:
            The created AuditEntry.
        """
        entry = AuditEntry(
            action=action,
            target=target,
            actor=actor,
            details=details,
            level=level,
            metadata=metadata or {},
        )

        # Check level filter
        level_order = [AuditLevel.DEBUG, AuditLevel.INFO, AuditLevel.WARNING,
                       AuditLevel.ERROR, AuditLevel.CRITICAL]
        if level_order.index(entry.level) < level_order.index(self._policy.min_level):
            return entry

        # Check policy
        violations = self._policy.check(entry)
        self._violations.extend(violations)

        # Enforce max entries
        if self._policy.max_entries and len(self._entries) >= self._policy.max_entries:
            self._entries = self._entries[-(self._policy.max_entries - 1):]

        self._entries.append(entry)

        # Notify listeners
        for listener in self._listeners:
            try:
                listener(entry)
            except Exception:
                pass

        return entry

    def query(
        self,
        action: Optional[AuditAction] = None,
        actor: Optional[str] = None,
        target: Optional[str] = None,
        level: Optional[AuditLevel] = None,
        since: Optional[str] = None,
        limit: int = 0,
    ) -> List[AuditEntry]:
        """Query audit entries with optional filters."""
        results = list(self._entries)

        if action:
            results = [e for e in results if e.action == action]
        if actor:
            results = [e for e in results if e.actor == actor]
        if target:
            results = [e for e in results if e.target == target]
        if level:
            results = [e for e in results if e.level == level]
        if since:
            results = [e for e in results if e.timestamp >= since]
        if limit > 0:
            results = results[-limit:]

        return results

    def add_listener(self, callback: Callable[[AuditEntry], None]) -> None:
        """Add a listener that receives entries as they're logged."""
        self._listeners.append(callback)

    def generate_report(self) -> AuditReport:
        """Generate an audit summary report."""
        report = AuditReport(total_entries=len(self._entries))

        for entry in self._entries:
            action_name = entry.action.value
            report.by_action[action_name] = report.by_action.get(action_name, 0) + 1
            report.by_actor[entry.actor] = report.by_actor.get(entry.actor, 0) + 1
            level_name = entry.level.value
            report.by_level[level_name] = report.by_level.get(level_name, 0) + 1

        if self._entries:
            report.time_range = (
                f"{self._entries[0].timestamp} — {self._entries[-1].timestamp}"
            )

        report.policy_violations = len(self._violations)
        return report

    def export_log(self) -> List[Dict[str, Any]]:
        """Export all entries as dicts."""
        return [e.to_dict() for e in self._entries]

    def export_text(self) -> str:
        """Export all entries as text log lines."""
        return "\n".join(e.to_log_line() for e in self._entries)

    def clear(self) -> int:
        """Clear all entries. Returns count cleared."""
        count = len(self._entries)
        self._entries = []
        self._violations = []
        return count

    @property
    def count(self) -> int:
        return len(self._entries)

    @property
    def violations(self) -> List[str]:
        return list(self._violations)


def create_audit_log(
    require_actor: bool = False,
    max_entries: int = 10000,
    min_level: str = "info",
) -> AuditLog:
    """Create an audit log with configured policy."""
    policy = AuditPolicy(
        require_actor=require_actor,
        max_entries=max_entries,
        min_level=AuditLevel(min_level),
    )
    return AuditLog(policy=policy)


def strict_audit_policy() -> AuditPolicy:
    """Create a strict audit policy."""
    return AuditPolicy(
        require_actor=True,
        require_details_for={
            AuditAction.DELETE,
            AuditAction.APPROVE,
            AuditAction.REJECT,
            AuditAction.UPDATE,
        },
        max_entries=50000,
        min_level=AuditLevel.INFO,
    )


def minimal_audit_policy() -> AuditPolicy:
    """Create a minimal audit policy (no requirements)."""
    return AuditPolicy(
        require_actor=False,
        require_details_for=set(),
        max_entries=1000,
        min_level=AuditLevel.WARNING,
    )
