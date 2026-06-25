from __future__ import annotations

import unittest

from market_data.entrypoints.databricks import _environment_overrides


class DatabricksEntrypointTest(unittest.TestCase):
    def test_maps_only_non_empty_job_parameters(self) -> None:
        overrides = _environment_overrides(
            lookback_days="7",
            output_table="main.market_data.daily_candles",
            universe_file="",
        )

        self.assertEqual(
            overrides,
            {
                "MARKET_DATA_LOOKBACK_DAYS": "7",
                "MARKET_DATA_OUTPUT_TABLE": (
                    "main.market_data.daily_candles"
                ),
            },
        )


if __name__ == "__main__":
    unittest.main()
