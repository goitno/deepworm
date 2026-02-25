"""Tests for internationalization and localization module."""

import pytest
from deepworm.i18n import (
    TranslationEntry,
    TranslationCatalog,
    LanguageDetection,
    detect_language,
    extract_translatable,
    create_catalog,
    merge_catalogs,
    _detect_script,
)


# --- TranslationEntry ---

class TestTranslationEntry:
    def test_basic(self):
        entry = TranslationEntry(key="hello", source="Hello")
        assert entry.key == "hello"
        assert entry.source == "Hello"

    def test_get_source(self):
        entry = TranslationEntry(key="hello", source="Hello")
        assert entry.get("en") == "Hello"  # fallback

    def test_get_translation(self):
        entry = TranslationEntry(
            key="hello", source="Hello",
            translations={"tr": "Merhaba", "de": "Hallo"},
        )
        assert entry.get("tr") == "Merhaba"
        assert entry.get("de") == "Hallo"

    def test_get_base_locale(self):
        entry = TranslationEntry(
            key="hello", source="Hello",
            translations={"tr": "Merhaba"},
        )
        assert entry.get("tr-TR") == "Merhaba"

    def test_get_fallback(self):
        entry = TranslationEntry(key="hello", source="Hello")
        assert entry.get("xx") == "Hello"  # fallback to source

    def test_get_no_fallback(self):
        entry = TranslationEntry(key="hello", source="Hello")
        assert entry.get("xx", fallback=False) == ""

    def test_add_translation(self):
        entry = TranslationEntry(key="hello", source="Hello")
        entry.add_translation("fr", "Bonjour")
        assert entry.get("fr") == "Bonjour"

    def test_to_dict(self):
        entry = TranslationEntry(key="hello", source="Hello", context="greeting")
        d = entry.to_dict()
        assert d["key"] == "hello"
        assert d["context"] == "greeting"


# --- TranslationCatalog ---

class TestTranslationCatalog:
    def test_empty(self):
        catalog = TranslationCatalog()
        assert catalog.entry_count == 0

    def test_add(self):
        catalog = TranslationCatalog()
        catalog.add("hello", "Hello")
        assert catalog.entry_count == 1

    def test_get(self):
        catalog = TranslationCatalog(source_locale="en")
        catalog.add("hello", "Hello")
        catalog.translate("hello", "tr", "Merhaba")
        assert catalog.get("hello") == "Hello"
        assert catalog.get("hello", "tr") == "Merhaba"

    def test_get_missing_key(self):
        catalog = TranslationCatalog()
        assert catalog.get("missing") == "missing"

    def test_locales(self):
        catalog = TranslationCatalog(source_locale="en")
        catalog.add("hello", "Hello")
        catalog.translate("hello", "tr", "Merhaba")
        catalog.translate("hello", "de", "Hallo")
        assert "en" in catalog.locales
        assert "tr" in catalog.locales
        assert "de" in catalog.locales

    def test_coverage(self):
        catalog = TranslationCatalog()
        catalog.add("a", "A")
        catalog.add("b", "B")
        catalog.translate("a", "tr", "A-tr")
        assert catalog.coverage("tr") == 0.5

    def test_missing(self):
        catalog = TranslationCatalog()
        catalog.add("a", "A")
        catalog.add("b", "B")
        catalog.translate("a", "tr", "A-tr")
        assert "b" in catalog.missing("tr")
        assert "a" not in catalog.missing("tr")

    def test_export_po(self):
        catalog = TranslationCatalog(name="test")
        catalog.add("hello", "Hello")
        catalog.translate("hello", "tr", "Merhaba")
        po = catalog.export_po("tr")
        assert "Merhaba" in po
        assert "Hello" in po

    def test_export_json(self):
        catalog = TranslationCatalog()
        catalog.add("hello", "Hello")
        catalog.translate("hello", "tr", "Merhaba")
        j = catalog.export_json("tr")
        assert j["hello"] == "Merhaba"

    def test_to_dict(self):
        catalog = TranslationCatalog(name="test")
        catalog.add("a", "A")
        d = catalog.to_dict()
        assert d["name"] == "test"
        assert d["entry_count"] == 1


