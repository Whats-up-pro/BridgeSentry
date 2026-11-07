"""Unit tests for the holdout regime filter.

Target and alias ids must never appear in the exact/family/temporal pools;
temporal must also drop future-dated and undated records; no_rag is empty;
known is the full KB.
"""
from src.module2_rag.holdout import INCIDENTS, REGIMES, regime_pool

KB = [
    {"exploit_id": "old", "date": "2020-01-01", "vulnerability_class": "logic_bug"},
    {"exploit_id": "nomad_20220801", "date": "2022-08-01", "vulnerability_class": "fake_deposit"},
    {"exploit_id": "same_class_before", "date": "2021-06-01", "vulnerability_class": "fake_deposit"},
    {"exploit_id": "after", "date": "2023-01-01", "vulnerability_class": "key_compromise"},
    {"exploit_id": "undated", "vulnerability_class": "logic_bug"},
]


def _ids(pool):
    return {r["exploit_id"] for r in pool}


def test_known_is_full_and_drops_nothing():
    pool, dropped = regime_pool(KB, "known", "nomad")
    assert _ids(pool) == {"old", "nomad_20220801", "same_class_before", "after", "undated"}
    assert dropped == []


def test_no_rag_is_empty_and_drops_everything():
    pool, dropped = regime_pool(KB, "no_rag", "nomad")
    assert pool == []
    assert set(dropped) == {"old", "nomad_20220801", "same_class_before", "after", "undated"}


def test_exact_drops_only_target_alias():
    pool, dropped = regime_pool(KB, "exact", "nomad")
    assert "nomad_20220801" not in _ids(pool)
    assert dropped == ["nomad_20220801"]
    # everything else survives, including same-class and later records
    assert {"old", "same_class_before", "after", "undated"} <= _ids(pool)


def test_temporal_keeps_only_strictly_earlier_dated():
    pool, dropped = regime_pool(KB, "temporal", "nomad")  # cutoff 2022-08-01
    assert _ids(pool) == {"old", "same_class_before"}
    assert set(dropped) == {"nomad_20220801", "after", "undated"}


def test_family_drops_target_and_same_class():
    pool, dropped = regime_pool(KB, "family", "nomad")  # nomad class = fake_deposit
    assert _ids(pool) == {"old", "after", "undated"}
    assert set(dropped) == {"nomad_20220801", "same_class_before"}


def test_unknown_regime_raises():
    try:
        regime_pool(KB, "bogus", "nomad")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for unknown regime")


def test_unknown_fixture_raises_for_holdout_regimes():
    for regime in ("exact", "family", "temporal"):
        try:
            regime_pool(KB, regime, "no_such_fixture")
        except KeyError:
            pass
        else:
            raise AssertionError(f"expected KeyError for unknown fixture under {regime}")


def test_registry_entries_well_formed():
    for fixture, inc in INCIDENTS.items():
        assert inc["aliases"], fixture
        assert inc["date"] and len(inc["date"]) == 10, fixture
        assert inc["vulnerability_class"], fixture


def test_regimes_constant_matches_docs():
    assert set(REGIMES) == {"known", "no_rag", "exact", "family", "temporal"}
