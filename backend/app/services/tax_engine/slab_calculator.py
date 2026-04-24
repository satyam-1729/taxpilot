"""Progressive slab tax calculation.

Pure functions — no I/O, no LLM, no mutation. Given a taxable income and a
slab ladder, return the tax liability *before* surcharge, cess, and s.87A
rebate (those apply in separate stages of the engine).

The core primitive ``compute_slab_tax`` is AY-agnostic: it takes whatever
ladder the caller hands it. The convenience wrappers accept the rules
module for the AY being computed, so no AY value is ever hardcoded here.
"""

from __future__ import annotations

from decimal import Decimal
from types import ModuleType

from .types import Slab


def compute_slab_tax(taxable_income: int, slabs: tuple[Slab, ...]) -> Decimal:
    """Apply a progressive slab ladder to a taxable-income amount.

    Slabs are assumed to be ordered ascending, contiguous (each slab's
    ``lower`` equals the previous slab's ``upper``), with exactly one
    unbounded topmost slab (``upper is None``). The AY rule modules
    guarantee this shape — this function does not revalidate it.

    Args:
        taxable_income: Income to tax, in whole rupees. Negative or zero
            values yield zero tax.
        slabs: Slab ladder for the regime (and age group, for old regime).

    Returns:
        Tax liability before surcharge, cess, and 87A rebate, as a
        ``Decimal``. The caller rounds per s.288B at the end of the stack.
    """
    if taxable_income <= 0:
        return Decimal("0")

    tax = Decimal("0")
    for slab in slabs:
        if taxable_income <= slab.lower:
            break
        ceiling = slab.upper if slab.upper is not None else taxable_income
        income_in_slab = min(taxable_income, ceiling) - slab.lower
        tax += Decimal(income_in_slab) * slab.rate

    return tax


def compute_new_regime_tax(taxable_income: int, rules: ModuleType) -> Decimal:
    """Tax under s.115BAC (new regime) for the given AY rules module."""
    return compute_slab_tax(taxable_income, rules.NEW_REGIME_SLABS)


def compute_old_regime_tax(
    taxable_income: int, age: int, rules: ModuleType
) -> Decimal:
    """Tax under the old regime for the given AY rules module.

    The basic exemption limit depends on age as on the last day of the
    financial year: ₹2.5L (<60), ₹3L (60–79), ₹5L (80+).
    """
    slabs = _pick_old_regime_slabs(age, rules)
    return compute_slab_tax(taxable_income, slabs)


def _pick_old_regime_slabs(age: int, rules: ModuleType) -> tuple[Slab, ...]:
    if age >= rules.SUPER_SENIOR_CITIZEN_AGE:
        return rules.OLD_REGIME_SLABS_SUPER_SENIOR
    if age >= rules.SENIOR_CITIZEN_AGE:
        return rules.OLD_REGIME_SLABS_SENIOR
    return rules.OLD_REGIME_SLABS_UNDER_60
