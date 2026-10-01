"""
Tests for core modules — base_api_client, builders, config.
Run: python -m pytest tests/ -v
"""

import pytest
from core.base_api_client import BaseApiClient, ApiResponse
from core.builders import Builder, TypedBuilder
from config.env import Environment


# ══════════════════════════════════════════════════════════════════════
# BaseApiClient Tests
# ══════════════════════════════════════════════════════════════════════

class TestApiResponse:
    def test_ok_status(self):
        r = ApiResponse(status=200)
        assert r.ok is True

    def test_not_ok_status(self):
        r = ApiResponse(status=404)
        assert r.ok is False

    def test_error_status(self):
        r = ApiResponse(status=500, error="Internal Server Error")
        assert r.ok is False
        assert r.error is not None

    def test_repr(self):
        r = ApiResponse(status=200, url="https://example.com/api")
        assert "200" in repr(r)
        assert "True" in repr(r)


class TestBaseApiClient:
    def test_health_public_api(self):
        """Smoke test against a known public API."""
        client = BaseApiClient("https://httpbin.org", timeout=10)
        resp = client.get("/get")
        assert resp.ok
        assert resp.status == 200
        assert resp.json is not None
        assert resp.elapsed_ms > 0

    def test_post_request(self):
        client = BaseApiClient("https://httpbin.org", timeout=10)
        resp = client.post("/post", json_body={"key": "value"})
        assert resp.ok
        assert resp.json["json"]["key"] == "value"

    def test_params_encoding(self):
        client = BaseApiClient("https://httpbin.org", timeout=10)
        resp = client.get("/get", params={"q": "hello world", "limit": 5})
        assert resp.ok
        assert resp.json["args"]["q"] == "hello world"
        assert resp.json["args"]["limit"] == "5"

    def test_404_handling(self):
        client = BaseApiClient("https://httpbin.org", timeout=10)
        resp = client.get("/status/404")
        assert not resp.ok
        assert resp.status == 404

    def test_custom_headers(self):
        client = BaseApiClient("https://httpbin.org",
                               headers={"X-Custom": "test-value"}, timeout=10)
        resp = client.get("/headers")
        assert resp.ok
        assert resp.json["headers"]["X-Custom"] == "test-value"


# ══════════════════════════════════════════════════════════════════════
# Builder Tests
# ══════════════════════════════════════════════════════════════════════

class TestBuilder:
    def test_basic_build(self):
        obj = Builder("User").set("name", "Azeez").set("role", "admin").build()
        assert obj == {"name": "Azeez", "role": "admin"}

    def test_chaining(self):
        b = Builder("Item")
        result = b.set("a", 1).set("b", 2).set("c", 3).build()
        assert result == {"a": 1, "b": 2, "c": 3}

    def test_merge(self):
        obj = Builder("Test").set("x", 1).merge({"y": 2, "z": 3}).build()
        assert obj == {"x": 1, "y": 2, "z": 3}

    def test_deep_copy(self):
        """Built objects should be independent copies."""
        b = Builder("Mutable").set("items", [1, 2, 3])
        a = b.build()
        c = b.build()
        a["items"].append(4)
        assert c["items"] == [1, 2, 3]  # not affected


class TestTypedBuilder:
    def test_subclass_builder(self):
        class BrandBuilder(TypedBuilder):
            def with_name(self, name):
                return self.set("name", name)
            def with_category(self, cat):
                return self.set("category", cat)
            def with_branches(self, n):
                return self.set("branches", n)

        brand = BrandBuilder().with_name("KFC").with_category("Food").with_branches(3).build()
        assert brand == {"name": "KFC", "category": "Food", "branches": 3}

    def test_build_many(self):
        class ItemBuilder(TypedBuilder):
            def with_type(self, t):
                return self.set("type", t)

        items = ItemBuilder().with_type("widget").build_many(
            3, mutator=lambda i, d: d.update({"id": i + 1})
        )
        assert len(items) == 3
        assert items[0] == {"type": "widget", "id": 1}
        assert items[2] == {"type": "widget", "id": 3}


# ══════════════════════════════════════════════════════════════════════
# Config Tests
# ══════════════════════════════════════════════════════════════════════

class TestEnvironment:
    def test_defaults(self):
        e = Environment()
        assert e.default_timeout_ms == 30000
        assert e.max_workers == 10
        assert e.verbose is False

    def test_frozen(self):
        e = Environment()
        with pytest.raises(Exception):
            e.base_url = "changed"
