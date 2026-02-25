"""Tests for deepworm.languages."""

from deepworm.languages import (
    Language,
    get_language,
    get_language_instruction,
    list_languages,
)


def test_get_language_english():
    lang = get_language("en")
    assert lang is not None
    assert lang.code == "en"
    assert lang.name == "English"


def test_get_language_turkish():
    lang = get_language("tr")
    assert lang is not None
    assert lang.code == "tr"
    assert lang.native_name == "Türkçe"


def test_get_language_case_insensitive():
    lang = get_language("TR")
    assert lang is not None
    assert lang.code == "tr"


def test_get_language_unknown():
    lang = get_language("xx")
    assert lang is None


def test_list_languages_returns_all():
    langs = list_languages()
    assert len(langs) >= 10
    codes = [l.code for l in langs]
    assert "en" in codes
    assert "tr" in codes
    assert "de" in codes
    assert "fr" in codes
    assert "zh" in codes
    assert "ja" in codes
    assert "ko" in codes


def test_list_languages_sorted():
    langs = list_languages()
    codes = [l.code for l in langs]
    assert codes == sorted(codes)


def test_get_language_instruction_known():
    instruction = get_language_instruction("tr")
    assert "Türkçe" in instruction


def test_get_language_instruction_unknown():
    instruction = get_language_instruction("xx")
    assert instruction == ""


def test_language_dataclass():
    lang = Language(code="test", name="Test", native_name="Test Native", prompt_instruction="Write in Test.")
    assert lang.code == "test"
    assert lang.prompt_instruction == "Write in Test."