# --- LanguageDetection ---

class TestLanguageDetection:
    def test_to_dict(self):
        ld = LanguageDetection(language="en", confidence=0.9, script="Latin")
        d = ld.to_dict()
        assert d["language"] == "en"
        assert d["confidence"] == 0.9


# --- detect_language ---

class TestDetectLanguage:
    def test_english(self):
        result = detect_language(
            "The quick brown fox jumps over the lazy dog. This is a test."
        )
        assert result.language == "en"
        assert result.confidence > 0

    def test_turkish(self):
        result = detect_language(
            "Bu bir test cümlesidir. Türkçe için özel karakterler içerir."
        )
        assert result.language == "tr"

    def test_german(self):
        result = detect_language(
            "Das ist ein Test. Die Qualität der Übersetzung ist sehr gut."
        )
        assert result.language == "de"

    def test_french(self):
        result = detect_language(
            "C'est un test. La qualité de la traduction est très bonne."
        )
        assert result.language == "fr"

    def test_spanish(self):
        result = detect_language(
            "Esta es una prueba. La calidad de la traducción es muy buena."
        )
        assert result.language == "es"

    def test_empty(self):
        result = detect_language("")
        assert result.language == "unknown"
        assert result.confidence == 0

    def test_script_detection(self):
        result = detect_language("The quick brown fox jumps over the lazy dog.")
        assert result.script == "Latin"


# --- extract_translatable ---

class TestExtractTranslatable:
    def test_headings(self):
        results = extract_translatable("# Title\n\n## Section")
        headings = [r for r in results if r["type"] == "heading"]
        assert len(headings) == 2
        assert headings[0]["text"] == "Title"

    def test_list_items(self):
        results = extract_translatable("- Item one\n- Item two")
        items = [r for r in results if r["type"] == "list_item"]
        assert len(items) == 2

    def test_paragraphs(self):
        results = extract_translatable("This is a paragraph.")
        paras = [r for r in results if r["type"] == "paragraph"]
        assert len(paras) >= 1

    def test_skips_code_blocks(self):
        text = "Text\n```python\ncode here\n```\nMore text"
        results = extract_translatable(text)
        texts = [r["text"] for r in results]
        assert not any("code here" in t for t in texts)

    def test_table_cells(self):
        text = "| Name | Value |\n|------|-------|\n| A | B |"
        results = extract_translatable(text)
        cells = [r for r in results if r["type"] == "table_cell"]
        assert len(cells) >= 2

    def test_empty(self):
        results = extract_translatable("")
        assert len(results) == 0


# --- create_catalog ---

class TestCreateCatalog:
    def test_basic(self):
        catalog = create_catalog("test", entries={"hello": "Hello"})
        assert catalog.entry_count == 1
        assert catalog.get("hello") == "Hello"

    def test_empty(self):
        catalog = create_catalog()
        assert catalog.entry_count == 0


# --- merge_catalogs ---

class TestMergeCatalogs:
    def test_merge(self):
        c1 = create_catalog(entries={"a": "A"})
        c2 = create_catalog(entries={"b": "B"})
        merged = merge_catalogs(c1, c2)
        assert merged.entry_count == 2

    def test_merge_translations(self):
        c1 = create_catalog(entries={"hello": "Hello"})
        c1.translate("hello", "tr", "Merhaba")
        c2 = create_catalog(entries={"hello": "Hello"})
        c2.translate("hello", "de", "Hallo")
        merged = merge_catalogs(c1, c2)
        assert merged.get("hello", "tr") == "Merhaba"
        assert merged.get("hello", "de") == "Hallo"


# --- _detect_script ---

class TestDetectScript:
    def test_latin(self):
        assert _detect_script("Hello World") == "Latin"

    def test_cyrillic(self):
        assert _detect_script("Привет мир") == "Cyrillic"

    def test_unknown(self):
        assert _detect_script("123 456") == "Unknown"
