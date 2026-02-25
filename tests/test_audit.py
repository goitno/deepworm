"""Tests for deepworm.audit – audit trail and change logging."""

import pytest

from deepworm.audit import (
    AuditAction,
    AuditEntry,
    AuditLevel,
    AuditLog,
    AuditPolicy,
    AuditReport,
    create_audit_log,
    minimal_audit_policy,
    strict_audit_policy,
)


# ---------------------------------------------------------------------------
# AuditAction / AuditLevel
# ---------------------------------------------------------------------------

class TestEnums:
    def test_action_values(self):
        assert len(AuditAction) == 10
        assert AuditAction.CREATE.value == "create"
        assert AuditAction.ARCHIVE.value == "archive"

    def test_level_values(self):
        assert len(AuditLevel) == 5
        assert AuditLevel.DEBUG.value == "debug"
        assert AuditLevel.CRITICAL.value == "critical"


# ---------------------------------------------------------------------------
# AuditEntry
# ---------------------------------------------------------------------------

class TestAuditEntry:
    def test_defaults(self):
        entry = AuditEntry(action=AuditAction.CREATE, target="doc.md")
        assert entry.actor == "system"
        assert entry.timestamp != ""
        assert entry.entry_id != ""
        assert entry.checksum != ""

    def test_to_dict(self):
        entry = AuditEntry(
            action=AuditAction.UPDATE,
            target="report.md",
            actor="alice",
            details="Fixed typo",
        )
        d = entry.to_dict()
        assert d["action"] == "update"
        assert d["actor"] == "alice"
        assert d["details"] == "Fixed typo"

    def test_to_log_line(self):
        entry = AuditEntry(
            action=AuditAction.DELETE,
            target="old.md",
            actor="bob",
            level=AuditLevel.WARNING,
        )
        line = entry.to_log_line()
        assert "WARNING" in line
        assert "delete" in line
        assert "bob" in line

    def test_checksum_deterministic(self):
        e1 = AuditEntry(
            action=AuditAction.READ,
            target="x",
            actor="a",
            timestamp="2024-01-01T00:00:00Z",
        )
        e2 = AuditEntry(
            action=AuditAction.READ,
            target="x",
            actor="a",
            timestamp="2024-01-01T00:00:00Z",
        )
        assert e1.checksum == e2.checksum


# ---------------------------------------------------------------------------
# AuditPolicy
# ---------------------------------------------------------------------------

class TestAuditPolicy:
    def test_default_policy(self):
        policy = AuditPolicy()
        assert policy.require_actor is True

    def test_check_missing_actor(self):
        policy = AuditPolicy(require_actor=True)
        entry = AuditEntry(action=AuditAction.CREATE, target="test")
        violations = policy.check(entry)
        assert len(violations) >= 1
        assert "Actor" in violations[0]

    def test_check_missing_details(self):
        policy = AuditPolicy(require_actor=False)
        entry = AuditEntry(action=AuditAction.DELETE, target="test")
        violations = policy.check(entry)
        assert any("Details" in v for v in violations)

    def test_allowed_actors(self):
        policy = AuditPolicy(
            require_actor=False,
            allowed_actors={"alice", "bob"},
        )
        entry = AuditEntry(action=AuditAction.READ, target="x", actor="eve")
        violations = policy.check(entry)
        assert any("eve" in v for v in violations)

    def test_no_violations(self):
        policy = AuditPolicy(require_actor=False, require_details_for=set())
        entry = AuditEntry(action=AuditAction.READ, target="x")
        assert policy.check(entry) == []


# ---------------------------------------------------------------------------
# AuditLog
# ---------------------------------------------------------------------------

