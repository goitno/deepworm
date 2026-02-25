"""Security utilities for content sanitization and validation.

Provides input sanitization, content policy enforcement, secret detection,
URL validation, and safe string operations for document processing.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import string
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Pattern, Set


class ThreatLevel(Enum):
    """Severity levels for security findings."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatType(Enum):
    """Types of security threats detected."""

    XSS = "xss"
    INJECTION = "injection"
    SECRET_LEAK = "secret_leak"
    UNSAFE_URL = "unsafe_url"
    PATH_TRAVERSAL = "path_traversal"
    SSRF = "ssrf"
    PII = "pii"
    MALICIOUS_CONTENT = "malicious_content"


@dataclass
class SecurityFinding:
    """A single security finding."""

    threat_type: ThreatType
    threat_level: ThreatLevel
    message: str
    location: str = ""
    line: int = 0
    suggestion: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "threat_type": self.threat_type.value,
            "threat_level": self.threat_level.value,
            "message": self.message,
            "location": self.location,
            "line": self.line,
            "suggestion": self.suggestion,
        }


@dataclass
class SecurityReport:
    """Result of a security scan."""

    findings: List[SecurityFinding] = field(default_factory=list)
    scanned_lines: int = 0
    scan_type: str = "full"

    @property
    def threat_count(self) -> int:
        return len(self.findings)

    @property
    def max_threat_level(self) -> ThreatLevel:
        if not self.findings:
            return ThreatLevel.NONE
        levels = [ThreatLevel.NONE, ThreatLevel.LOW, ThreatLevel.MEDIUM,
                  ThreatLevel.HIGH, ThreatLevel.CRITICAL]
        max_idx = 0
        for f in self.findings:
            idx = levels.index(f.threat_level)
            if idx > max_idx:
                max_idx = idx
        return levels[max_idx]

    @property
    def is_safe(self) -> bool:
        return all(
            f.threat_level in (ThreatLevel.NONE, ThreatLevel.LOW)
            for f in self.findings
        )

    def by_level(self, level: ThreatLevel) -> List[SecurityFinding]:
        return [f for f in self.findings if f.threat_level == level]

    def by_type(self, threat_type: ThreatType) -> List[SecurityFinding]:
        return [f for f in self.findings if f.threat_type == threat_type]

    def to_markdown(self) -> str:
        lines = ["# Security Report", ""]
        lines.append(f"- **Scanned lines**: {self.scanned_lines}")
        lines.append(f"- **Findings**: {self.threat_count}")
        lines.append(f"- **Max threat level**: {self.max_threat_level.value}")
        lines.append(f"- **Safe**: {'Yes' if self.is_safe else 'No'}")
        lines.append("")

        if self.findings:
            lines.append("## Findings")
            lines.append("")
            for i, f in enumerate(self.findings, 1):
                lines.append(f"### {i}. [{f.threat_level.value.upper()}] {f.threat_type.value}")
                lines.append(f"- **Message**: {f.message}")
                if f.location:
                    lines.append(f"- **Location**: {f.location}")
                if f.line:
                    lines.append(f"- **Line**: {f.line}")
                if f.suggestion:
                    lines.append(f"- **Suggestion**: {f.suggestion}")
                lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "findings": [f.to_dict() for f in self.findings],
            "scanned_lines": self.scanned_lines,
            "threat_count": self.threat_count,
            "max_threat_level": self.max_threat_level.value,
            "is_safe": self.is_safe,
        }


@dataclass
class ContentPolicy:
    """Content policy for validation.

    Defines what is allowed and blocked in content.
    """

    max_length: int = 100_000
    allow_html: bool = False
    allow_scripts: bool = False
    allow_iframes: bool = False
    allow_data_urls: bool = False
    allow_external_urls: bool = True
    blocked_domains: List[str] = field(default_factory=list)
    blocked_patterns: List[str] = field(default_factory=list)
    require_https: bool = False
    max_url_length: int = 2048
    allowed_schemes: List[str] = field(
        default_factory=lambda: ["http", "https", "mailto"]
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_length": self.max_length,
            "allow_html": self.allow_html,
            "allow_scripts": self.allow_scripts,
            "allow_iframes": self.allow_iframes,
            "allow_data_urls": self.allow_data_urls,
            "allow_external_urls": self.allow_external_urls,
            "blocked_domains": self.blocked_domains,
            "require_https": self.require_https,
            "max_url_length": self.max_url_length,
            "allowed_schemes": self.allowed_schemes,
        }


