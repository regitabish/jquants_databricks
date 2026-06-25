from __future__ import annotations

import unittest
from unittest.mock import patch

from market_data.entrypoints.databricks import (
    _environment_overrides,
    _load_environment,
)


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

    def test_loads_dotenv_before_constructing_local_environment(
        self,
    ) -> None:
        def load_dotenv() -> None:
            import os

            os.environ["JQUANTS_API_KEY"] = "from-dotenv"

        with patch.dict("os.environ", {}, clear=True):
            environ = _load_environment(
                {"MARKET_DATA_LOOKBACK_DAYS": "7"},
                dotenv_loader=load_dotenv,
            )

        self.assertEqual(environ["JQUANTS_API_KEY"], "from-dotenv")
        self.assertEqual(environ["MARKET_DATA_LOOKBACK_DAYS"], "7")


if __name__ == "__main__":
    unittest.main()
