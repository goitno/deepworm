"""Tests for glossary module."""

from deepworm.glossary import (
    Glossary,
    GlossaryEntry,
    extract_glossary,
    inject_glossary,
)


SAMPLE_TEXT = """
# Machine Learning Report

Natural Language Processing (NLP) is widely used in healthcare.
Machine Learning is defined as algorithms that improve through experience.
Deep Learning refers to neural networks with many layers.

## Applications

Computer Vision, which is the field of image analysis, has grown rapidly.
NLP and Computer Vision are the two most active areas of research.
Machine Learning models continue to improve in accuracy.
Natural Language Processing enables automated text understanding.
Deep Learning models require large datasets for training.
"""


class TestGlossaryEntry:
    def test_to_dict_basic(self):
        entry = GlossaryEntry(term="ML", definition="Machine Learning", frequency=3)
        d = entry.to_dict()
        assert d["term"] == "ML"
        assert d["definition"] == "Machine Learning"
        assert d["frequency"] == 3
        assert "abbreviation" not in d

    def test_to_dict_with_abbr(self):
        entry = GlossaryEntry(
            term="NLP", definition="Text processing", abbreviation="NLP"
        )
        d = entry.to_dict()
        assert d["abbreviation"] == "NLP"


class TestGlossary:
    def test_add_and_get(self):
        g = Glossary()
        g.add("AI", "Artificial Intelligence")
        assert g.get("AI") is not None
        assert g.get("AI").definition == "Artificial Intelligence"

    def test_get_case_insensitive(self):
        g = Glossary()
        g.add("Machine Learning", "ML algorithms")
        assert g.get("machine learning") is not None

    def test_add_updates_existing(self):
        g = Glossary()
        g.add("AI", "Old definition")
        g.add("AI", "New definition")
        assert len(g.entries) == 1
        assert g.get("AI").definition == "New definition"

    def test_remove(self):
        g = Glossary()
        g.add("AI", "Artificial Intelligence")
        assert g.remove("AI") is True
        assert g.get("AI") is None

    def test_remove_not_found(self):
        g = Glossary()
        assert g.remove("nonexistent") is False

    def test_terms_property(self):
        g = Glossary()
        g.add("Alpha", "First")
        g.add("Beta", "Second")
        assert g.terms == ["Alpha", "Beta"]

    def test_sort_alpha(self):
        g = Glossary()
        g.add("Zebra", "Z")
        g.add("Alpha", "A")
        g.sort("alpha")
        assert g.terms[0] == "Alpha"

    def test_sort_frequency(self):
        g = Glossary()
        e1 = g.add("Rare", "R")
        e1.frequency = 1
        e2 = g.add("Common", "C")
        e2.frequency = 10
        g.sort("frequency")
        assert g.terms[0] == "Common"

    def test_sort_occurrence(self):
        g = Glossary()
        e1 = g.add("Later", "L")
        e1.first_occurrence = 50
        e2 = g.add("Earlier", "E")
        e2.first_occurrence = 5
        g.sort("occurrence")
        assert g.terms[0] == "Earlier"

    def test_to_markdown(self):
        g = Glossary()
        g.add("AI", "Artificial Intelligence")
        g.add("ML", "Machine Learning", abbreviation="ML")
        md = g.to_markdown()
        assert "## Glossary" in md
        assert "**AI**" in md
        assert "(ML)" in md

    def test_to_markdown_empty(self):
        g = Glossary()
        assert g.to_markdown() == ""

    def test_to_definition_list(self):
        g = Glossary()
        g.add("AI", "Artificial Intelligence")
        html = g.to_definition_list()
        assert "<dl>" in html
        assert "<dt>AI</dt>" in html
        assert "<dd>Artificial Intelligence</dd>" in html

    def test_to_dict(self):
        g = Glossary(title="Terms")
        g.add("Test", "A trial")
        d = g.to_dict()
        assert d["title"] == "Terms"
        assert len(d["entries"]) == 1

    def test_merge(self):
        g1 = Glossary()
        g1.add("AI", "Artificial Intelligence")
        e = g1.get("AI")
        e.frequency = 5

        g2 = Glossary()
        g2.add("ML", "Machine Learning")
        g2.add("AI", "")
        e2 = g2.get("AI")
        e2.frequency = 3

        g1.merge(g2)
        assert len(g1.entries) == 2
        assert g1.get("AI").frequency == 8  # Combined
        assert g1.get("ML") is not None

    def test_merge_preserves_definition(self):
        g1 = Glossary()
        g1.add("AI", "Artificial Intelligence")

        g2 = Glossary()
        g2.add("AI", "")

        g1.merge(g2)
        assert g1.get("AI").definition == "Artificial Intelligence"


class TestExtractGlossary:
    def test_finds_definitions(self):
        glossary = extract_glossary(SAMPLE_TEXT)
        ml = glossary.get("Machine Learning")
        assert ml is not None
        assert "algorithms" in ml.definition.lower() or ml.definition != ""

    def test_finds_abbreviations(self):
        # Test abbreviation extraction directly with simple text
        text = "Natural Language Processing (NLP) is important. Natural Language Processing is used widely."
        glossary = extract_glossary(text, min_frequency=1)
        nlp = glossary.get("Natural Language Processing")
        assert nlp is not None
        assert nlp.abbreviation == "NLP"

    def test_tracks_frequency(self):
        glossary = extract_glossary(SAMPLE_TEXT)
        for entry in glossary.entries:
            assert entry.frequency >= 1

    def test_min_frequency_filter(self):
        glossary = extract_glossary(SAMPLE_TEXT, min_frequency=2)
        for entry in glossary.entries:
            assert entry.frequency >= 2

    def test_empty_text(self):
        glossary = extract_glossary("")
        assert glossary.entries == []

    def test_sorted_alphabetically(self):
        glossary = extract_glossary(SAMPLE_TEXT)
        terms = glossary.terms
        assert terms == sorted(terms, key=str.lower)


class TestInjectGlossary:
    def test_inject(self):
        g = Glossary()
        g.add("AI", "Artificial Intelligence")
        result = inject_glossary("# Report\n\nContent here.", g)
        assert "---" in result
        assert "## Glossary" in result
        assert "**AI**" in result

    def test_inject_empty_glossary(self):
        g = Glossary()
        text = "# Report\n\nContent."
        assert inject_glossary(text, g) == text

    def test_inject_preserves_original(self):
        g = Glossary()
        g.add("Test", "A trial")
        result = inject_glossary("Original text", g)
        assert "Original text" in result
