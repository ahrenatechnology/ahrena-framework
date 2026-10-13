"""Turn tokens and hours into money, from a price table that is data.

`prices.json`, beside this file, holds one entry per model: the price per million tokens of
each kind, the page it was read from and the day it was read. A model with no entry is never
priced by analogy: its tokens are left out of the cost and its name is returned, so a report
says "no price for model X".

The exchange rate and the hourly rate are configuration with no default. A figure that needs
one that is not configured is None, and is shown as "not configured", never as zero.

Standard library only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from usage import KINDS

MILLION = Decimal(1_000_000)
PRICES = Path(__file__).resolve().parent / "prices.json"


@dataclass
class PriceTable:
    models: dict[str, dict[str, str]] = field(default_factory=dict)
    aliases: dict[str, str] = field(default_factory=dict)
    tiers: dict[str, dict] = field(default_factory=dict)

    def entry(self, model: str) -> dict[str, str] | None:
        return self.models.get(self.aliases.get(model, model))


def load_prices(path: Path = PRICES) -> PriceTable:
    data = json.loads(path.read_text(encoding="utf-8"))
    return PriceTable(data.get("models", {}), data.get("aliases", {}), data.get("prompt_tiers", {}))


@dataclass
class TokenCost:
    """The cost of a set of tokens, and the models that could not be priced."""

    usd: Decimal = Decimal(0)
    unpriced: dict[str, int] = field(default_factory=dict)

    def add(self, other: "TokenCost") -> None:
        self.usd += other.usd
        for model, count in other.unpriced.items():
            self.unpriced[model] = self.unpriced.get(model, 0) + count


def token_cost(tokens: dict[str, dict[str, int]], table: PriceTable) -> TokenCost:
    """Price tokens by model and kind; collect the token count of every unpriced model."""
    cost = TokenCost()
    for model, counts in tokens.items():
        entry = table.entry(model)
        if entry is None:
            cost.unpriced[model] = cost.unpriced.get(model, 0) + sum(int(counts.get(kind, 0)) for kind in KINDS)
            continue
        for kind in KINDS:
            cost.usd += Decimal(int(counts.get(kind, 0))) * Decimal(entry[kind]) / MILLION
    return cost


def to_brl(usd: Decimal | None, brl_per_usd: float | None) -> Decimal | None:
    if usd is None or brl_per_usd is None:
        return None
    return usd * Decimal(str(brl_per_usd))


@dataclass
class Rates:
    """The two configured rates. Either may be None."""

    brl_per_usd: float | None = None
    hourly_rate: float | None = None
    hourly_rate_currency: str | None = None

    def hourly(self, currency: str) -> Decimal | None:
        """The hourly rate in a currency, or None when it cannot be expressed in it."""
        if self.hourly_rate is None or self.hourly_rate_currency is None:
            return None
        rate = Decimal(str(self.hourly_rate))
        if self.hourly_rate_currency == currency:
            return rate
        if self.brl_per_usd is None:
            return None
        exchange = Decimal(str(self.brl_per_usd))
        return rate * exchange if currency == "BRL" else rate / exchange


def development_cost(token_usd: Decimal, active_hours: Decimal, rates: Rates) -> dict[str, Decimal | None]:
    """Token cost, the cost of a person's active hours, and their sum, in both currencies."""
    out: dict[str, Decimal | None] = {"token_usd": token_usd, "token_brl": to_brl(token_usd, rates.brl_per_usd)}
    for currency, tokens in (("usd", token_usd), ("brl", out["token_brl"])):
        rate = rates.hourly(currency.upper())
        time = active_hours * rate if rate is not None else None
        out[f"time_{currency}"] = time
        out[f"development_{currency}"] = tokens + time if tokens is not None and time is not None else None
    return out


def rounded(value: Decimal | None, places: int = 4) -> float | None:
    """A JSON-ready number, or None for a figure that is not configured."""
    return None if value is None else float(round(value, places))
