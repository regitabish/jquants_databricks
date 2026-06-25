from __future__ import annotations

import unittest
from datetime import date

from market_data.domain import DateRange, Instrument
from market_data.infrastructure.jquants import JQuantsDailyCandleSource


class FakeFrame:
    empty = True


class SpyJQuantsClient:
    def __init__(self) -> None:
        self.code: str | None = None

    def get_eq_bars_daily(
        self,
        code: str,
        from_yyyymmdd: str,
        to_yyyymmdd: str,
    ) -> FakeFrame:
        self.code = code
        return FakeFrame()


class JQuantsDailyCandleSourceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = SpyJQuantsClient()
        self.source = JQuantsDailyCandleSource(self.client)
        self.date_range = DateRange(date(2026, 1, 1), date(2026, 1, 31))

    def test_jquants_normalizes_its_own_symbol_format(self) -> None:
        self.source.fetch(Instrument("285a"), self.date_range)

        self.assertEqual(self.client.code, "285A")

    def test_jquants_rejects_unsupported_symbol_without_domain_rule(self) -> None:
        instrument = Instrument(
            "AAPL",
            market="NASDAQ",
            asset_class="equity",
        )

        with self.assertRaisesRegex(ValueError, "J-Quants"):
            self.source.fetch(instrument, self.date_range)


if __name__ == "__main__":
    unittest.main()
