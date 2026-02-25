"""Tests for deepworm.protocols module."""

import pytest
from deepworm.protocols import (
    ResultStatus,
    Ok,
    Err,
    ok,
    err,
    try_result,
    Some,
    Nothing,
    NOTHING,
    some,
    nothing,
    Serializable,
    Renderable,
    Validatable,
    Disposable,
    Configurable,
    Identifiable,
    is_serializable,
    is_renderable,
    is_validatable,
    is_dict_like,
    is_list_like,
    is_callable,
    is_numeric,
    is_non_empty_string,
    Lazy,
    Left,
    Right,
    left,
    right,
    Pair,
    pair,
    safe_int,
    safe_float,
    safe_bool,
    safe_str,
)


# ---- Result type ----


class TestOk:
    def test_ok_creation(self):
        r = Ok(42)
        assert r.value == 42
        assert r.status == ResultStatus.OK

    def test_ok_properties(self):
        r = ok("hello")
        assert r.is_ok is True
        assert r.is_err is False

    def test_ok_unwrap(self):
        r = ok(99)
        assert r.unwrap() == 99

    def test_ok_unwrap_or(self):
        r = ok(10)
        assert r.unwrap_or(0) == 10

    def test_ok_map(self):
        r = ok(5)
        mapped = r.map(lambda x: x * 2)
        assert mapped.unwrap() == 10
        assert mapped.is_ok is True


class TestErr:
    def test_err_creation(self):
        r = Err("fail")
        assert r.error == "fail"
        assert r.status == ResultStatus.ERR

    def test_err_properties(self):
        r = err("oops")
        assert r.is_ok is False
        assert r.is_err is True

    def test_err_unwrap_raises(self):
        r = err("problem")
        with pytest.raises(ValueError, match="problem"):
            r.unwrap()

    def test_err_unwrap_or(self):
        r = err("fail")
        assert r.unwrap_or(42) == 42

    def test_err_map_passes_through(self):
        r = err("fail")
        mapped = r.map(lambda x: x * 2)
        assert mapped.is_err is True
        assert mapped.error == "fail"


class TestTryResult:
    def test_try_success(self):
        r = try_result(int, "42")
        assert r.is_ok is True
        assert r.unwrap() == 42

    def test_try_failure(self):
        r = try_result(int, "not_a_number")
        assert r.is_err is True
        assert "invalid literal" in r.error

    def test_try_with_kwargs(self):
        def add(a, b):
            return a + b

        r = try_result(add, 3, b=7)
        assert r.unwrap() == 10


# ---- Option type ----


class TestSome:
    def test_some_creation(self):
        s = Some(42)
        assert s.value == 42
        assert s.is_some is True
        assert s.is_nothing is False

    def test_some_unwrap(self):
        s = some("hello")
        assert s.unwrap() == "hello"

    def test_some_unwrap_or(self):
        s = some(10)
        assert s.unwrap_or(0) == 10

    def test_some_map(self):
        s = some(3)
        mapped = s.map(lambda x: x ** 2)
        assert mapped.unwrap() == 9


class TestNothing:
    def test_nothing_properties(self):
        n = Nothing()
        assert n.is_some is False
        assert n.is_nothing is True

    def test_nothing_unwrap_raises(self):
        with pytest.raises(ValueError, match="Nothing"):
            NOTHING.unwrap()

    def test_nothing_unwrap_or(self):
        assert NOTHING.unwrap_or(42) == 42

    def test_nothing_map(self):
        mapped = nothing().map(lambda x: x * 2)
        assert mapped.is_nothing is True

    def test_nothing_factory(self):
        n = nothing()
        assert n is NOTHING


# ---- Protocols ----


