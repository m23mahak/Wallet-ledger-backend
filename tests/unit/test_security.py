from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.configuration.config import get_settings
from app.core.exceptions import Unauthorized
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_is_not_plaintext_and_verifies():
    h = hash_password("S3cret-pass")
    assert h != "S3cret-pass"
    assert verify_password("S3cret-pass", h)
    assert not verify_password("wrong", h)


def test_same_password_hashes_differently():
    assert hash_password("same-pass-1") != hash_password("same-pass-1")


def test_jwt_roundtrip():
    payload = decode_access_token(create_access_token(42, "USER"))
    assert payload["sub"] == "42"
    assert payload["role"] == "USER"


def test_expired_token_rejected():
    token = create_access_token(1, "USER", expires_minutes=-1)
    with pytest.raises(Unauthorized):
        decode_access_token(token)


def test_tampered_token_rejected():
    token = create_access_token(1, "USER")
    with pytest.raises(Unauthorized):
        decode_access_token(token[:-2] + "xx")


def test_wrong_secret_rejected():
    s = get_settings()
    forged = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        "other-secret-other-secret-other-secret", algorithm=s.jwt_algorithm,
    )
    with pytest.raises(Unauthorized):
        decode_access_token(forged)


def test_token_without_exp_rejected():
    s = get_settings()
    token = jwt.encode({"sub": "1"}, s.jwt_secret, algorithm=s.jwt_algorithm)
    with pytest.raises(Unauthorized):
        decode_access_token(token)
