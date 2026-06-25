from __future__ import annotations

import unittest
from datetime import date

from market_data.domain import CandleRecord, DateRange, Instrument


class InstrumentTest(unittest.TestCase):
    def test_accepts_symbols_from_multiple_asset_classes(self) -> None:
        instruments = [
            Instrument("7203", market="JPX", asset_class="equity"),
            Instrument("AAPL", market="NASDAQ", asset_class="equity"),
            Instrument("XAUUSD", market="OTC", asset_class="commodity"),
        ]

        self.assertEqual(
            [instrument.key for instrument in instruments],
            ["JPX:7203", "NASDAQ:AAPL", "OTC:XAUUSD"],
        )

    def test_only_requires_a_non_empty_symbol(self) -> None:
        self.assertEqual(Instrument(" btc-usd ").symbol, "btc-usd")

        with self.assertRaises(ValueError):
            Instrument("  ")


class DateRangeTest(unittest.TestCase):
    def test_rejects_reversed_range(self) -> None:
        with self.assertRaises(ValueError):
            DateRange(date(2026, 6, 25), date(2026, 6, 24))

    def test_from_strings_preserves_reversed_range_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "開始日"):
            DateRange.from_strings("2026-06-25", "2026-06-24")


class CandleRecordTest(unittest.TestCase):
    def test_copies_input_mapping(self) -> None:
        source = {"Date": "2026-01-05", "Close": 100}
        candle = CandleRecord(source)
        source["Close"] = 200

        self.assertEqual(candle.to_dict()["Close"], 100)


if __name__ == "__main__":
    unittest.main()
