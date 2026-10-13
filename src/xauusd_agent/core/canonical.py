"""Canonical, length-prefixed identities for persisted evidence."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from .clock import format_utc
from .decimal_value import canonical_decimal
from .errors import ValidationError


def _frame(tag: bytes, payload: bytes) -> bytes:
    return tag + len(payload).to_bytes(8, "big", signed=False) + payload


def canonical_bytes(value: Any) -> bytes:
    """Encode supported values without delimiter or type ambiguity."""

    if value is None:
        return _frame(b"n", b"")
    if isinstance(value, bool):
        return _frame(b"b", b"1" if value else b"0")
    if isinstance(value, int):
        return _frame(b"i", str(value).encode("ascii"))
    if isinstance(value, float):
        raise ValidationError("binary floats are forbidden in canonical values")
    if isinstance(value, Decimal):
        return _frame(b"d", canonical_decimal(value).encode("ascii"))
    if isinstance(value, datetime):
        return _frame(b"t", format_utc(value).encode("ascii"))
    if isinstance(value, Enum):
        return _frame(b"e", canonical_bytes(value.value))
    if isinstance(value, str):
        return _frame(b"s", value.encode("utf-8"))
    if isinstance(value, bytes):
        return _frame(b"x", value)
    if isinstance(value, Mapping):
        encoded_items: list[tuple[bytes, bytes]] = []
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValidationError("canonical mapping keys must be strings")
            encoded_items.append((canonical_bytes(key), canonical_bytes(item)))
        encoded_items.sort(key=lambda pair: pair[0])
        parts = (_frame(b"k", key) + _frame(b"v", item) for key, item in encoded_items)
        return _frame(b"m", b"".join(parts))
    if isinstance(value, Sequence):
        return _frame(b"l", b"".join(_frame(b"v", canonical_bytes(item)) for item in value))
    raise ValidationError(f"unsupported canonical value type: {type(value).__name__}")


def sha256_hex(*values: Any) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(_frame(b"a", canonical_bytes(value)))
    return digest.hexdigest()


def canonical_json(value: Any) -> str:
    """Human-readable JSON that preserves exact decimal and timestamp types."""

    def convert(item: Any) -> Any:
        if item is None or isinstance(item, (bool, int, str)):
            return item
        if isinstance(item, float):
            raise ValidationError("binary floats are forbidden in canonical JSON")
        if isinstance(item, Decimal):
            return {"$decimal": canonical_decimal(item)}
        if isinstance(item, datetime):
            return {"$utc": format_utc(item)}
        if isinstance(item, Enum):
            return {"$enum": item.__class__.__name__, "value": convert(item.value)}
        if isinstance(item, bytes):
            return {"$bytes_hex": item.hex()}
        if isinstance(item, Mapping):
            if any(not isinstance(key, str) for key in item):
                raise ValidationError("canonical JSON mapping keys must be strings")
            return {key: convert(item[key]) for key in sorted(item)}
        if isinstance(item, Sequence):
            return [convert(part) for part in item]
        raise ValidationError(f"unsupported canonical JSON type: {type(item).__name__}")

    return json.dumps(convert(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