# ---------------------------------------------------------------------------
# XSS / HTML sanitization
# ---------------------------------------------------------------------------

# Tags considered dangerous for XSS
_DANGEROUS_TAGS = re.compile(
    r"<\s*(script|iframe|object|embed|applet|form|input|button|textarea|select"
    r"|meta|link|base|svg|math|style)\b[^>]*>",
    re.IGNORECASE,
)

_EVENT_HANDLERS = re.compile(
    r"\bon\w+\s*=",  # onclick=, onload=, onerror=, etc.
    re.IGNORECASE,
)

_JAVASCRIPT_URI = re.compile(
    r"(?:href|src|action)\s*=\s*[\"']?\s*javascript\s*:",
    re.IGNORECASE,
)

_DATA_URI = re.compile(
    r"(?:href|src)\s*=\s*[\"']?\s*data\s*:",
    re.IGNORECASE,
)


def sanitize_html(text: str) -> str:
    """Remove dangerous HTML tags and attributes from text.

    Strips script tags, event handlers, javascript: URIs, and data: URIs.
    Leaves safe markdown and plain text intact.
    """
    # Remove script/style content entirely
    text = re.sub(r"<script\b[^>]*>.*?</script>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style\b[^>]*>.*?</style>", "", text, flags=re.IGNORECASE | re.DOTALL)

    # Remove dangerous tags
    text = _DANGEROUS_TAGS.sub("", text)

    # Remove event handlers
    text = _EVENT_HANDLERS.sub("", text)

    # Remove javascript: URIs
    text = _JAVASCRIPT_URI.sub("", text)

    # Remove data: URIs
    text = _DATA_URI.sub("", text)

    return text


# ---------------------------------------------------------------------------
# Secret detection
# ---------------------------------------------------------------------------

_SECRET_PATTERNS: List[tuple] = [
    # API keys
    (re.compile(r"(?:api[_-]?key|apikey)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{20,})", re.IGNORECASE),
     "API key", ThreatLevel.HIGH),
    # AWS keys
    (re.compile(r"AKIA[0-9A-Z]{16}"),
     "AWS access key", ThreatLevel.CRITICAL),
    # GitHub tokens
    (re.compile(r"gh[ps]_[a-zA-Z0-9]{36,}"),
     "GitHub token", ThreatLevel.CRITICAL),
    # Generic tokens
    (re.compile(r"(?:token|secret|password|passwd|pwd)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{8,})", re.IGNORECASE),
     "Secret/password", ThreatLevel.HIGH),
    # Private keys
    (re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----"),
     "Private key", ThreatLevel.CRITICAL),
    # JWT
    (re.compile(r"eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}"),
     "JWT token", ThreatLevel.HIGH),
    # Connection strings
    (re.compile(r"(?:mysql|postgres|mongodb|redis)://\S+:\S+@", re.IGNORECASE),
     "Database connection string", ThreatLevel.CRITICAL),
]


def detect_secrets(text: str) -> List[SecurityFinding]:
    """Scan text for leaked secrets, API keys, and credentials."""
    findings: List[SecurityFinding] = []
    lines = text.split("\n")

    for line_num, line in enumerate(lines, 1):
        for pattern, description, level in _SECRET_PATTERNS:
            if pattern.search(line):
                findings.append(SecurityFinding(
                    threat_type=ThreatType.SECRET_LEAK,
                    threat_level=level,
                    message=f"Potential {description} detected",
                    location=line[:80] + ("..." if len(line) > 80 else ""),
                    line=line_num,
                    suggestion=f"Remove or redact the {description}",
                ))
    return findings


