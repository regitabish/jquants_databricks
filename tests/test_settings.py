from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path

from market_data.infrastructure.settings import JQuantsJobSettings


class JQuantsJobSettingsTest(unittest.TestCase):
    def test_uses_lookback_when_dates_are_omitted(self) -> None:
        settings = JQuantsJobSettings.from_environment(
            {
                "JQUANTS_API_KEY": "secret",
                "MARKET_DATA_LOOKBACK_DAYS": "7",
            },
            today=date(2026, 6, 25),
        )

        self.assertEqual(settings.date_range.start, date(2026, 6, 19))
        self.assertEqual(settings.date_range.end, date(2026, 6, 25))
        self.assertIsNone(settings.universe_file)
        self.assertEqual(settings.write_mode, "merge")

    def test_reads_generic_market_data_environment_names(self) -> None:
        settings = JQuantsJobSettings.from_environment(
            {
                "JQUANTS_API_KEY": "secret",
                "MARKET_DATA_START_DATE": "2026-01-01",
                "MARKET_DATA_END_DATE": "2026-01-31",
                "MARKET_DATA_UNIVERSE_FILE": "config/us_equities.yaml",
            }
        )

        self.assertEqual(
            settings.universe_file,
            Path("config/us_equities.yaml"),
        )

    def test_legacy_default_universe_path_uses_packaged_resource(
        self,
    ) -> None:
        settings = JQuantsJobSettings.from_environment(
            {
                "JQUANTS_API_KEY": "secret",
                "JQUANTS_START_DATE": "2026-01-01",
                "JQUANTS_END_DATE": "2026-01-31",
                "JQUANTS_SYMBOLS_FILE": "config/nikkei225.yaml",
            }
        )

        self.assertIsNone(settings.universe_file)


if __name__ == "__main__":
    unittest.main()
