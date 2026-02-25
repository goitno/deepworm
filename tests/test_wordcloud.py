"""Tests for word cloud and frequency analysis."""

import pytest
from deepworm.wordcloud import (
    WordFrequency,
    WordCloudData,
    generate_word_cloud,
    compare_word_clouds,
    tfidf_cloud,
    _tokenize,
)


# --- WordFrequency ---

class TestWordFrequency:
    def test_basic(self):
        wf = WordFrequency(word="test", count=5, frequency=0.1)
        assert wf.word == "test"
        assert wf.count == 5

    def test_to_dict(self):
        wf = WordFrequency(word="test", count=5, frequency=0.1, rank=1, weight=0.8)
        d = wf.to_dict()
        assert d["word"] == "test"
        assert d["count"] == 5
        assert d["rank"] == 1


# --- WordCloudData ---

class TestWordCloudData:
    def test_empty(self):
        data = WordCloudData()
        assert len(data.words) == 0
        assert data.total_words == 0

    def test_top(self):
        data = WordCloudData()
        data.words = [
            WordFrequency("a", 10, 0.1, weight=0.8),
            WordFrequency("b", 5, 0.05, weight=0.4),
            WordFrequency("c", 20, 0.2, weight=1.0),
        ]
        top = data.top
        assert top[0].word == "c"
        assert len(top) <= 10

    def test_filter_by_min_count(self):
        data = WordCloudData()
        data.words = [
            WordFrequency("a", 10, 0.1),
            WordFrequency("b", 2, 0.02),
            WordFrequency("c", 1, 0.01),
        ]
        filtered = data.filter_by_min_count(3)
        assert len(filtered) == 1

    def test_to_size_map(self):
        data = WordCloudData()
        data.words = [
            WordFrequency("big", 20, 0.2, weight=1.0),
            WordFrequency("small", 5, 0.05, weight=0.0),
        ]
        sizes = data.to_size_map(min_size=12, max_size=72)
        assert len(sizes) == 2
        assert sizes[0]["size"] == 72  # max weight → max size
        assert sizes[1]["size"] == 12  # min weight → min size

    def test_to_size_map_empty(self):
        data = WordCloudData()
        assert data.to_size_map() == []

    def test_to_markdown(self):
        data = WordCloudData(source_title="Test Report")
        data.words = [
            WordFrequency("python", 15, 0.1, rank=1, weight=1.0),
        ]
        data.total_words = 150
        data.unique_words = 50
        md = data.to_markdown()
        assert "## Word Frequencies" in md
        assert "python" in md
        assert "Test Report" in md
        assert "| Rank |" in md

    def test_to_html_cloud(self):
        data = WordCloudData()
        data.words = [
            WordFrequency("python", 15, 0.1, weight=1.0),
        ]
        html = data.to_html_cloud()
        assert "python" in html
        assert "font-size:" in html

    def test_to_html_cloud_empty(self):
        data = WordCloudData()
        html = data.to_html_cloud()
        assert "No words" in html

    def test_to_csv(self):
        data = WordCloudData()
        data.words = [
            WordFrequency("test", 10, 0.1, rank=1, weight=0.5),
        ]
        csv = data.to_csv()
        assert "word,count,frequency,rank,weight" in csv
        assert "test,10" in csv

    def test_to_dict(self):
        data = WordCloudData(total_words=100, unique_words=50)
        data.words = [
            WordFrequency("test", 10, 0.1, rank=1, weight=0.5),
        ]
        d = data.to_dict()
        assert d["total_words"] == 100
        assert d["unique_words"] == 50
        assert len(d["words"]) == 1


# --- Generate Word Cloud ---

SAMPLE_TEXT = """
Python is a versatile programming language. Python is used for machine learning,
web development, data science, and automation. Machine learning with Python
has become incredibly popular. Data science tools in Python include pandas,
numpy, and scikit-learn. Python programming enables rapid development
and clean code. The Python community is large and welcoming.
Python libraries make complex tasks simple.
"""


