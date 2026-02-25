"""Tests for deepworm.exceptions module."""

import pytest

from deepworm.exceptions import (
    APIKeyError,
    ConfigError,
    DeepWormError,
    ProviderError,
    RateLimitError,
)


class TestDeepWormError:
    def test_basic(self):
        err = DeepWormError("something broke")
        assert str(err) == "something broke"
        assert err.hint == ""

    def test_with_hint(self):
        err = DeepWormError("bad config", hint="check your settings")
        assert err.hint == "check your settings"
        assert "check your settings" in err.friendly()

    def test_friendly_no_hint(self):
        err = DeepWormError("oops")
        assert err.friendly() == "oops"


class TestAPIKeyError:
    def test_is_provider_error(self):
        err = APIKeyError("no key")
        assert isinstance(err, ProviderError)
        assert isinstance(err, DeepWormError)

    def test_hint(self):
        err = APIKeyError("missing", hint="set OPENAI_API_KEY")
        assert "OPENAI_API_KEY" in err.friendly()


class TestRateLimitError:
    def test_basic(self):
        err = RateLimitError(provider="openai")
        assert "openai" in str(err)
        assert "Rate limit" in str(err)

    def test_with_retry_after(self):
        err = RateLimitError(provider="openai", retry_after=30)
        assert err.retry_after == 30
        assert "30s" in err.hint


class TestInheritance:
    def test_hierarchy(self):
        assert issubclass(APIKeyError, ProviderError)
        assert issubclass(ProviderError, DeepWormError)
        assert issubclass(ConfigError, DeepWormError)

    def test_catch_base(self):
        with pytest.raises(DeepWormError):
            raise APIKeyError("test")
