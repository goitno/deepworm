"""Tests for deepworm.tables."""

from __future__ import annotations

from deepworm.tables import (
    from_csv,
    from_dicts,
    from_pairs,
    make_table,
    to_csv,
    transpose,
)


class TestMakeTable:
    def test_basic(self):
        result = make_table(["Name", "Age"], [["Alice", 30], ["Bob", 25]])
        lines = result.strip().split("\n")
        assert len(lines) == 4  # header + sep + 2 rows
        assert "Name" in lines[0]
        assert "Age" in lines[0]
        assert "---" in lines[1]
        assert "Alice" in lines[2]
        assert "Bob" in lines[3]

    def test_empty_headers(self):
        assert make_table([], []) == ""

    def test_alignment_left(self):
        result = make_table(["Col"], [["data"]], alignment="left")
        sep_line = result.split("\n")[1]
        assert not sep_line.strip().startswith("|:")  # no colon at start

    def test_alignment_right(self):
        result = make_table(["Col"], [["data"]], alignment="right")
        sep_line = result.split("\n")[1]
        assert ":" in sep_line

    def test_alignment_center(self):
        result = make_table(["Col"], [["data"]], alignment="center")
        sep_line = result.split("\n")[1]
        # Center alignment: :---:
        assert sep_line.count(":") >= 2

    def test_mixed_alignment(self):
        result = make_table(
            ["Left", "Right", "Center"],
            [["a", "b", "c"]],
            alignment=["left", "right", "center"],
        )
        assert result  # should not crash

    def test_padding_short_rows(self):
        result = make_table(["A", "B", "C"], [["only_one"]])
        assert "only_one" in result

    def test_pipe_format(self):
        result = make_table(["Col1", "Col2"], [["val1", "val2"]])
        for line in result.split("\n"):
            assert line.startswith("|")
            assert line.endswith("|")


class TestFromDicts:
    def test_basic(self):
        data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]
        result = from_dicts(data)
        assert "name" in result
        assert "age" in result
        assert "Alice" in result
        assert "Bob" in result

    def test_custom_columns(self):
        data = [{"a": 1, "b": 2, "c": 3}]
        result = from_dicts(data, columns=["c", "a"])
        lines = result.split("\n")
        header = lines[0]
        # "c" should come before "a"
        assert header.index("c") < header.index("a")

    def test_empty_data(self):
        assert from_dicts([]) == ""

    def test_missing_keys(self):
        data = [{"a": 1, "b": 2}, {"a": 3}]
        result = from_dicts(data)
        assert "3" in result  # should not crash


class TestFromPairs:
    def test_basic(self):
        pairs = [("Name", "deepworm"), ("Version", "0.4.0")]
        result = from_pairs(pairs)
        assert "Key" in result
        assert "Value" in result
        assert "deepworm" in result

    def test_custom_headers(self):
        pairs = [("Python", "3.9"), ("Node", "18")]
        result = from_pairs(pairs, headers=("Tool", "Version"))
        assert "Tool" in result
        assert "Version" in result


class TestToCsv:
    def test_basic(self):
        result = to_csv(["Name", "Age"], [["Alice", 30], ["Bob", 25]])
        assert "Name,Age" in result
        assert "Alice,30" in result
        assert "Bob,25" in result

    def test_empty(self):
        result = to_csv(["A"], [])
        assert "A" in result


class TestFromCsv:
    def test_basic(self):
        csv_text = "Name,Age\nAlice,30\nBob,25\n"
        result = from_csv(csv_text)
        assert "Name" in result
        assert "Alice" in result
        assert "|" in result

    def test_empty(self):
        assert from_csv("") == ""


class TestTranspose:
    def test_basic(self):
        result = transpose(
            ["Feature", "Score"],
            [["Speed", "9"], ["Safety", "8"]],
            row_header="Metric",
        )
        assert "Metric" in result
        assert "Speed" in result
        assert "Feature" in result

    def test_empty(self):
        assert transpose([], []) == ""
        assert transpose(["A"], []) == ""