class TestGenerateWordCloud:
    def test_generates_cloud(self):
        cloud = generate_word_cloud(SAMPLE_TEXT)
        assert len(cloud.words) > 0
        assert cloud.total_words > 0

    def test_python_is_top(self):
        cloud = generate_word_cloud(SAMPLE_TEXT, min_count=1)
        top = cloud.top
        assert top[0].word == "python"

    def test_respects_max_words(self):
        cloud = generate_word_cloud(SAMPLE_TEXT, max_words=5, min_count=1)
        assert len(cloud.words) <= 5

    def test_respects_min_length(self):
        cloud = generate_word_cloud(SAMPLE_TEXT, min_length=5, min_count=1)
        for wf in cloud.words:
            assert len(wf.word) >= 5

    def test_respects_min_count(self):
        cloud = generate_word_cloud(SAMPLE_TEXT, min_count=3)
        for wf in cloud.words:
            assert wf.count >= 3

    def test_custom_stop_words(self):
        cloud = generate_word_cloud(
            SAMPLE_TEXT,
            custom_stop_words={"python"},
            min_count=1,
        )
        words = [w.word for w in cloud.words]
        assert "python" not in words

    def test_ranks_assigned(self):
        cloud = generate_word_cloud(SAMPLE_TEXT, min_count=1)
        ranks = [w.rank for w in cloud.words]
        assert 1 in ranks

    def test_weights_normalized(self):
        cloud = generate_word_cloud(SAMPLE_TEXT, min_count=1)
        for wf in cloud.words:
            assert 0.0 <= wf.weight <= 1.0

    def test_empty_text(self):
        cloud = generate_word_cloud("")
        assert len(cloud.words) == 0

    def test_with_title(self):
        cloud = generate_word_cloud(SAMPLE_TEXT, title="Test")
        assert cloud.source_title == "Test"

    def test_all_stop_words(self):
        cloud = generate_word_cloud("the and or but if is a it")
        assert len(cloud.words) == 0

    def test_frequency_sum(self):
        cloud = generate_word_cloud(SAMPLE_TEXT, min_count=1)
        # Frequencies should be reasonable
        for wf in cloud.words:
            assert 0 < wf.frequency <= 1.0


# --- Compare Word Clouds ---

class TestCompareWordClouds:
    def test_compare_similar(self):
        cloud_a = generate_word_cloud(
            "Python is great for machine learning and data science.",
            min_count=1,
        )
        cloud_b = generate_word_cloud(
            "Python excels at machine learning and deep learning.",
            min_count=1,
        )
        result = compare_word_clouds(cloud_a, cloud_b)
        assert result["shared_count"] > 0
        assert "top_shared" in result

    def test_compare_different(self):
        cloud_a = generate_word_cloud(
            "astronomy telescope galaxy nebula constellation stars",
            min_count=1,
        )
        cloud_b = generate_word_cloud(
            "cooking recipe kitchen ingredients baking flour",
            min_count=1,
        )
        result = compare_word_clouds(cloud_a, cloud_b)
        assert result["shared_count"] == 0

    def test_compare_structure(self):
        cloud_a = generate_word_cloud("testing code code testing", min_count=1)
        cloud_b = generate_word_cloud("testing code code testing", min_count=1)
        result = compare_word_clouds(cloud_a, cloud_b)
        assert "shared_count" in result
        assert "unique_to_a" in result
        assert "unique_to_b" in result
        assert "overlap_ratio" in result


# --- TF-IDF Cloud ---

class TestTfidfCloud:
    def test_tfidf_multiple_docs(self):
        texts = [
            "Python is great for machine learning and data science.",
            "JavaScript is popular for web development and frontend.",
            "Rust is known for memory safety and performance.",
        ]
        clouds = tfidf_cloud(texts, min_length=3)
        assert len(clouds) == 3
        for cloud in clouds:
            assert len(cloud.words) > 0

    def test_tfidf_distinctive_words(self):
        texts = [
            "Python Python Python data data data science science",
            "JavaScript JavaScript JavaScript web web web frontend frontend",
        ]
        clouds = tfidf_cloud(texts, min_length=3)
        # Python should be prominent in first, JavaScript in second
        top_a = [w.word for w in clouds[0].top[:3]]
        top_b = [w.word for w in clouds[1].top[:3]]
        assert "python" in top_a
        assert "javascript" in top_b

    def test_tfidf_empty_input(self):
        assert tfidf_cloud([]) == []

    def test_tfidf_single_doc(self):
        clouds = tfidf_cloud(["Python machine learning"], min_length=3)
        assert len(clouds) == 1


# --- Tokenize ---

class TestTokenize:
    def test_basic(self):
        tokens = _tokenize("Hello World!")
        assert "hello" in tokens
        assert "world" in tokens

    def test_strips_markdown(self):
        tokens = _tokenize("## Heading\n**Bold** text")
        assert "heading" in tokens
        assert "bold" in tokens

    def test_strips_code_blocks(self):
        tokens = _tokenize("Before\n```python\ncode\n```\nAfter")
        assert "before" in tokens
        assert "code" not in tokens

    def test_strips_urls(self):
        tokens = _tokenize("Visit https://example.com for more")
        assert "example" not in tokens
        assert "visit" in tokens
