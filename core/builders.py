"""
Generic Builder Pattern — fluent test data construction for any project.

Usage:
    # Quick dict builder
    user = Builder("User").set("name", "Azeez").set("email", "a@x.com").set("role", "admin").build()
    # => {"name": "Azeez", "email": "a@x.com", "role": "admin"}

    # Custom typed builder
    class UserBuilder(TypedBuilder):
        def __init__(self):
            super().__init__()
            self._data = {"role": "viewer", "active": True}  # defaults

        def with_name(self, name: str):
            return self.set("name", name)

        def with_email(self, email: str):
            return self.set("email", email)

        def as_admin(self):
            return self.set("role", "admin")

    user = UserBuilder().with_name("Grace").with_email("g@x.com").as_admin().build()
"""

from copy import deepcopy
from typing import Any, Dict


class Builder:
    """
    Generic fluent builder for constructing test data dicts.
    Use for ad-hoc data construction without creating a custom class.
    """

    def __init__(self, label: str = "Object"):
        self._label = label
        self._data: Dict[str, Any] = {}

    def set(self, key: str, value: Any) -> "Builder":
        """Set a key-value pair. Returns self for chaining."""
        self._data[key] = value
        return self

    def merge(self, other: Dict[str, Any]) -> "Builder":
        """Merge a dict into the builder data."""
        self._data.update(other)
        return self

    def build(self) -> Dict[str, Any]:
        """Return a deep copy of the built object."""
        return deepcopy(self._data)

    def __repr__(self):
        return f"Builder({self._label}, keys={list(self._data.keys())})"


class TypedBuilder:
    """
    Base class for domain-specific builders.
    Subclass this and add with_xxx() methods that call self.set().

    Rules (from enterprise patterns):
    - Builders NEVER call APIs
    - Builders NEVER touch the UI
    - Builders NEVER run tests
    - Builders ONLY construct data objects in memory
    """

    def __init__(self):
        self._data: Dict[str, Any] = {}

    def set(self, key: str, value: Any) -> "TypedBuilder":
        self._data[key] = value
        return self

    def build(self) -> Dict[str, Any]:
        return deepcopy(self._data)

    def build_many(self, count: int, mutator=None) -> list:
        """Build N copies, optionally mutating each with mutator(index, data)."""
        results = []
        for i in range(count):
            obj = self.build()
            if mutator:
                mutator(i, obj)
            results.append(obj)
        return results
