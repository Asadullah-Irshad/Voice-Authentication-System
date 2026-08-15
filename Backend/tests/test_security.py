"""Unit tests for password hashing and JWT tokens."""

import pytest
from app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from fastapi import HTTPException


def test_password_hash_roundtrip():
    hashed = hash_password("s3cret-password")
    assert hashed != "s3cret-password"  # never stored in plaintext
    assert verify_password("s3cret-password", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_password_hash_is_salted():
    # Two hashes of the same password must differ (random salt).
    assert hash_password("same") != hash_password("same")


def test_token_roundtrip():
    token = create_access_token("user@example.com")
    assert decode_access_token(token) == "user@example.com"


def test_invalid_token_rejected():
    with pytest.raises(HTTPException) as exc:
        decode_access_token("not-a-real-token")
    assert exc.value.status_code == 401


def test_verify_bad_hash_returns_false():
    assert verify_password("anything", "not-a-bcrypt-hash") is False
