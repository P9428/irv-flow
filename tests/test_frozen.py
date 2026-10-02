"""The prereg is pinned by sha256 and the code's frozen constants must equal what it declares."""
import hashlib
import os
import sys
from fractions import Fraction

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [os.path.join(ROOT, "src")]
import rule as R              # noqa: E402

PREREG = os.path.join(ROOT, "prereg", "IF-01-PREREGISTRATION.md")
PIN = os.path.join(ROOT, "prereg", "FROZEN_SHA")


def test_prereg_sha_pinned():
    sha = hashlib.sha256(open(PREREG, "rb").read()).hexdigest()
    assert sha == open(PIN, encoding="utf-8").read().strip(), "prereg changed after freeze: write an AMENDMENT, never edit"


def test_core_matches_mimicry_freeze():
    assert (R.D, R.MULTIPLE, R.LOOKBACK_S, R.Z_LAMPORTS, R.FEE) == (Fraction(1, 2), Fraction(2), 900, 1_000_000_000, Fraction(125, 10000))
    assert R.K == Fraction(79, 81) and R.K_TOL == Fraction(1, 100)


def test_flow_thresholds_match_prereg():
    assert R.FLOW == {
        "AGE_MIN_S": 30, "AGE_MAX_S": 300, "RUN_MIN": Fraction(2), "RUN_MAX": Fraction(3),
        "BUYERS_MIN": 20, "BUYERS_MAX": 80, "BIG_BUY_SHARE_MAX": Fraction(1, 5),
        "BIG_SELL_SHARE_MAX": Fraction(2, 5), "PACE_MAX": Fraction(1), "DIP_SELLERS_MIN": 3,
        "DIP_TOP_SELLER_SHARE_MAX": Fraction(1, 2)}
    text = open(PREREG, encoding="utf-8").read()
    for k, v in R.FLOW.items():
        assert f"`{k}` = {v}" in text, f"{k} not declared as {v} in the prereg"


def test_amendment_1_declares_the_size_the_code_uses():
    text = open(PREREG, encoding="utf-8").read()
    assert "## AMENDMENT 1" in text and f"`Z_LAMPORTS` = {R.Z_LAMPORTS}" in text


def test_frozen_at_is_the_last_capture_on_disk_at_freeze():
    assert open(os.path.join(ROOT, "prereg", "FROZEN_AT"), encoding="utf-8").read().strip() == "mi-20260929T1040Z"
