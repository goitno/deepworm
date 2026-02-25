"""Tests for the security module."""

import pytest

from deepworm.security import (
    ContentPolicy,
    SecurityFinding,
    SecurityReport,
    ThreatLevel,
    ThreatType,
    check_path_traversal,
    constant_time_compare,
    content_hash,
    detect_pii,
    detect_secrets,
    extract_urls,
    generate_token,
    mask_secret,
    redact_text,
    relaxed_policy,
    sanitize_html,
    sanitize_markdown,
    scan_content,
    strict_policy,
    validate_url,
)


# ---------------------------------------------------------------------------
# ThreatLevel / ThreatType
# ---------------------------------------------------------------------------


class TestEnums:
    def test_threat_levels(self):
        assert len(ThreatLevel) == 5

    def test_threat_types(self):
        assert len(ThreatType) == 8


# ---------------------------------------------------------------------------
# SecurityFinding
# ---------------------------------------------------------------------------


class TestSecurityFinding:
    def test_to_dict(self):
        f = SecurityFinding(
            threat_type=ThreatType.XSS,
            threat_level=ThreatLevel.HIGH,
            message="Script tag found",
            line=5,
        )
        d = f.to_dict()
        assert d["threat_type"] == "xss"
        assert d["threat_level"] == "high"
        assert d["message"] == "Script tag found"
        assert d["line"] == 5


# ---------------------------------------------------------------------------
# SecurityReport
# ---------------------------------------------------------------------------


class TestSecurityReport:
    def test_empty_report(self):
        r = SecurityReport(scanned_lines=10)
        assert r.threat_count == 0
        assert r.max_threat_level == ThreatLevel.NONE
        assert r.is_safe

    def test_report_with_findings(self):
        r = SecurityReport(
            findings=[
                SecurityFinding(ThreatType.XSS, ThreatLevel.HIGH, "xss"),
                SecurityFinding(ThreatType.PII, ThreatLevel.LOW, "email"),
            ],
            scanned_lines=20,
        )
        assert r.threat_count == 2
        assert r.max_threat_level == ThreatLevel.HIGH
        assert not r.is_safe

    def test_by_level(self):
        r = SecurityReport(findings=[
            SecurityFinding(ThreatType.XSS, ThreatLevel.HIGH, "a"),
            SecurityFinding(ThreatType.PII, ThreatLevel.LOW, "b"),
        ])
        assert len(r.by_level(ThreatLevel.HIGH)) == 1
        assert len(r.by_level(ThreatLevel.LOW)) == 1

    def test_by_type(self):
        r = SecurityReport(findings=[
            SecurityFinding(ThreatType.XSS, ThreatLevel.HIGH, "a"),
            SecurityFinding(ThreatType.XSS, ThreatLevel.MEDIUM, "b"),
            SecurityFinding(ThreatType.PII, ThreatLevel.LOW, "c"),
        ])
        assert len(r.by_type(ThreatType.XSS)) == 2

    def test_to_markdown(self):
        r = SecurityReport(
            findings=[SecurityFinding(ThreatType.XSS, ThreatLevel.HIGH, "found xss")],
            scanned_lines=5,
        )
        md = r.to_markdown()
        assert "Security Report" in md
        assert "found xss" in md
        assert "HIGH" in md

    def test_to_dict(self):
        r = SecurityReport(scanned_lines=10)
        d = r.to_dict()
        assert d["is_safe"] is True
        assert d["threat_count"] == 0

    def test_is_safe_with_low_only(self):
        r = SecurityReport(findings=[
            SecurityFinding(ThreatType.PII, ThreatLevel.LOW, "email"),
        ])
        assert r.is_safe  # LOW is considered safe


# ---------------------------------------------------------------------------
# sanitize_html
# ---------------------------------------------------------------------------


class TestSanitizeHtml:
    def test_removes_script(self):
        text = '<p>Hello</p><script>alert("xss")</script>'
        result = sanitize_html(text)
        assert "<script" not in result
        assert "alert" not in result
        assert "<p>Hello</p>" in result

    def test_removes_event_handlers(self):
        text = '<img src="x" onerror="alert(1)">'
        result = sanitize_html(text)
        assert "onerror" not in result

    def test_removes_javascript_uri(self):
        text = '<a href="javascript:alert(1)">click</a>'
        result = sanitize_html(text)
        assert "javascript:" not in result

    def test_preserves_safe_text(self):
        text = "Hello **world** with [link](https://example.com)"
        assert sanitize_html(text) == text