# ---------------------------------------------------------------------------
# PII detection
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
_PHONE_RE = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CREDIT_CARD_RE = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")


def detect_pii(text: str) -> List[SecurityFinding]:
    """Detect personally identifiable information in text."""
    findings: List[SecurityFinding] = []
    lines = text.split("\n")

    for line_num, line in enumerate(lines, 1):
        if _EMAIL_RE.search(line):
            findings.append(SecurityFinding(
                threat_type=ThreatType.PII,
                threat_level=ThreatLevel.MEDIUM,
                message="Email address detected",
                line=line_num,
                suggestion="Consider redacting email addresses",
            ))
        if _PHONE_RE.search(line):
            findings.append(SecurityFinding(
                threat_type=ThreatType.PII,
                threat_level=ThreatLevel.MEDIUM,
                message="Phone number detected",
                line=line_num,
                suggestion="Consider redacting phone numbers",
            ))
        if _SSN_RE.search(line):
            findings.append(SecurityFinding(
                threat_type=ThreatType.PII,
                threat_level=ThreatLevel.HIGH,
                message="SSN-like pattern detected",
                line=line_num,
                suggestion="Remove or redact SSN",
            ))
        if _CREDIT_CARD_RE.search(line):
            findings.append(SecurityFinding(
                threat_type=ThreatType.PII,
                threat_level=ThreatLevel.HIGH,
                message="Credit card number-like pattern detected",
                line=line_num,
                suggestion="Remove or redact credit card numbers",
            ))
    return findings


# ---------------------------------------------------------------------------
# URL validation
# ---------------------------------------------------------------------------

_URL_RE = re.compile(
    r"(?:https?|ftp|file|data|javascript)://[^\s<>\"'`\])]+"
    r"|\b(?:https?://)?(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?:/[^\s<>\"'`\])]*)?",
    re.IGNORECASE,
)

_PRIVATE_IP_RE = re.compile(
    r"(?:^|(?<=://))(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    r"|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
    r"|192\.168\.\d{1,3}\.\d{1,3}"
    r"|127\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    r"|localhost"
    r"|0\.0\.0\.0)",
    re.IGNORECASE,
)


def validate_url(url: str, policy: Optional[ContentPolicy] = None) -> List[SecurityFinding]:
    """Validate a URL against security policy."""
    findings: List[SecurityFinding] = []
    policy = policy or ContentPolicy()

    # Length check
    if len(url) > policy.max_url_length:
        findings.append(SecurityFinding(
            threat_type=ThreatType.UNSAFE_URL,
            threat_level=ThreatLevel.LOW,
            message=f"URL exceeds max length ({len(url)} > {policy.max_url_length})",
        ))

    # Scheme check
    scheme_match = re.match(r"([a-zA-Z][a-zA-Z0-9+.-]*):", url)
    if scheme_match:
        scheme = scheme_match.group(1).lower()
        if scheme == "javascript":
            findings.append(SecurityFinding(
                threat_type=ThreatType.XSS,
                threat_level=ThreatLevel.HIGH,
                message="javascript: URL detected",
                suggestion="Remove javascript: URLs",
            ))
        elif scheme == "data" and not policy.allow_data_urls:
            findings.append(SecurityFinding(
                threat_type=ThreatType.UNSAFE_URL,
                threat_level=ThreatLevel.MEDIUM,
                message="data: URL detected",
                suggestion="Remove or convert data: URLs",
            ))
        elif scheme not in policy.allowed_schemes:
            findings.append(SecurityFinding(
                threat_type=ThreatType.UNSAFE_URL,
                threat_level=ThreatLevel.LOW,
                message=f"URL uses disallowed scheme: {scheme}",
            ))

    # HTTPS requirement
    if policy.require_https and url.startswith("http://"):
        findings.append(SecurityFinding(
            threat_type=ThreatType.UNSAFE_URL,
            threat_level=ThreatLevel.LOW,
            message="URL uses HTTP instead of HTTPS",
            suggestion="Use HTTPS for secure communication",
        ))

    # Private IP / SSRF check
    if _PRIVATE_IP_RE.search(url):
        findings.append(SecurityFinding(
            threat_type=ThreatType.SSRF,
            threat_level=ThreatLevel.HIGH,
            message="URL points to private/internal network",
            suggestion="Remove internal URLs",
        ))

    # Blocked domains
    for domain in policy.blocked_domains:
        if domain.lower() in url.lower():
            findings.append(SecurityFinding(
                threat_type=ThreatType.UNSAFE_URL,
                threat_level=ThreatLevel.MEDIUM,
                message=f"URL contains blocked domain: {domain}",
            ))

    return findings