class TestProtocols:
    def test_serializable(self):
        class MyObj:
            def to_dict(self):
                return {"x": 1}

        assert isinstance(MyObj(), Serializable)
        assert is_serializable(MyObj())

    def test_renderable(self):
        class MyWidget:
            def render(self):
                return "<div/>"

        assert isinstance(MyWidget(), Renderable)
        assert is_renderable(MyWidget())

    def test_validatable(self):
        class MyForm:
            def validate(self):
                return True

        assert isinstance(MyForm(), Validatable)
        assert is_validatable(MyForm())

    def test_disposable(self):
        class MyResource:
            def dispose(self):
                pass

        assert isinstance(MyResource(), Disposable)

    def test_configurable(self):
        class MyService:
            def configure(self, config):
                self.cfg = config

        assert isinstance(MyService(), Configurable)

    def test_identifiable(self):
        class MyEntity:
            @property
            def id(self):
                return "abc-123"

        assert isinstance(MyEntity(), Identifiable)

    def test_non_protocol(self):
        assert not is_serializable("string")
        assert not is_renderable(42)
        assert not is_validatable([1, 2, 3])


# ---- Type guards ----


class TestTypeGuards:
    def test_is_dict_like(self):
        assert is_dict_like({}) is True
        assert is_dict_like({"a": 1}) is True
        assert is_dict_like([]) is False
        assert is_dict_like("str") is False

    def test_is_list_like(self):
        assert is_list_like([1, 2]) is True
        assert is_list_like((1, 2)) is True
        assert is_list_like("string") is False
        assert is_list_like(b"bytes") is False
        assert is_list_like(42) is False

    def test_is_callable(self):
        assert is_callable(len) is True
        assert is_callable(lambda: 1) is True
        assert is_callable(42) is False

    def test_is_numeric(self):
        assert is_numeric(42) is True
        assert is_numeric(3.14) is True
        assert is_numeric(True) is False
        assert is_numeric("42") is False

    def test_is_non_empty_string(self):
        assert is_non_empty_string("hello") is True
        assert is_non_empty_string("") is False
        assert is_non_empty_string("   ") is False
        assert is_non_empty_string(42) is False


# ---- Lazy ----


class TestLazy:
    def test_lazy_evaluation(self):
        calls = []
        def factory():
            calls.append(1)
            return 42

        lazy = Lazy(factory)
        assert lazy.is_computed is False
        assert len(calls) == 0
        assert lazy.value == 42
        assert lazy.is_computed is True
        assert len(calls) == 1

    def test_lazy_caching(self):
        counter = [0]
        def factory():
            counter[0] += 1
            return "computed"

        lazy = Lazy(factory)
        _ = lazy.value
        _ = lazy.value
        _ = lazy.value
        assert counter[0] == 1

    def test_lazy_reset(self):
        counter = [0]
        def factory():
            counter[0] += 1
            return counter[0]

        lazy = Lazy(factory)
        assert lazy.value == 1
        lazy.reset()
        assert lazy.is_computed is False
        assert lazy.value == 2


# ---- Either ----


class TestEither:
    def test_left(self):
        l = left("error")
        assert l.is_left is True
        assert l.is_right is False
        assert l.value == "error"

    def test_right(self):
        r = right(42)
        assert r.is_left is False
        assert r.is_right is True
        assert r.value == 42

    def test_left_right_types(self):
        assert isinstance(left(1), Left)
        assert isinstance(right(1), Right)


# ---- Pair ----


class TestPair:
    def test_pair_creation(self):
        p = pair(1, "two")
        assert p.first == 1
        assert p.second == "two"

    def test_pair_to_tuple(self):
        p = pair("a", "b")
        assert p.to_tuple() == ("a", "b")

    def test_pair_swap(self):
        p = pair(1, 2)
        swapped = p.swap()
        assert swapped.first == 2
        assert swapped.second == 1


# ---- Safe conversions ----


class TestSafeConversions:
    def test_safe_int(self):
        assert safe_int("42") == 42
        assert safe_int("nope") == 0
        assert safe_int("nope", -1) == -1
        assert safe_int(None) == 0

    def test_safe_float(self):
        assert safe_float("3.14") == 3.14
        assert safe_float("nope") == 0.0
        assert safe_float("nope", -1.0) == -1.0

    def test_safe_bool(self):
        assert safe_bool(True) is True
        assert safe_bool(False) is False
        assert safe_bool("true") is True
        assert safe_bool("yes") is True
        assert safe_bool("1") is True
        assert safe_bool("false") is False
        assert safe_bool("no") is False

    def test_safe_str(self):
        assert safe_str(42) == "42"
        assert safe_str(None) == ""
        assert safe_str(None, "N/A") == "N/A"
