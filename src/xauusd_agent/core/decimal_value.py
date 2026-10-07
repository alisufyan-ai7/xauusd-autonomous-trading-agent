"""Lossless decimal parsing and canonical formatting.

Binary floating-point input is intentionally rejected at this boundary.  Market
and account values must arrive as text, integers, or already-exact Decimal
instances.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, Inexact, InvalidOperation, localcontext
from typing import Final

from .errors import ValidationError

ZERO: Final[Decimal] = Decimal("0")


def parse_decimal(value: str | int | Decimal) -> Decimal:
    """Return a finite Decimal without accepting implicit float conversion."""

    if isinstance(value, bool) or isinstance(value, float):
        raise ValidationError("decimal input must not be bool or binary float")
    try:
        result = value if isinstance(value, Decimal) else Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValidationError("invalid decimal input") from exc
    if not result.is_finite():
        raise ValidationError("decimal input must be finite")
    return ZERO if result.is_zero() else result


def canonical_decimal(value: str | int | Decimal) -> str:
    """Encode a Decimal as minimal, non-exponent, locale-independent text."""

    number = parse_decimal(value)
    if number.is_zero():
        return "0"
    with localcontext() as context:
        context.prec = max(len(number.as_tuple().digits), 1)
        rendered = format(number, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


@dataclass(frozen=True, slots=True)
class ExactDecimal:
    """A validated exact numeric value with deterministic text identity."""

    value: Decimal

    def __init__(self, value: str | int | Decimal) -> None:
        object.__setattr__(self, "value", parse_decimal(value))

    @property
    def canonical(self) -> str:
        return canonical_decimal(self.value)

    def quantized(self, quantum: str | int | Decimal) -> ExactDecimal:
        """Apply a scale only when doing so does not round the value."""

        step = parse_decimal(quantum)
        if step <= ZERO:
            raise ValidationError("quantum must be positive")
        try:
            with localcontext() as context:
                context.prec = max(
                    len(self.value.as_tuple().digits), len(step.as_tuple().digits), 1
                )
                context.traps[Inexact] = True
                return ExactDecimal(self.value.quantize(step, context=context))
        except (Inexact, InvalidOperation) as exc:
            raise ValidationError("quantization would lose precision") from exc

    def __str__(self) -> str:
        return self.canonical
