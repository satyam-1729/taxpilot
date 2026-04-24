"""AY-agnostic structural types shared across the tax engine.

The *values* of slabs and surcharge tiers are AY-versioned (see
``rules/ay{year}.py``). The *shapes* live here so every AY module and every
calculator share a single definition.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class Slab:
    """A single income tax slab. ``upper`` is None for the topmost (unbounded) slab."""

    lower: int
    upper: Optional[int]
    rate: Decimal


@dataclass(frozen=True)
class SurchargeTier:
    """Surcharge tier. ``upper`` is None for the topmost (unbounded) tier."""

    lower: int
    upper: Optional[int]
    rate: Decimal
