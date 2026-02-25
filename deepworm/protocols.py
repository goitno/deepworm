"""Protocol definitions and type contracts for deepworm.

Provides Protocol classes (structural typing), type guards, result types,
and common interface contracts for the research pipeline.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterator,
    List,
    Optional,
    Protocol,
    Tuple,
    TypeVar,
    Union,
    runtime_checkable,
)


T = TypeVar("T")
E = TypeVar("E")


# ---------------------------------------------------------------------------
# Result type (Ok | Err)
# ---------------------------------------------------------------------------


class ResultStatus(Enum):
    """Status of a Result."""

    OK = "ok"
    ERR = "err"


@dataclass
class Ok(Generic[T]):
    """Successful result."""

    value: T
    status: ResultStatus = field(default=ResultStatus.OK, init=False)

    @property
    def is_ok(self) -> bool:
        return True

    @property
    def is_err(self) -> bool:
        return False

    def unwrap(self) -> T:
        return self.value

    def unwrap_or(self, default: T) -> T:
        return self.value

    def map(self, fn: Callable[[T], Any]) -> "Ok":
        return Ok(fn(self.value))


@dataclass
class Err(Generic[E]):
    """Error result."""

    error: E
    status: ResultStatus = field(default=ResultStatus.ERR, init=False)

    @property
    def is_ok(self) -> bool:
        return False

    @property
    def is_err(self) -> bool:
        return True

    def unwrap(self) -> Any:
        raise ValueError(f"Called unwrap on Err: {self.error}")

    def unwrap_or(self, default: Any) -> Any:
        return default

    def map(self, fn: Callable) -> "Err":
        return self  # Err passes through


# Result is a union of Ok[T] and Err[E]
Result = Union[Ok[T], Err[E]]


def ok(value: T) -> Ok[T]:
    """Create an Ok result."""
    return Ok(value)


def err(error: E) -> Err[E]:
    """Create an Err result."""
    return Err(error)


def try_result(fn: Callable[..., T], *args: Any, **kwargs: Any) -> Result:
    """Execute a function and wrap the result in Ok/Err."""
    try:
        return Ok(fn(*args, **kwargs))
    except Exception as e:
        return Err(str(e))


# ---------------------------------------------------------------------------
# Option type (Some | Nothing)
# ---------------------------------------------------------------------------


@dataclass
class Some(Generic[T]):
    """A value that exists."""

    value: T

    @property
    def is_some(self) -> bool:
        return True

    @property
    def is_nothing(self) -> bool:
        return False

    def unwrap(self) -> T:
        return self.value

    def unwrap_or(self, default: T) -> T:
        return self.value

    def map(self, fn: Callable[[T], Any]) -> "Some":
        return Some(fn(self.value))


@dataclass
class Nothing:
    """Absence of a value."""

    @property
    def is_some(self) -> bool:
        return False

    @property
    def is_nothing(self) -> bool:
        return True

    def unwrap(self) -> Any:
        raise ValueError("Called unwrap on Nothing")

    def unwrap_or(self, default: Any) -> Any:
        return default

    def map(self, fn: Callable) -> "Nothing":
        return self


Option = Union[Some[T], Nothing]

NOTHING = Nothing()


def some(value: T) -> Some[T]:
    """Create a Some value."""
    return Some(value)


def nothing() -> Nothing:
    """Create a Nothing value."""
    return NOTHING


# ---------------------------------------------------------------------------
# Protocol interfaces (structural typing)
# ---------------------------------------------------------------------------


@runtime_checkable
class Serializable(Protocol):
    """Protocol for objects that can be serialized to dict."""

    def to_dict(self) -> Dict[str, Any]: ...


@runtime_checkable
class Renderable(Protocol):
    """Protocol for objects that can render to string."""

    def render(self) -> str: ...


@runtime_checkable
class Validatable(Protocol):
    """Protocol for objects that can validate themselves."""

    def validate(self) -> bool: ...


@runtime_checkable
class Disposable(Protocol):
    """Protocol for objects with cleanup/dispose."""

    def dispose(self) -> None: ...


@runtime_checkable
class Configurable(Protocol):
    """Protocol for objects that accept configuration."""

    def configure(self, config: Dict[str, Any]) -> None: ...


@runtime_checkable
class Identifiable(Protocol):
    """Protocol for objects with a unique identifier."""

    @property
    def id(self) -> str: ...


# ---------------------------------------------------------------------------
# Type guards
# ---------------------------------------------------------------------------


def is_serializable(obj: Any) -> bool:
    """Check if an object implements Serializable protocol."""
    return isinstance(obj, Serializable)


def is_renderable(obj: Any) -> bool:
    """Check if an object implements Renderable protocol."""
    return isinstance(obj, Renderable)


def is_validatable(obj: Any) -> bool:
    """Check if an object implements Validatable protocol."""
    return isinstance(obj, Validatable)


def is_dict_like(obj: Any) -> bool:
    """Check if an object is dict-like."""
    return hasattr(obj, "__getitem__") and hasattr(obj, "keys")


def is_list_like(obj: Any) -> bool:
    """Check if an object is list-like (but not str or bytes)."""
    if isinstance(obj, (str, bytes)):
        return False
    return hasattr(obj, "__iter__") and hasattr(obj, "__len__")


def is_callable(obj: Any) -> bool:
    """Check if an object is callable."""
    return callable(obj)


def is_numeric(value: Any) -> bool:
    """Check if a value is numeric."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_non_empty_string(value: Any) -> bool:
    """Check if a value is a non-empty string."""
    return isinstance(value, str) and len(value.strip()) > 0