def extract_urls(text: str) -> List[str]:
    """Extract all URLs from text."""
    return _URL_RE.findall(text)


# ---------------------------------------------------------------------------
# Path traversal
# ---------------------------------------------------------------------------

_PATH_TRAVERSAL_RE = re.compile(r"\.\.[/\\]|[/\\]\.\.")


def check_path_traversal(path: str) -> List[SecurityFinding]:
    """Check a file path for traversal attacks."""
    findings: List[SecurityFinding] = []

    if _PATH_TRAVERSAL_RE.search(path):
        findings.append(SecurityFinding(
            threat_type=ThreatType.PATH_TRAVERSAL,
            threat_level=ThreatLevel.HIGH,
            message="Path traversal pattern detected",
            location=path,
            suggestion="Normalize path and check it stays within allowed directory",
        ))

    # Null byte
    if "\x00" in path:
        findings.append(SecurityFinding(
            threat_type=ThreatType.PATH_TRAVERSAL,
            threat_level=ThreatLevel.HIGH,
            message="Null byte in path",
            location=repr(path),
            suggestion="Reject paths containing null bytes",
        ))

    return findings


# ---------------------------------------------------------------------------
# Content sanitization
# ---------------------------------------------------------------------------

def sanitize_markdown(text: str) -> str:
    """Sanitize markdown content by removing dangerous elements.

    Removes:
      - HTML script/style tags and event handlers
      - javascript: links
      - data: URIs (in HTML attributes)

    Preserves:
      - Standard markdown syntax
      - Safe HTML tags (p, em, strong, a with safe href, etc.)
    """
    # Remove script/style blocks
    text = re.sub(r"<script\b[^>]*>.*?</script>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style\b[^>]*>.*?</style>", "", text, flags=re.IGNORECASE | re.DOTALL)

    # Remove event handlers from any HTML tags
    text = re.sub(r"\s+on\w+\s*=\s*[\"'][^\"']*[\"']", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+on\w+\s*=\s*\S+", "", text, flags=re.IGNORECASE)

    # Remove javascript: in markdown links
    text = re.sub(
        r"\[([^\]]*)\]\(javascript:[^)]*\)",
        r"[\1](#)",
        text,
        flags=re.IGNORECASE,
    )

    return text


def redact_text(text: str, patterns: Optional[List[str]] = None) -> str:
    """Redact sensitive patterns from text.

    Args:
        text: Input text to redact.
        patterns: Custom regex patterns to redact. If None, uses default
                  patterns for emails, phone numbers, and SSNs.
    """
    if patterns is None:
        # Default redaction
        text = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
        text = _PHONE_RE.sub("[REDACTED_PHONE]", text)
        text = _SSN_RE.sub("[REDACTED_SSN]", text)
        text = _CREDIT_CARD_RE.sub("[REDACTED_CC]", text)
    else:
        for p in patterns:
            text = re.sub(p, "[REDACTED]", text)
    return text


# ---------------------------------------------------------------------------
# Hashing & token utilities
# ---------------------------------------------------------------------------

def content_hash(text: str, algorithm: str = "sha256") -> str:
    """Generate a hash of content for integrity checking."""
    if algorithm == "sha256":
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
    elif algorithm == "sha512":
        return hashlib.sha512(text.encode("utf-8")).hexdigest()
    elif algorithm == "md5":
        return hashlib.md5(text.encode("utf-8")).hexdigest()
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")


def generate_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length)


