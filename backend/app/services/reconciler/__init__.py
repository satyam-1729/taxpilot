"""Reconciler — cross-source mismatch detection.

The IT Dept's AIS is the source-of-truth for income/TDS reported against a
PAN. The reconciler compares Form 16, broker P&L, and (later) bank
statements against AIS and flags mismatches *before* the user files, so the
filing doesn't trigger a 143(1) notice months later.

Two simple rules govern the output:
- AIS > our docs  → user under-reported. ERROR.
- our docs > AIS  → AIS still being populated; INFO. Not a hard error.

This module is pure: takes already-decrypted parsed_json blobs, returns a
list of Mismatch records. The API layer handles fetching documents and
unwrapping the DEK.
"""

from app.services.reconciler.engine import Mismatch, reconcile

__all__ = ["Mismatch", "reconcile"]
