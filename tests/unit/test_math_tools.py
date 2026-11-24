import pytest
from backend.tools.math_tools import evaluate_math_expression as ev

pytestmark = pytest.mark.unit


def test_basic_arithmetic():
    r = ev("2*2")
    assert r["success"] and r["numeric_result"] == 4


def test_percentage_of():
    assert ev("15% of 200")["numeric_result"] == 30


def test_sqrt():
    assert ev("sqrt(144)")["numeric_result"] == 12


def test_natural_language_math():
    assert ev("what is 12 plus 30")["numeric_result"] == 42


def test_division_by_zero_is_reported_not_raised():
    r = ev("10/0")
    assert not r["success"] and "zero" in r["message"].lower()


def test_code_injection_is_rejected():
    r = ev("__import__('os').system('echo pwned')")
    assert not r["success"]
