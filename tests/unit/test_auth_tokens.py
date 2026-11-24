import pytest

from backend import auth

pytestmark = pytest.mark.unit


def test_token_roundtrip():
    assert auth.verify_token(auth.create_token(7)) == 7


def test_tampered_token_rejected():
    token = auth.create_token(7)
    payload, sig = token.split(".")
    assert auth.verify_token(payload + "." + sig[:-2] + "xx") is None


def test_expired_token_rejected():
    assert auth.verify_token(auth.create_token(7, ttl_hours=-1)) is None


def test_garbage_token_rejected():
    assert auth.verify_token("not-a-token") is None
