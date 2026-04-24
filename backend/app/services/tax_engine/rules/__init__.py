"""AY-versioned tax rule modules.

Each module is a frozen snapshot of the slab rates, section limits, and cess
rates for a single Assessment Year. Callers must select the module that
matches the AY of the filing they are computing — never import values across
AYs.
"""
