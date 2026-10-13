from __future__ import annotations

import unittest
from datetime import UTC, datetime
from decimal import Decimal

from xauusd_agent.core import (
    ExactDecimal,
    TimeObservation,
    ValidationError,
    canonical_bytes,
    canonical_decimal,
    canonical_json,
    format_utc,
    parse_decimal,
    parse_utc,
    sha256_hex,
)


class DecimalTests(unittest.TestCase):
    def test_decimal_is_lossless_and_canonical(self) -> None:
        self.assertEqual(parse_decimal("100.2300"), Decimal("100.2300"))
        self.assertEqual(canonical_decimal("100.2300"), "100.23")
        self.assertEqual(canonical_decimal("-0.000"), "0")
        self.assertEqual(str(ExactDecimal("0.0100")), "0.01")

    def test_binary_and_non_finite_values_fail_closed(self) -> None:
        for value in (0.1, True, Decimal("NaN"), Decimal("Infinity")):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                parse_decimal(value)  # type: ignore[arg-type]

    def test_quantization_never_rounds_silently(self) -> None:
        self.assertEqual(ExactDecimal("1.230").quantized("0.01").value, Decimal("1.23"))
        with self.assertRaises(ValidationError):
            ExactDecimal("1.234").quantized("0.01")


class CanonicalIdentityTests(unittest.TestCase):
    def test_mapping_order_does_not_change_identity(self) -> None:
        left = {"price": Decimal("2300.100"), "symbol": "XAUUSD"}
        right = {"symbol": "XAUUSD", "price": Decimal("2300.1")}
        self.assertEqual(canonical_bytes(left), canonical_bytes(right))
        self.assertEqual(sha256_hex(left), sha256_hex(right))

    def test_types_and_boundaries_are_unambiguous(self) -> None:
        self.assertNotEqual(canonical_bytes("1"), canonical_bytes(1))
        self.assertNotEqual(canonical_bytes(["ab", "c"]), canonical_bytes(["a", "bc"]))
        with self.assertRaises(ValidationError):
            canonical_bytes(1.0)

    def test_canonical_json_tags_exact_types(self) -> None:
        rendered = canonical_json({"v": Decimal("1.20"), "at": datetime(2026, 10, 7, tzinfo=UTC)})
        self.assertEqual(
            rendered,
            '{"at":{"$utc":"2026-10-07T00:00:00.000000Z"},"v":{"$decimal":"1.2"}}',
        )


class ClockTests(unittest.TestCase):
    def test_utc_round_trip_is_fixed_width(self) -> None:
        value = datetime(2026, 10, 7, 1, 2, 3, 4, tzinfo=UTC)
        encoded = format_utc(value)
        self.assertEqual(encoded, "2026-10-07T01:02:03.000004Z")
        self.assertEqual(parse_utc(encoded), value)

    def test_naive_and_non_z_timestamp_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            format_utc(datetime(2026, 10, 7))
        with self.assertRaises(ValidationError):
            parse_utc("2026-10-07T00:00:00+00:00")

    def test_monotonic_counter_requires_non_negative_integer(self) -> None:
        with self.assertRaises(ValidationError):
            TimeObservation(datetime(2026, 10, 7, tzinfo=UTC), 1.5)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