def constant_time_compare(a: str, b: str) -> bool:
    """Compare two strings in constant time to prevent timing attacks."""
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def mask_secret(value: str, visible: int = 4) -> str:
    """Mask a secret value, showing only the last N characters.

    Example: mask_secret("sk-1234567890abcdef") -> "***************cdef"
    """
    if len(value) <= visible:
        return "*" * len(value)
    return "*" * (len(value) - visible) + value[-visible:]


# ---------------------------------------------------------------------------
# Full scan
# ---------------------------------------------------------------------------

def scan_content(
    text: str,
    policy: Optional[ContentPolicy] = None,
    check_secrets: bool = True,
    check_pii_flag: bool = True,
    check_xss: bool = True,
    check_urls: bool = True,
) -> SecurityReport:
    """Run a comprehensive security scan on text content.

    Args:
        text: Content to scan.
        policy: Content policy for URL validation.
        check_secrets: Scan for leaked secrets.
        check_pii_flag: Scan for PII.
        check_xss: Scan for XSS patterns.
        check_urls: Validate URLs.

    Returns:
        SecurityReport with all findings.
    """
    findings: List[SecurityFinding] = []
    lines = text.split("\n")
    policy = policy or ContentPolicy()

    # Content length
    if len(text) > policy.max_length:
        findings.append(SecurityFinding(
            threat_type=ThreatType.MALICIOUS_CONTENT,
            threat_level=ThreatLevel.LOW,
            message=f"Content exceeds max length ({len(text)} > {policy.max_length})",
        ))

    # XSS detection
    if check_xss:
        for line_num, line in enumerate(lines, 1):
            if _DANGEROUS_TAGS.search(line):
                findings.append(SecurityFinding(
                    threat_type=ThreatType.XSS,
                    threat_level=ThreatLevel.HIGH,
                    message="Dangerous HTML tag detected",
                    line=line_num,
                    location=line[:80],
                    suggestion="Remove or sanitize HTML tags",
                ))
            if _EVENT_HANDLERS.search(line):
                findings.append(SecurityFinding(
                    threat_type=ThreatType.XSS,
                    threat_level=ThreatLevel.HIGH,
                    message="HTML event handler detected",
                    line=line_num,
                    suggestion="Remove event handlers",
                ))
            if _JAVASCRIPT_URI.search(line):
                findings.append(SecurityFinding(
                    threat_type=ThreatType.XSS,
                    threat_level=ThreatLevel.HIGH,
                    message="javascript: URI detected",
                    line=line_num,
                    suggestion="Remove javascript: URIs",
                ))

    # Secret detection
    if check_secrets:
        findings.extend(detect_secrets(text))

    # PII detection
    if check_pii_flag:
        findings.extend(detect_pii(text))

    # URL validation
    if check_urls:
        urls = extract_urls(text)
        for url in urls:
            findings.extend(validate_url(url, policy))

    return SecurityReport(
        findings=findings,
        scanned_lines=len(lines),
        scan_type="full",
    )


# ---------------------------------------------------------------------------
# Policy presets
# ---------------------------------------------------------------------------

def strict_policy() -> ContentPolicy:
    """Create a strict content policy.

    - No HTML, scripts, iframes, data URLs
    - HTTPS required
    - Short max length
    """
    return ContentPolicy(
        max_length=50_000,
        allow_html=False,
        allow_scripts=False,
        allow_iframes=False,
        allow_data_urls=False,
        require_https=True,
        allowed_schemes=["https", "mailto"],
    )


def relaxed_policy() -> ContentPolicy:
    """Create a relaxed content policy for trusted content."""
    return ContentPolicy(
        max_length=500_000,
        allow_html=True,
        allow_scripts=False,
        allow_iframes=False,
        allow_data_urls=True,
        require_https=False,
        allowed_schemes=["http", "https", "mailto", "ftp"],
    )
