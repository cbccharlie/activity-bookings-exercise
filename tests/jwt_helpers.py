"""Build unsigned JWTs for tests."""

import base64
import json


def _segment(data: object) -> str:
    raw = json.dumps(data).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def make_jwt(exp: object) -> str:
    """Return `header.payload.signature` with the given `exp` claim (signature is fake)."""
    return f"{_segment({'alg': 'HS256', 'typ': 'JWT'})}.{_segment({'exp': exp})}.signature"
