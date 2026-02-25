"""Tests for report annotations module."""

from deepworm.annotations import (
    Annotation,
    AnnotationSet,
    AnnotationType,
    annotate_report,
    extract_annotations,
    auto_annotate,
)


class TestAnnotationType:
    def test_values(self):
        assert AnnotationType.COMMENT == "comment"
        assert AnnotationType.QUESTION == "question"
        assert AnnotationType.TODO == "todo"
        assert AnnotationType.WARNING == "warning"
        assert AnnotationType.FACT_CHECK == "fact_check"
        assert AnnotationType.HIGHLIGHT == "highlight"


class TestAnnotation:
    def test_to_dict(self):
        ann = Annotation(id=1, text="Check this", annotation_type=AnnotationType.WARNING)
        d = ann.to_dict()
        assert d["id"] == 1
        assert d["text"] == "Check this"
        assert d["type"] == "warning"

    def test_to_dict_with_target(self):
        ann = Annotation(id=1, text="Note", target="some text", line=5, author="reviewer")
        d = ann.to_dict()
        assert d["target"] == "some text"
        assert d["line"] == 5
        assert d["author"] == "reviewer"

    def test_defaults(self):
        ann = Annotation(id=1, text="test")
        assert ann.annotation_type == AnnotationType.COMMENT
        assert ann.resolved is False
        assert ann.target == ""


class TestAnnotationSet:
    def test_add(self):
        s = AnnotationSet()
        ann = s.add("First note")
        assert ann.id == 1
        assert ann.text == "First note"

    def test_auto_increment_id(self):
        s = AnnotationSet()
        a1 = s.add("One")
        a2 = s.add("Two")
        assert a1.id == 1
        assert a2.id == 2

    def test_get(self):
        s = AnnotationSet()
        s.add("Note")
        assert s.get(1) is not None
        assert s.get(999) is None

    def test_resolve(self):
        s = AnnotationSet()
        s.add("Check")
        assert s.resolve(1) is True
        assert s.get(1).resolved is True
        assert s.resolve(999) is False

    def test_remove(self):
        s = AnnotationSet()
        s.add("Delete me")
        assert s.remove(1) is True
        assert s.get(1) is None
        assert s.remove(1) is False

    def test_unresolved(self):
        s = AnnotationSet()
        s.add("Open")
        s.add("Closed")
        s.resolve(2)
        assert len(s.unresolved) == 1
        assert s.unresolved[0].id == 1

    def test_resolved_list(self):
        s = AnnotationSet()
        s.add("Open")
        s.add("Closed")
        s.resolve(2)
        assert len(s.resolved_list) == 1

    def test_by_type(self):
        s = AnnotationSet()
        s.add("Comment 1", AnnotationType.COMMENT)
        s.add("Warning 1", AnnotationType.WARNING)
        s.add("Comment 2", AnnotationType.COMMENT)
        assert len(s.by_type(AnnotationType.COMMENT)) == 2
        assert len(s.by_type(AnnotationType.WARNING)) == 1

    def test_by_line(self):
        s = AnnotationSet()
        s.add("Line 5 note", line=5)
        s.add("Line 10 note", line=10)
        s.add("Also line 5", line=5)
        assert len(s.by_line(5)) == 2
        assert len(s.by_line(10)) == 1
        assert len(s.by_line(99)) == 0

    def test_summary(self):
        s = AnnotationSet()
        s.add("A", AnnotationType.COMMENT)
        s.add("B", AnnotationType.WARNING)
        s.resolve(1)
        sm = s.summary
        assert sm["total"] == 2
        assert sm["resolved"] == 1
        assert sm["unresolved"] == 1
        assert sm["comment"] == 1
        assert sm["warning"] == 1

    def test_to_markdown(self):
        s = AnnotationSet()
        s.add("Check accuracy", AnnotationType.FACT_CHECK, line=10)
        s.add("Resolved item", AnnotationType.TODO)
        s.resolve(2)
        md = s.to_markdown()
        assert "## Annotations" in md
        assert "Check accuracy" in md
        assert "line 10" in md

    def test_to_markdown_empty(self):
        s = AnnotationSet()
        assert s.to_markdown() == ""

    def test_to_dict(self):
        s = AnnotationSet()
        s.add("Test")
        d = s.to_dict()
        assert "annotations" in d
        assert "summary" in d
        assert len(d["annotations"]) == 1


class TestAnnotateReport:
    def test_inline_style(self):
        s = AnnotationSet()
        s.add("Check this", AnnotationType.WARNING, line=2)
        report = "Line 1\nLine 2\nLine 3"
        result = annotate_report(report, s, style="inline")
        assert "<!-- [warning]" in result
        assert "Check this" in result

    def test_append_style(self):
        s = AnnotationSet()
        s.add("General note")
        report = "# Report\n\nContent"
        result = annotate_report(report, s, style="append")
        assert "---" in result
        assert "## Annotations" in result

    def test_no_annotations(self):
        s = AnnotationSet()
        report = "Clean report"
        assert annotate_report(report, s) == report

    def test_annotations_without_line(self):
        s = AnnotationSet()
        s.add("General comment")
        report = "Line 1\nLine 2"
        result = annotate_report(report, s, style="inline")
        assert "<!-- [comment]" in result


class TestExtractAnnotations:
    def test_html_comments(self):
        text = "Some text <!-- [warning] Check citation --> more text"
        clean, anns = extract_annotations(text)
        assert "Check citation" not in clean
        assert len(anns.annotations) == 1
        assert anns.annotations[0].annotation_type == AnnotationType.WARNING

    def test_critic_markup(self):
        text = "Some text {>> review this <<} more text"
        clean, anns = extract_annotations(text)
        assert "review this" not in clean
        assert len(anns.annotations) == 1

    def test_no_annotations(self):
        text = "Clean text without annotations"
        clean, anns = extract_annotations(text)
        assert clean == text
        assert len(anns.annotations) == 0

    def test_multiple_annotations(self):
        text = "A <!-- [comment] note 1 --> B <!-- [todo] task --> C"
        clean, anns = extract_annotations(text)
        assert len(anns.annotations) == 2

    def test_unknown_type_defaults_comment(self):
        text = "Text <!-- [unknown] note --> end"
        _, anns = extract_annotations(text)
        assert anns.annotations[0].annotation_type == AnnotationType.COMMENT


class TestAutoAnnotate:
    def test_vague_language(self):
        text = "Many experts believe this is correct.\nThis is a fact."
        anns = auto_annotate(text)
        warnings = anns.by_type(AnnotationType.WARNING)
        assert len(warnings) > 0

    def test_unsupported_stats(self):
        text = "The success rate is 95% in all cases."
        anns = auto_annotate(text)
        checks = anns.by_type(AnnotationType.FACT_CHECK)
        assert len(checks) > 0

    def test_stats_with_citation_ok(self):
        text = "The success rate is 95% (Smith, 2023)."
        anns = auto_annotate(text)
        checks = anns.by_type(AnnotationType.FACT_CHECK)
        assert len(checks) == 0

    def test_todo_markers(self):
        text = "This section needs work. TODO: add more data."
        anns = auto_annotate(text)
        todos = anns.by_type(AnnotationType.TODO)
        assert len(todos) > 0

    def test_clean_text(self):
        text = "# Title\n\nThis is a well-written report with proper citations."
        anns = auto_annotate(text)
        assert len(anns.annotations) == 0

    def test_line_numbers(self):
        text = "Line 1 is fine.\nMany experts agree on this."
        anns = auto_annotate(text)
        if anns.annotations:
            assert anns.annotations[0].line > 0
