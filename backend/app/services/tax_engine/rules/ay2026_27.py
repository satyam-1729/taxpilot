"""Tax rule constants for Assessment Year 2026-27 (Financial Year 2025-26).

Source: Finance Act 2025 (Budget presented 1 Feb 2025), Income Tax Act 1961.

This module is the single source of truth for every slab, limit, and rate
used in AY 2026-27 computations. Nothing in this file depends on the rest
of the codebase; it is import-free (except stdlib) and side-effect-free, so
it can be swapped out for a different AY without touching engine logic.

All monetary amounts are in whole rupees (``int``). All rates are
``Decimal`` to avoid float rounding drift across millions of computations.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from ..types import Slab, SurchargeTier

# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

ASSESSMENT_YEAR = "2026-27"
FINANCIAL_YEAR = "2025-26"
FY_START = "2025-04-01"
FY_END = "2026-03-31"


# ---------------------------------------------------------------------------
# Slab rates — New Regime (Section 115BAC, default from AY 2024-25)
# ---------------------------------------------------------------------------
# Finance Act 2025 widened the new-regime slabs. Seven slabs in total.

NEW_REGIME_SLABS: tuple[Slab, ...] = (
    Slab(lower=0,        upper=400_000,   rate=Decimal("0.00")),
    Slab(lower=400_000,  upper=800_000,   rate=Decimal("0.05")),
    Slab(lower=800_000,  upper=1_200_000, rate=Decimal("0.10")),
    Slab(lower=1_200_000, upper=1_600_000, rate=Decimal("0.15")),
    Slab(lower=1_600_000, upper=2_000_000, rate=Decimal("0.20")),
    Slab(lower=2_000_000, upper=2_400_000, rate=Decimal("0.25")),
    Slab(lower=2_400_000, upper=None,     rate=Decimal("0.30")),
)


# ---------------------------------------------------------------------------
# Slab rates — Old Regime
# ---------------------------------------------------------------------------
# Four slabs, age-differentiated basic exemption limit.

OLD_REGIME_SLABS_UNDER_60: tuple[Slab, ...] = (
    Slab(lower=0,        upper=250_000,   rate=Decimal("0.00")),
    Slab(lower=250_000,  upper=500_000,   rate=Decimal("0.05")),
    Slab(lower=500_000,  upper=1_000_000, rate=Decimal("0.20")),
    Slab(lower=1_000_000, upper=None,     rate=Decimal("0.30")),
)

OLD_REGIME_SLABS_SENIOR: tuple[Slab, ...] = (  # age 60 to <80
    Slab(lower=0,        upper=300_000,   rate=Decimal("0.00")),
    Slab(lower=300_000,  upper=500_000,   rate=Decimal("0.05")),
    Slab(lower=500_000,  upper=1_000_000, rate=Decimal("0.20")),
    Slab(lower=1_000_000, upper=None,     rate=Decimal("0.30")),
)

OLD_REGIME_SLABS_SUPER_SENIOR: tuple[Slab, ...] = (  # age >= 80
    Slab(lower=0,        upper=500_000,   rate=Decimal("0.00")),
    Slab(lower=500_000,  upper=1_000_000, rate=Decimal("0.20")),
    Slab(lower=1_000_000, upper=None,     rate=Decimal("0.30")),
)


# ---------------------------------------------------------------------------
# Surcharge (applied on tax before cess, once taxable income crosses ₹50L)
# ---------------------------------------------------------------------------
# Old regime retains the full ladder up to 37%. New regime caps at 25%
# (Finance Act 2023 change, retained in AY 2026-27).

SURCHARGE_TIERS_OLD_REGIME: tuple[SurchargeTier, ...] = (
    SurchargeTier(lower=5_000_000,   upper=10_000_000,  rate=Decimal("0.10")),
    SurchargeTier(lower=10_000_000,  upper=20_000_000,  rate=Decimal("0.15")),
    SurchargeTier(lower=20_000_000,  upper=50_000_000,  rate=Decimal("0.25")),
    SurchargeTier(lower=50_000_000,  upper=None,        rate=Decimal("0.37")),
)

SURCHARGE_TIERS_NEW_REGIME: tuple[SurchargeTier, ...] = (
    SurchargeTier(lower=5_000_000,   upper=10_000_000,  rate=Decimal("0.10")),
    SurchargeTier(lower=10_000_000,  upper=20_000_000,  rate=Decimal("0.15")),
    SurchargeTier(lower=20_000_000,  upper=None,        rate=Decimal("0.25")),
)

# Surcharge cap for capital gains under s.111A / 112 / 112A and dividend
# income — never exceeds 15% irrespective of total income.
SURCHARGE_CAP_CAPITAL_GAINS_DIVIDEND = Decimal("0.15")


# ---------------------------------------------------------------------------
# Health & Education Cess (Section 2 of Finance Act)
# ---------------------------------------------------------------------------

CESS_RATE = Decimal("0.04")  # 4% on (tax + surcharge)


# ---------------------------------------------------------------------------
# Section 87A rebate
# ---------------------------------------------------------------------------
# Rebate kicks in only if taxable income is at-or-below the threshold. In
# the new regime, marginal relief applies just above the threshold so that
# tax liability never exceeds income over the threshold.

REBATE_87A_OLD_REGIME_THRESHOLD = 500_000
REBATE_87A_OLD_REGIME_MAX = 12_500

REBATE_87A_NEW_REGIME_THRESHOLD = 1_200_000
REBATE_87A_NEW_REGIME_MAX = 60_000
REBATE_87A_NEW_REGIME_MARGINAL_RELIEF = True  # tax ≤ income − threshold


# ---------------------------------------------------------------------------
# Standard deduction (Section 16(ia))
# ---------------------------------------------------------------------------
# Salaried and pensioners. Budget 2024 raised the new-regime figure to ₹75k.

STANDARD_DEDUCTION_OLD_REGIME = 50_000
STANDARD_DEDUCTION_NEW_REGIME = 75_000

# Family-pension deduction under s.57(iia): lower of ₹25,000 or 1/3rd of pension
# (new regime); old regime retains ₹15,000.
FAMILY_PENSION_DEDUCTION_OLD_REGIME = 15_000
FAMILY_PENSION_DEDUCTION_NEW_REGIME = 25_000


# ---------------------------------------------------------------------------
# Chapter VI-A deductions (old regime unless flagged otherwise)
# ---------------------------------------------------------------------------

# Section 80C — LIC, PPF, ELSS, home-loan principal, tuition, etc.
SECTION_80C_CAP = 150_000

# Section 80CCD(1B) — additional NPS contribution (over and above 80C)
SECTION_80CCD_1B_CAP = 50_000

# Section 80CCD(2) — employer NPS contribution. Available in BOTH regimes.
# Central/State govt employees: 14% of salary (basic + DA).
# Private employees: 10% under old regime, 14% under new regime (Finance
# Act 2024).
SECTION_80CCD_2_CAP_GOVT = Decimal("0.14")
SECTION_80CCD_2_CAP_PRIVATE_OLD = Decimal("0.10")
SECTION_80CCD_2_CAP_PRIVATE_NEW = Decimal("0.14")

# Section 80D — medical insurance premium.
# Limits are independent caps for (a) self+family and (b) parents.
SECTION_80D_SELF_UNDER_60 = 25_000
SECTION_80D_SELF_SENIOR = 50_000
SECTION_80D_PARENTS_UNDER_60 = 25_000
SECTION_80D_PARENTS_SENIOR = 50_000
# Preventive health-check-up is a sub-limit inside the above, not additional.
SECTION_80D_PREVENTIVE_HEALTH_CHECKUP_CAP = 5_000

# Section 80DD / 80DDB / 80U — disability & specified-disease (old regime).
SECTION_80DD_NORMAL_DISABILITY = 75_000
SECTION_80DD_SEVERE_DISABILITY = 125_000
SECTION_80DDB_UNDER_60 = 40_000
SECTION_80DDB_SENIOR = 100_000
SECTION_80U_NORMAL_DISABILITY = 75_000
SECTION_80U_SEVERE_DISABILITY = 125_000

# Section 80E — interest on education loan. No upper limit; claim allowed
# for 8 consecutive AYs starting from the AY in which repayment begins.
SECTION_80E_CAP: Optional[int] = None
SECTION_80E_MAX_YEARS = 8

# Section 80EE / 80EEA — first-time homebuyer interest (legacy; closed for
# new sanctions but retained for carry-forward of existing beneficiaries).
SECTION_80EE_CAP = 50_000
SECTION_80EEA_CAP = 150_000

# Section 80EEB — interest on electric-vehicle loan (sanctioned 1-Apr-2019
# to 31-Mar-2023; still deductible till the loan runs out).
SECTION_80EEB_CAP = 150_000

# Section 80G — donations. Limits are per-donee, capped at 10% of adjusted
# GTI; the engine computes the 10% cap from the profile.
SECTION_80G_QUALIFYING_LIMIT_RATIO = Decimal("0.10")

# Section 80GG — rent paid when HRA not received. Lower of:
#   - ₹5,000/month
#   - 25% of adjusted total income
#   - actual rent − 10% of adjusted total income
SECTION_80GG_MONTHLY_CAP = 5_000
SECTION_80GG_ATI_RATIO = Decimal("0.25")
SECTION_80GG_RENT_OFFSET_RATIO = Decimal("0.10")

# Section 80TTA (non-senior) / 80TTB (senior) — savings/FD interest.
SECTION_80TTA_CAP = 10_000
SECTION_80TTB_CAP = 50_000


# ---------------------------------------------------------------------------
# HRA — Section 10(13A) read with Rule 2A
# ---------------------------------------------------------------------------
# Exempt amount = minimum of:
#   1. Actual HRA received
#   2. % of (basic + DA forming part of retirement benefits + commission %
#      of turnover) — 50% metro, 40% non-metro
#   3. Rent paid − 10% of (basic + DA)
# IT Department still treats only the four classic metros as 50% cities.

HRA_METRO_RATIO = Decimal("0.50")
HRA_NON_METRO_RATIO = Decimal("0.40")
HRA_RENT_OFFSET_RATIO = Decimal("0.10")
HRA_METRO_CITIES: frozenset[str] = frozenset({
    "DELHI",
    "MUMBAI",
    "KOLKATA",
    "CHENNAI",
})


# ---------------------------------------------------------------------------
# House property — Section 24
# ---------------------------------------------------------------------------

# 30% standard deduction on Net Annual Value — s.24(a)
HOUSE_PROPERTY_STANDARD_DEDUCTION_RATIO = Decimal("0.30")

# Interest on home loan — s.24(b). Self-occupied cap ₹2L; let-out is
# unlimited but set-off against other heads is capped at ₹2L per year
# with balance carry-forward up to 8 years.
SECTION_24B_SELF_OCCUPIED_CAP = 200_000
HOUSE_PROPERTY_LOSS_SETOFF_CAP = 200_000
HOUSE_PROPERTY_LOSS_CARRYFORWARD_YEARS = 8


# ---------------------------------------------------------------------------
# Capital gains
# ---------------------------------------------------------------------------
# Budget 2024 overhaul (effective 23-Jul-2024, fully applicable for AY 2026-27):
#   - STCG on listed equity / equity MF / business-trust (s.111A): 20%
#   - LTCG on listed equity / equity MF / business-trust (s.112A): 12.5%
#     above ₹1.25L exemption
#   - LTCG on other assets (s.112): 12.5% WITHOUT indexation (resident
#     individuals / HUFs on land & buildings acquired before 23-Jul-2024
#     may opt for 20% WITH indexation, whichever is lower).
#   - STCG on other assets: slab rate.

STCG_111A_RATE = Decimal("0.20")           # listed equity, STT paid
LTCG_112A_RATE = Decimal("0.125")          # listed equity, STT paid
LTCG_112A_EXEMPTION = 125_000              # per-year exemption on s.112A gains
LTCG_112_RATE = Decimal("0.125")           # other assets, no indexation
LTCG_112_LEGACY_INDEXED_RATE = Decimal("0.20")  # resident land/bldg pre-23-Jul-2024 option

# Holding-period thresholds (Budget 2024 simplification):
#   - Listed securities → long-term if held > 12 months
#   - All other assets → long-term if held > 24 months
HOLDING_PERIOD_MONTHS_LISTED = 12
HOLDING_PERIOD_MONTHS_UNLISTED = 24

# LTCG grandfathering on listed equity — s.55(2)(ac). For shares/units
# acquired on or before 31-Jan-2018, cost of acquisition = higher of:
#   - actual cost, or
#   - lower of (FMV on 31-Jan-2018, sale consideration)
LTCG_GRANDFATHERING_DATE = "2018-01-31"

# Securities Transaction Tax threshold date for new capital-gains regime
CAPITAL_GAINS_REGIME_CHANGE_DATE = "2024-07-23"


# ---------------------------------------------------------------------------
# Advance tax — Section 211
# ---------------------------------------------------------------------------
# Four cumulative instalments. Exempt if total tax liability (after TDS) is
# below ₹10,000. Senior citizens with no business income are fully exempt.

ADVANCE_TAX_THRESHOLD = 10_000
ADVANCE_TAX_INSTALLMENTS: tuple[tuple[str, Decimal], ...] = (
    ("2025-06-15", Decimal("0.15")),
    ("2025-09-15", Decimal("0.45")),
    ("2025-12-15", Decimal("0.75")),
    ("2026-03-15", Decimal("1.00")),
)


# ---------------------------------------------------------------------------
# Interest for default — Sections 234A / 234B / 234C
# ---------------------------------------------------------------------------

INTEREST_234_RATE_PER_MONTH = Decimal("0.01")  # 1% simple, per month or part


# ---------------------------------------------------------------------------
# Age thresholds (applied on date = last day of FY)
# ---------------------------------------------------------------------------

SENIOR_CITIZEN_AGE = 60
SUPER_SENIOR_CITIZEN_AGE = 80


# ---------------------------------------------------------------------------
# Rounding — Section 288A/288B
# ---------------------------------------------------------------------------
# Total income rounded to nearest ₹10; tax payable rounded to nearest ₹10.

ROUND_INCOME_TO = 10
ROUND_TAX_TO = 10
