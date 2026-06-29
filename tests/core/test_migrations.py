from __future__ import annotations

from typing import Any

import pytest

from packages.core.migrations import CURRENT_SCHEMA_VERSION, MIGRATIONS, Migration, apply, register


def test_apply_noop_at_current() -> None:
    spec = {"schema_version": CURRENT_SCHEMA_VERSION, "id": "d"}
    assert apply(spec) == spec


def test_apply_chains_with_local_registry() -> None:
    def to_11(s: dict[str, Any]) -> dict[str, Any]:
        return {**s, "added": 1}

    def to_20(s: dict[str, Any]) -> dict[str, Any]:
        return {**s, "more": 2}

    registry: dict[tuple[str, str], Migration] = {
        ("1.0", "1.1"): to_11,
        ("1.1", "2.0"): to_20,
    }
    out = apply({"schema_version": "1.0", "id": "d"}, target="2.0", registry=registry)
    assert out["schema_version"] == "2.0"
    assert out["added"] == 1
    assert out["more"] == 2


def test_apply_no_path_raises() -> None:
    with pytest.raises(ValueError, match="no migration path"):
        apply({"schema_version": "1.0", "id": "d"}, target="9.9", registry={})


def test_apply_detects_cycle() -> None:
    registry: dict[tuple[str, str], Migration] = {("0.9", "0.9"): lambda s: s}
    with pytest.raises(ValueError, match="cycle"):
        apply({"schema_version": "0.9"}, registry=registry)


def test_register_adds_to_global_and_returns_fn() -> None:
    @register("mig-test-from", "mig-test-to")
    def _m(s: dict[str, Any]) -> dict[str, Any]:
        return s

    try:
        assert MIGRATIONS[("mig-test-from", "mig-test-to")] is _m
    finally:
        MIGRATIONS.pop(("mig-test-from", "mig-test-to"), None)
