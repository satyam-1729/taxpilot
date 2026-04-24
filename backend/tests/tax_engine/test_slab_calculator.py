"""Slab-calculator tests for AY 2026-27.

Each parametrised case is a hand-verified (income, expected_tax) pair
against the slab ladders in ``rules/ay2026_27.py``. Values cover every
slab boundary, plus representative mid-slab and high-income amounts.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.tax_engine.rules import ay2026_27 as rules
from app.services.tax_engine.slab_calculator import (
    compute_new_regime_tax,
    compute_old_regime_tax,
    compute_slab_tax,
)


# ---------------------------------------------------------------------------
# New regime — s.115BAC
# Slabs: 0 / 4L / 8L / 12L / 16L / 20L / 24L+ @ 0/5/10/15/20/25/30%
# ---------------------------------------------------------------------------

NEW_REGIME_CASES = [
    # (label, income, expected_tax)
    ("zero",               0,          0),
    ("below_exemption",    300_000,    0),
    ("edge_4L",            400_000,    0),
    ("mid_5pct",           500_000,    5_000),      # 1L @ 5%
    ("edge_8L",            800_000,    20_000),     # 4L @ 5%
    ("edge_12L",           1_200_000,  60_000),     # + 4L @ 10%
    ("mid_15pct",          1_500_000,  105_000),    # + 3L @ 15%
    ("edge_16L",           1_600_000,  120_000),    # + 4L @ 15%
    ("edge_20L",           2_000_000,  200_000),    # + 4L @ 20%
    ("edge_24L",           2_400_000,  300_000),    # + 4L @ 25%
    ("mid_30pct",          2_500_000,  330_000),    # + 1L @ 30%
    ("fifty_lakh",         5_000_000,  1_080_000),  # 300k + 26L @ 30%
    ("one_crore",         10_000_000,  2_580_000),  # 300k + 76L @ 30%
    ("five_crore",        50_000_000, 14_580_000),  # 300k + 476L @ 30%
]


@pytest.mark.parametrize(
    "income,expected",
    [(inc, exp) for _, inc, exp in NEW_REGIME_CASES],
    ids=[label for label, _, _ in NEW_REGIME_CASES],
)
def test_new_regime_tax(income: int, expected: int) -> None:
    assert compute_new_regime_tax(income, rules) == Decimal(expected)


# ---------------------------------------------------------------------------
# Old regime, under 60
# Slabs: 0 / 2.5L / 5L / 10L+ @ 0/5/20/30%
# ---------------------------------------------------------------------------

OLD_UNDER_60_CASES = [
    ("zero",               0,           0),
    ("negative",           -100_000,    0),
    ("below_exemption",    200_000,     0),
    ("edge_2_5L",          250_000,     0),
    ("mid_5pct",           400_000,     7_500),      # 1.5L @ 5%
    ("edge_5L",            500_000,     12_500),     # 2.5L @ 5%
    ("mid_20pct",          750_000,     62_500),     # + 2.5L @ 20%
    ("edge_10L",           1_000_000,   112_500),    # + 5L @ 20%
    ("mid_30pct",          1_500_000,   262_500),    # + 5L @ 30%
    ("one_crore",          10_000_000,  2_812_500),  # 262500 + 85L @ 30%
]


@pytest.mark.parametrize(
    "income,expected",
    [(inc, exp) for _, inc, exp in OLD_UNDER_60_CASES],
    ids=[label for label, _, _ in OLD_UNDER_60_CASES],
)
def test_old_regime_under_60(income: int, expected: int) -> None:
    assert compute_old_regime_tax(income, age=40, rules=rules) == Decimal(expected)


# ---------------------------------------------------------------------------
# Old regime, senior (60 ≤ age < 80) — basic exemption ₹3L
# ---------------------------------------------------------------------------

OLD_SENIOR_CASES = [
    ("edge_3L",            300_000,     0),
    ("mid_5pct",           400_000,     5_000),      # 1L @ 5%
    ("edge_5L",            500_000,     10_000),     # 2L @ 5%
    ("edge_10L",           1_000_000,   110_000),    # + 5L @ 20%
    ("mid_30pct",          1_500_000,   260_000),    # + 5L @ 30%
]


@pytest.mark.parametrize(
    "income,expected",
    [(inc, exp) for _, inc, exp in OLD_SENIOR_CASES],
    ids=[label for label, _, _ in OLD_SENIOR_CASES],
)
def test_old_regime_senior(income: int, expected: int) -> None:
    assert compute_old_regime_tax(income, age=65, rules=rules) == Decimal(expected)


# ---------------------------------------------------------------------------
# Old regime, super senior (age ≥ 80) — basic exemption ₹5L, no 5% slab
# ---------------------------------------------------------------------------

OLD_SUPER_SENIOR_CASES = [
    ("edge_5L",            500_000,     0),
    ("mid_20pct",          750_000,     50_000),     # 2.5L @ 20%
    ("edge_10L",           1_000_000,   100_000),    # 5L @ 20%
    ("mid_30pct",          1_500_000,   250_000),    # + 5L @ 30%
]


@pytest.mark.parametrize(
    "income,expected",
    [(inc, exp) for _, inc, exp in OLD_SUPER_SENIOR_CASES],
    ids=[label for label, _, _ in OLD_SUPER_SENIOR_CASES],
)
def test_old_regime_super_senior(income: int, expected: int) -> None:
    assert compute_old_regime_tax(income, age=82, rules=rules) == Decimal(expected)


# ---------------------------------------------------------------------------
# Age ladder boundaries
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "age,expected",
    [
        (59,  12_500),  # under-60 ladder: 2.5L @ 5%
        (60,  10_000),  # turns senior: 2L @ 5%
        (79,  10_000),  # still senior
        (80,  0),       # super-senior: ₹5L exempt
    ],
)
def test_old_regime_age_boundary(age: int, expected: int) -> None:
    assert compute_old_regime_tax(500_000, age=age, rules=rules) == Decimal(expected)


# ---------------------------------------------------------------------------
# Generic primitive
# ---------------------------------------------------------------------------


def test_primitive_accepts_any_ladder() -> None:
    assert compute_slab_tax(1_500_000, rules.NEW_REGIME_SLABS) == Decimal(105_000)
    assert compute_slab_tax(1_500_000, rules.OLD_REGIME_SLABS_UNDER_60) == Decimal(
        262_500
    )


def test_primitive_single_slab_ladder() -> None:
    """A trivial ladder (entire income at a flat rate) works end-to-end."""
    from app.services.tax_engine.types import Slab

    flat_10pct = (Slab(lower=0, upper=None, rate=Decimal("0.10")),)
    assert compute_slab_tax(1_000_000, flat_10pct) == Decimal(100_000)


# ---------------------------------------------------------------------------
# Invariants
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ladder_name",
    [
        "NEW_REGIME_SLABS",
        "OLD_REGIME_SLABS_UNDER_60",
        "OLD_REGIME_SLABS_SENIOR",
        "OLD_REGIME_SLABS_SUPER_SENIOR",
    ],
)
def test_tax_is_monotonic_in_income(ladder_name: str) -> None:
    """Progressive ladders must never decrease tax as income rises."""
    slabs = getattr(rules, ladder_name)
    previous = Decimal("-1")
    for income in range(0, 30_000_000, 50_000):
        tax = compute_slab_tax(income, slabs)
        assert tax >= previous, f"tax went down at income {income} on {ladder_name}"
        previous = tax


@pytest.mark.parametrize(
    "ladder_name",
    [
        "NEW_REGIME_SLABS",
        "OLD_REGIME_SLABS_UNDER_60",
        "OLD_REGIME_SLABS_SENIOR",
        "OLD_REGIME_SLABS_SUPER_SENIOR",
    ],
)
def test_marginal_rate_never_exceeds_top_slab(ladder_name: str) -> None:
    """Adding ₹1 to income must not add more than the topmost slab rate in tax."""
    slabs = getattr(rules, ladder_name)
    top_rate = slabs[-1].rate
    for income in (100_000, 500_000, 1_000_000, 5_000_000, 20_000_000):
        delta = compute_slab_tax(income + 10_000, slabs) - compute_slab_tax(
            income, slabs
        )
        assert delta <= Decimal(10_000) * top_rate + Decimal("0.01")


def test_returns_decimal_not_float() -> None:
    """Keep the arithmetic in Decimal — float drift is not acceptable for tax."""
    result = compute_new_regime_tax(1_500_000, rules)
    assert isinstance(result, Decimal)
