"""Internationalization and localization utilities.

Detect languages, manage translations, extract translatable strings,
and format locale-specific content for reports.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class TranslationEntry:
    """A single translatable string and its translations."""

    key: str
    source: str
    translations: Dict[str, str] = field(default_factory=dict)
    context: str = ""
    max_length: int = 0

    def get(self, locale: str, fallback: bool = True) -> str:
        """Get translation for locale, with optional fallback to source."""
        if locale in self.translations:
            return self.translations[locale]
        # Try base language (e.g., "en" from "en-US")
        base = locale.split("-")[0].split("_")[0]
        if base in self.translations:
            return self.translations[base]
        return self.source if fallback else ""

    def add_translation(self, locale: str, text: str) -> None:
        self.translations[locale] = text

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "source": self.source,
            "translations": self.translations,
            "context": self.context,
        }


@dataclass
class TranslationCatalog:
    """A collection of translations for a project."""

    name: str = ""
    source_locale: str = "en"
    entries: Dict[str, TranslationEntry] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def locales(self) -> Set[str]:
        """All available locales."""
        result: Set[str] = {self.source_locale}
        for entry in self.entries.values():
            result.update(entry.translations.keys())
        return result

    @property
    def entry_count(self) -> int:
        return len(self.entries)

    def add(self, key: str, source: str, context: str = "") -> TranslationEntry:
        """Add a new translatable string."""
        entry = TranslationEntry(key=key, source=source, context=context)
        self.entries[key] = entry
        return entry

    def get(self, key: str, locale: str = "", fallback: bool = True) -> str:
        """Get translated string by key and locale."""
        if key not in self.entries:
            return key if fallback else ""
        entry = self.entries[key]
        if not locale or locale == self.source_locale:
            return entry.source
        return entry.get(locale, fallback=fallback)

    def translate(self, key: str, locale: str, text: str) -> None:
        """Set translation for a key."""
        if key not in self.entries:
            self.add(key, key)
        self.entries[key].add_translation(locale, text)

    def coverage(self, locale: str) -> float:
        """Translation coverage for a locale (0.0 - 1.0)."""
        if not self.entries:
            return 0.0
        translated = sum(
            1 for e in self.entries.values()
            if locale in e.translations
        )
        return translated / len(self.entries)

    def missing(self, locale: str) -> List[str]:
        """Keys missing translation for a locale."""
        return [
            key for key, entry in self.entries.items()
            if locale not in entry.translations
        ]

    def export_po(self, locale: str) -> str:
        """Export translations in PO format."""
        lines = [
            f'# Translation catalog: {self.name}',
            f'# Language: {locale}',
            f'msgid ""',
            f'msgstr ""',
            f'"Content-Type: text/plain; charset=UTF-8\\n"',
            f'"Language: {locale}\\n"',
            "",
        ]
        for key, entry in sorted(self.entries.items()):
            if entry.context:
                lines.append(f"#. {entry.context}")
            lines.append(f'msgid "{_escape_po(entry.source)}"')
            trans = entry.get(locale, fallback=False)
            lines.append(f'msgstr "{_escape_po(trans)}"')
            lines.append("")
        return "\n".join(lines)

    def export_json(self, locale: str) -> Dict[str, str]:
        """Export translations as flat key→value dict."""
        result: Dict[str, str] = {}
        for key, entry in self.entries.items():
            result[key] = entry.get(locale)
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "source_locale": self.source_locale,
            "locales": sorted(self.locales),
            "entry_count": self.entry_count,
            "entries": {k: v.to_dict() for k, v in self.entries.items()},
        }


def _escape_po(text: str) -> str:
    """Escape string for PO format."""
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


@dataclass
class LanguageDetection:
    """Result of language detection."""

    language: str
    confidence: float
    script: str = ""
    details: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "language": self.language,
            "confidence": round(self.confidence, 4),
            "script": self.script,
            "details": {k: round(v, 4) for k, v in self.details.items()},
        }


# Language-specific character patterns and common words
_LANG_PATTERNS: Dict[str, Dict[str, Any]] = {
    "en": {
        "words": {"the", "and", "is", "in", "to", "of", "for", "that", "with", "this"},
        "weight": 1.0,
    },
    "tr": {
        "words": {"ve", "bir", "bu", "için", "ile", "olan", "da", "de", "den", "dan"},
        "chars": re.compile(r"[çğıöşüÇĞİÖŞÜ]"),
        "weight": 1.2,
    },
    "de": {
        "words": {"und", "der", "die", "das", "ist", "ein", "für", "mit", "auf", "den"},
        "chars": re.compile(r"[äöüßÄÖÜ]"),
        "weight": 1.1,
    },
    "fr": {
        "words": {"le", "la", "les", "des", "est", "une", "dans", "pour", "pas", "que"},
        "chars": re.compile(r"[àâéèêëîïôùûüÿçœæ]"),
        "weight": 1.1,
    },
    "es": {
        "words": {"el", "la", "los", "las", "es", "una", "por", "con", "para", "que"},
        "chars": re.compile(r"[áéíóúñ¿¡]"),
        "weight": 1.1,
    },
    "pt": {
        "words": {"os", "as", "uma", "para", "com", "por", "que", "não", "como", "mais"},
        "chars": re.compile(r"[ãõáéíóúâêôç]"),
        "weight": 1.1,
    },
    "it": {
        "words": {"il", "la", "che", "di", "non", "una", "per", "sono", "del", "con"},
        "chars": re.compile(r"[àèéìíîòóùú]"),
        "weight": 1.1,
    },
    "ja": {
        "chars": re.compile(r"[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]"),
        "weight": 2.0,
    },
    "zh": {
        "chars": re.compile(r"[\u4e00-\u9fff]"),
        "weight": 1.5,
    },
    "ko": {
        "chars": re.compile(r"[\uac00-\ud7af\u1100-\u11ff]"),
        "weight": 2.0,
    },
    "ar": {
        "chars": re.compile(r"[\u0600-\u06ff]"),
        "weight": 2.0,
    },
    "ru": {
        "chars": re.compile(r"[\u0400-\u04ff]"),
        "words": {"и", "в", "на", "не", "что", "он", "как", "это", "по", "но"},
        "weight": 1.5,
    },
}

_SCRIPT_NAMES = {
    "Latin": re.compile(r"[a-zA-ZÀ-ÿ]"),
    "CJK": re.compile(r"[\u4e00-\u9fff]"),
    "Hiragana": re.compile(r"[\u3040-\u309f]"),
    "Katakana": re.compile(r"[\u30a0-\u30ff]"),
    "Hangul": re.compile(r"[\uac00-\ud7af]"),
    "Arabic": re.compile(r"[\u0600-\u06ff]"),
    "Cyrillic": re.compile(r"[\u0400-\u04ff]"),
    "Devanagari": re.compile(r"[\u0900-\u097f]"),
}


def detect_language(text: str) -> LanguageDetection:
    """Detect the primary language of text.

    Uses character pattern matching and common word frequency analysis.

    Args:
        text: The text to analyze.

    Returns:
        LanguageDetection with detected language and confidence.
    """
    if not text or not text.strip():
        return LanguageDetection(language="unknown", confidence=0.0)

    text_lower = text.lower()
    words = re.findall(r"\b\w+\b", text_lower)
    word_set = set(words)
    total_words = len(words)

    scores: Dict[str, float] = {}

    for lang, patterns in _LANG_PATTERNS.items():
        score = 0.0
        weight = patterns.get("weight", 1.0)

        # Word matching
        if "words" in patterns and total_words > 0:
            common = word_set & patterns["words"]
            common_count = sum(1 for w in words if w in patterns["words"])
            score += (common_count / total_words) * weight * 100

        # Character pattern matching
        if "chars" in patterns:
            char_matches = len(patterns["chars"].findall(text))
            if char_matches > 0:
                score += min(char_matches / max(len(text), 1) * 200, 80) * weight

        scores[lang] = score

    if not scores or max(scores.values()) == 0:
        return LanguageDetection(language="unknown", confidence=0.0)

    best_lang = max(scores, key=scores.get)  # type: ignore[arg-type]
    best_score = scores[best_lang]
    total_score = sum(scores.values())

    confidence = min(best_score / max(total_score, 1), 1.0)

    # Detect script
    script = _detect_script(text)

    return LanguageDetection(
        language=best_lang,
        confidence=confidence,
        script=script,
        details=scores,
    )


def _detect_script(text: str) -> str:
    """Detect the primary script used in text."""
    script_counts: Dict[str, int] = {}
    for name, pattern in _SCRIPT_NAMES.items():
        count = len(pattern.findall(text))
        if count > 0:
            script_counts[name] = count
    if not script_counts:
        return "Unknown"
    return max(script_counts, key=script_counts.get)  # type: ignore[arg-type]


def extract_translatable(text: str) -> List[Dict[str, Any]]:
    """Extract translatable strings from markdown text.

    Extracts headings, paragraphs, list items, and other
    content blocks that would need translation.

    Args:
        text: Markdown text.

    Returns:
        List of dicts with key, text, and type.
    """
    results: List[Dict[str, Any]] = []
    counter = 0

    # Remove code blocks (not translatable)
    cleaned = re.sub(r"```[\s\S]*?```", "", text)

    for line in cleaned.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        # Headings
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading_match:
            counter += 1
            results.append({
                "key": f"heading_{counter}",
                "text": heading_match.group(2).strip(),
                "type": "heading",
                "level": len(heading_match.group(1)),
            })
            continue

        # List items
        list_match = re.match(r"^[-*+]\s+(.+)$", stripped)
        if list_match:
            counter += 1
            results.append({
                "key": f"list_{counter}",
                "text": list_match.group(1).strip(),
                "type": "list_item",
            })
            continue

        # Table rows (skip separator)
        if stripped.startswith("|") and not re.match(r"^\|[-\s|:]+\|$", stripped):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            for cell in cells:
                if cell.strip():
                    counter += 1
                    results.append({
                        "key": f"cell_{counter}",
                        "text": cell.strip(),
                        "type": "table_cell",
                    })
            continue

        # Regular text (skip markdown-only lines)
        if not re.match(r"^[-=]{3,}$", stripped):
            counter += 1
            results.append({
                "key": f"text_{counter}",
                "text": stripped,
                "type": "paragraph",
            })

    return results


def create_catalog(
    name: str = "",
    source_locale: str = "en",
    entries: Optional[Dict[str, str]] = None,
) -> TranslationCatalog:
    """Create a translation catalog.

    Args:
        name: Catalog name.
        source_locale: Source language code.
        entries: Optional dict of key→source text pairs.

    Returns:
        TranslationCatalog instance.
    """
    catalog = TranslationCatalog(name=name, source_locale=source_locale)
    if entries:
        for key, source in entries.items():
            catalog.add(key, source)
    return catalog


def merge_catalogs(*catalogs: TranslationCatalog) -> TranslationCatalog:
    """Merge multiple catalogs into one.

    Later catalogs override earlier ones for duplicate keys.

    Args:
        *catalogs: Catalogs to merge.

    Returns:
        Merged TranslationCatalog.
    """
    merged = TranslationCatalog(name="merged")
    for catalog in catalogs:
        for key, entry in catalog.entries.items():
            if key in merged.entries:
                # Merge translations
                for locale, trans in entry.translations.items():
                    merged.entries[key].add_translation(locale, trans)
            else:
                merged.entries[key] = TranslationEntry(
                    key=entry.key,
                    source=entry.source,
                    translations=dict(entry.translations),
                    context=entry.context,
                )
    return merged