# ---------------------------------------------------------------------------
# detect_secrets
# ---------------------------------------------------------------------------


class TestDetectSecrets:
    def test_detects_api_key(self):
        text = "api_key = 'my_secret_key_4eC39HqLyjWDarjtT1zdp7dc'"
        findings = detect_secrets(text)
        assert len(findings) >= 1
        assert any(f.threat_type == ThreatType.SECRET_LEAK for f in findings)

    def test_detects_aws_key(self):
        text = "AKIAIOSFODNN7EXAMPLE"
        findings = detect_secrets(text)
        assert any("AWS" in f.message for f in findings)

    def test_detects_private_key(self):
        text = "-----BEGIN PRIVATE KEY-----\nMIIBVg..."
        findings = detect_secrets(text)
        assert any("Private key" in f.message for f in findings)

    def test_clean_text(self):
        text = "This is just normal text without any secrets."
        findings = detect_secrets(text)
        assert len(findings) == 0

    def test_detects_github_token(self):
        text = "token: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij"
        findings = detect_secrets(text)
        assert len(findings) >= 1


# ---------------------------------------------------------------------------
# detect_pii
# ---------------------------------------------------------------------------


class TestDetectPii:
    def test_detects_email(self):
        findings = detect_pii("Contact us at user@example.com")
        assert any(f.message == "Email address detected" for f in findings)

    def test_detects_phone(self):
        findings = detect_pii("Call 555-123-4567")
        assert any("Phone" in f.message for f in findings)

    def test_detects_ssn(self):
        findings = detect_pii("SSN: 123-45-6789")
        assert any("SSN" in f.message for f in findings)

    def test_detects_credit_card(self):
        findings = detect_pii("Card: 4111-1111-1111-1111")
        assert any("Credit card" in f.message for f in findings)

    def test_clean_text(self):
        findings = detect_pii("Just a normal sentence.")
        assert len(findings) == 0


# ---------------------------------------------------------------------------
# validate_url
# ---------------------------------------------------------------------------


class TestValidateUrl:
    def test_safe_url(self):
        findings = validate_url("https://example.com")
        assert len(findings) == 0

    def test_javascript_url(self):
        findings = validate_url("javascript:alert(1)")
        assert any(f.threat_type == ThreatType.XSS for f in findings)

    def test_private_ip(self):
        findings = validate_url("http://192.168.1.1/admin")
        assert any(f.threat_type == ThreatType.SSRF for f in findings)

    def test_localhost(self):
        findings = validate_url("http://localhost:8080/api")
        assert any(f.threat_type == ThreatType.SSRF for f in findings)

    def test_blocked_domain(self):
        policy = ContentPolicy(blocked_domains=["evil.com"])
        findings = validate_url("https://evil.com/malware", policy)
        assert any("blocked domain" in f.message for f in findings)

    def test_require_https(self):
        policy = ContentPolicy(require_https=True)
        findings = validate_url("http://example.com", policy)
        assert any("HTTP instead of HTTPS" in f.message for f in findings)

    def test_url_too_long(self):
        policy = ContentPolicy(max_url_length=50)
        long_url = "https://example.com/" + "a" * 100
        findings = validate_url(long_url, policy)
        assert any("max length" in f.message for f in findings)


# ---------------------------------------------------------------------------
# extract_urls
# ---------------------------------------------------------------------------


class TestExtractUrls:
    def test_extracts_urls(self):
        text = "Visit https://example.com and http://test.org/page"
        urls = extract_urls(text)
        assert len(urls) >= 2

    def test_no_urls(self):
        urls = extract_urls("No URLs here")
        assert len(urls) == 0


# ---------------------------------------------------------------------------
# check_path_traversal
# ---------------------------------------------------------------------------


