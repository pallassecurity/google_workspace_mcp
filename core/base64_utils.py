"""
Shared base64 helpers for binary payload handling.
"""

import base64
import binascii


def _normalize_base64_input(content_base64: str) -> str:
    """
    Normalize a base64 payload to standard alphabet and remove whitespace.
    """
    normalized_content = "".join(content_base64.split())
    normalized_content = normalized_content.replace("-", "+").replace("_", "/")
    return normalized_content


def estimate_base64_decoded_size_upper_bound(content_base64: str) -> int:
    """
    Estimate an upper bound for decoded byte size without decoding.
    """
    normalized_content = _normalize_base64_input(content_base64)
    return ((len(normalized_content) + 3) // 4) * 3


def decode_base64_payload(content_base64: str) -> bytes:
    """
    Decode a base64 payload (supports standard + URL-safe variants).
    """
    normalized_content = _normalize_base64_input(content_base64)
    if not normalized_content:
        raise ValueError("Base64 content cannot be empty.")

    padded_content = normalized_content + "=" * (-len(normalized_content) % 4)
    try:
        return base64.b64decode(padded_content, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Invalid base64 payload.") from exc