class TestAuditLog:
    def test_log_entry(self):
        log = create_audit_log()
        entry = log.log(AuditAction.CREATE, "doc.md", actor="alice")
        assert log.count == 1
        assert entry.action == AuditAction.CREATE

    def test_query_by_action(self):
        log = create_audit_log()
        log.log(AuditAction.CREATE, "a.md")
        log.log(AuditAction.UPDATE, "a.md")
        log.log(AuditAction.CREATE, "b.md")
        results = log.query(action=AuditAction.CREATE)
        assert len(results) == 2

    def test_query_by_actor(self):
        log = create_audit_log()
        log.log(AuditAction.READ, "x", actor="alice")
        log.log(AuditAction.READ, "y", actor="bob")
        results = log.query(actor="alice")
        assert len(results) == 1

    def test_query_by_target(self):
        log = create_audit_log()
        log.log(AuditAction.UPDATE, "doc.md")
        log.log(AuditAction.UPDATE, "other.md")
        results = log.query(target="doc.md")
        assert len(results) == 1

    def test_query_limit(self):
        log = create_audit_log()
        for i in range(10):
            log.log(AuditAction.READ, f"file{i}")
        results = log.query(limit=3)
        assert len(results) == 3

    def test_listener(self):
        log = create_audit_log()
        received = []
        log.add_listener(lambda e: received.append(e))
        log.log(AuditAction.CREATE, "test")
        assert len(received) == 1

    def test_listener_error_ignored(self):
        log = create_audit_log()
        log.add_listener(lambda e: 1 / 0)  # raises
        log.log(AuditAction.READ, "test")  # should not raise
        assert log.count == 1

    def test_max_entries(self):
        log = create_audit_log(max_entries=5)
        for i in range(10):
            log.log(AuditAction.READ, f"file{i}")
        assert log.count <= 5

    def test_min_level_filter(self):
        log = create_audit_log(min_level="warning")
        log.log(AuditAction.READ, "x", level=AuditLevel.INFO)
        log.log(AuditAction.UPDATE, "y", level=AuditLevel.WARNING)
        assert log.count == 1

    def test_clear(self):
        log = create_audit_log()
        log.log(AuditAction.CREATE, "test")
        cleared = log.clear()
        assert cleared == 1
        assert log.count == 0

    def test_export_log(self):
        log = create_audit_log()
        log.log(AuditAction.CREATE, "test")
        exported = log.export_log()
        assert len(exported) == 1
        assert exported[0]["action"] == "create"

    def test_export_text(self):
        log = create_audit_log()
        log.log(AuditAction.CREATE, "test", actor="alice")
        text = log.export_text()
        assert "create" in text
        assert "alice" in text

    def test_violations_tracked(self):
        policy = AuditPolicy(require_actor=True)
        log = AuditLog(policy=policy)
        log.log(AuditAction.CREATE, "test")  # actor=system triggers violation
        assert len(log.violations) >= 1


# ---------------------------------------------------------------------------
# AuditReport
# ---------------------------------------------------------------------------

class TestAuditReport:
    def test_generate_report(self):
        log = create_audit_log()
        log.log(AuditAction.CREATE, "a", actor="alice")
        log.log(AuditAction.UPDATE, "a", actor="alice")
        log.log(AuditAction.READ, "b", actor="bob")
        report = log.generate_report()
        assert report.total_entries == 3
        assert report.by_action["create"] == 1
        assert report.by_actor["alice"] == 2

    def test_to_markdown(self):
        report = AuditReport(
            total_entries=5,
            by_action={"create": 3, "read": 2},
            by_actor={"alice": 5},
        )
        md = report.to_markdown()
        assert "## Audit Report" in md
        assert "5" in md
        assert "alice" in md

    def test_to_dict(self):
        report = AuditReport(total_entries=1)
        d = report.to_dict()
        assert d["total_entries"] == 1


# ---------------------------------------------------------------------------
# Preset policies
# ---------------------------------------------------------------------------

class TestPresetPolicies:
    def test_strict(self):
        policy = strict_audit_policy()
        assert policy.require_actor is True
        assert AuditAction.UPDATE in policy.require_details_for

    def test_minimal(self):
        policy = minimal_audit_policy()
        assert policy.require_actor is False
        assert len(policy.require_details_for) == 0
        assert policy.min_level == AuditLevel.WARNING