class TestCheckPathTraversal:
    def test_detect_traversal(self):
        findings = check_path_traversal("../../etc/passwd")
        assert len(findings) >= 1
        assert findings[0].threat_type == ThreatType.PATH_TRAVERSAL

    def test_detect_null_byte(self):
        findings = check_path_traversal("file.txt\x00.jpg")
        assert any("Null byte" in f.message for f in findings)

    def test_safe_path(self):
        findings = check_path_traversal("documents/report.md")
        assert len(findings) == 0


# ---------------------------------------------------------------------------
# sanitize_markdown
# ---------------------------------------------------------------------------


class TestSanitizeMarkdown:
    def test_removes_script(self):
        text = '# Title\n\n<script>alert("xss")</script>\n\nContent'
        result = sanitize_markdown(text)
        assert "<script" not in result
        assert "# Title" in result
        assert "Content" in result

    def test_removes_javascript_links(self):
        text = '[Click me](javascript:alert(1))'
        result = sanitize_markdown(text)
        assert "javascript:" not in result
        assert "[Click me]" in result

    def test_preserves_safe_markdown(self):
        text = "# Heading\n\n**Bold** and *italic*\n\n[Link](https://safe.com)"
        assert sanitize_markdown(text) == text


# ---------------------------------------------------------------------------
# redact_text
# ---------------------------------------------------------------------------


class TestRedactText:
    def test_redacts_email(self):
        result = redact_text("Email: user@example.com")
        assert "[REDACTED_EMAIL]" in result
        assert "user@example.com" not in result

    def test_redacts_phone(self):
        result = redact_text("Call 555-123-4567")
        assert "[REDACTED_PHONE]" in result

    def test_custom_patterns(self):
        result = redact_text("ref: ABC-123", patterns=[r"ABC-\d+"])
        assert "[REDACTED]" in result
        assert "ABC-123" not in result


# ---------------------------------------------------------------------------
# Hashing / tokens
# ---------------------------------------------------------------------------


class TestHashingTokens:
    def test_content_hash_sha256(self):
        h = content_hash("hello")
        assert len(h) == 64  # SHA-256 hex length

    def test_content_hash_md5(self):
        h = content_hash("hello", "md5")
        assert len(h) == 32

    def test_content_hash_deterministic(self):
        assert content_hash("test") == content_hash("test")
        assert content_hash("a") != content_hash("b")

    def test_generate_token(self):
        t1 = generate_token()
        t2 = generate_token()
        assert t1 != t2
        assert len(t1) > 20

    def test_constant_time_compare(self):
        assert constant_time_compare("hello", "hello")
        assert not constant_time_compare("hello", "world")

    def test_mask_secret(self):
        assert mask_secret("sk-1234567890abcdef") == "***************cdef"
        assert mask_secret("ab", visible=4) == "**"


# ---------------------------------------------------------------------------
# scan_content
# ---------------------------------------------------------------------------


class TestScanContent:
    def test_clean_content(self):
        report = scan_content("This is a clean document about science.")
        assert report.is_safe

    def test_detects_xss(self):
        report = scan_content('<script>alert("xss")</script>')
        assert not report.is_safe
        assert any(f.threat_type == ThreatType.XSS for f in report.findings)

    def test_detects_secrets_in_scan(self):
        report = scan_content("api_key = 'my_secret_key_4eC39HqLyjWDarjtT1zdp7dc'")
        assert any(f.threat_type == ThreatType.SECRET_LEAK for f in report.findings)

    def test_scanned_lines(self):
        report = scan_content("line1\nline2\nline3")
        assert report.scanned_lines == 3

    def test_selective_scan(self):
        text = "api_key = 'my_secret_key_1234567890abcdef1234'"
        report = scan_content(text, check_secrets=False)
        assert not any(f.threat_type == ThreatType.SECRET_LEAK for f in report.findings)


# ---------------------------------------------------------------------------
# Policy presets
# ---------------------------------------------------------------------------


class TestPolicyPresets:
    def test_strict_policy(self):
        p = strict_policy()
        assert not p.allow_html
        assert not p.allow_scripts
        assert p.require_https
        assert p.max_length == 50_000

    def test_relaxed_policy(self):
        p = relaxed_policy()
        assert p.allow_html
        assert p.allow_data_urls
        assert p.max_length == 500_000

    def test_content_policy_to_dict(self):
        p = ContentPolicy()
        d = p.to_dict()
        assert "max_length" in d
        assert "allow_html" in d