# ---------------------------------------------------------------------------
# Lazy evaluation
# ---------------------------------------------------------------------------


class Lazy(Generic[T]):
    """Lazy-evaluated value. Computed on first access."""

    def __init__(self, factory: Callable[[], T]) -> None:
        self._factory = factory
        self._value: Optional[T] = None
        self._computed = False

    @property
    def value(self) -> T:
        if not self._computed:
            self._value = self._factory()
            self._computed = True
        return self._value  # type: ignore

    @property
    def is_computed(self) -> bool:
        return self._computed

    def reset(self) -> None:
        self._computed = False
        self._value = None


# ---------------------------------------------------------------------------
# Either type
# ---------------------------------------------------------------------------


@dataclass
class Left(Generic[T]):
    """Left side of Either."""

    value: T

    @property
    def is_left(self) -> bool:
        return True

    @property
    def is_right(self) -> bool:
        return False


@dataclass
class Right(Generic[T]):
    """Right side of Either."""

    value: T

    @property
    def is_left(self) -> bool:
        return False

    @property
    def is_right(self) -> bool:
        return True


Either = Union[Left[T], Right[E]]


def left(value: T) -> Left[T]:
    """Create a Left value."""
    return Left(value)


def right(value: T) -> Right[T]:
    """Create a Right value."""
    return Right(value)


# ---------------------------------------------------------------------------
# Pair / Triple
# ---------------------------------------------------------------------------


@dataclass
class Pair(Generic[T, E]):
    """A pair of values."""

    first: T
    second: E

    def to_tuple(self) -> Tuple:
        return (self.first, self.second)

    def swap(self) -> "Pair[E, T]":
        return Pair(self.second, self.first)


def pair(first: T, second: E) -> Pair[T, E]:
    """Create a Pair."""
    return Pair(first, second)


# ---------------------------------------------------------------------------
# Type conversion helpers
# ---------------------------------------------------------------------------


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert to int."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert to float."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_bool(value: Any) -> bool:
    """Safely convert to bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "on")
    return bool(value)


def safe_str(value: Any, default: str = "") -> str:
    """Safely convert to string."""
    if value is None:
        return default
    return str(value)
