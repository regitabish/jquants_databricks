"""J-Quantsジョブの依存関係を組み立てる。"""

from __future__ import annotations

from typing import Any

from market_data.application import FetchDailyCandles, FetchDailyCandlesRequest
from market_data.infrastructure.jquants import JQuantsDailyCandleSource
from market_data.infrastructure.settings import JQuantsJobSettings
from market_data.infrastructure.system import SystemSleeper
from market_data.infrastructure.universes import (
    PackagedYamlInstrumentUniverse,
    YamlInstrumentUniverse,
)
from market_data.infrastructure.writers import CsvCandleWriter, DeltaCandleWriter
from market_data.presentation.console import ConsoleProgressReporter


def run_jquants_job(
    spark_session: Any | None = None,
    settings: JQuantsJobSettings | None = None,
) -> None:
    from dotenv import load_dotenv
    import jquantsapi

    load_dotenv()
    job_settings = settings or JQuantsJobSettings.from_environment()

    if spark_session is None:
        candle_writer = CsvCandleWriter(
            job_settings.output_csv,
            provider="jquants",
        )
    else:
        candle_writer = DeltaCandleWriter(
            spark_session=spark_session,
            output_table=job_settings.output_table,
            write_mode=job_settings.write_mode,
            provider="jquants",
        )

    if job_settings.universe_file is None:
        instrument_universe = PackagedYamlInstrumentUniverse(
            "nikkei225.yaml"
        )
    else:
        instrument_universe = YamlInstrumentUniverse(
            job_settings.universe_file
        )

    use_case = FetchDailyCandles(
        instrument_universe=instrument_universe,
        candle_source=JQuantsDailyCandleSource(
            jquantsapi.ClientV2(api_key=job_settings.api_key)
        ),
        candle_writer=candle_writer,
        sleeper=SystemSleeper(),
        progress_reporter=ConsoleProgressReporter(),
    )
    use_case.execute(
        FetchDailyCandlesRequest(
            date_range=job_settings.date_range,
            request_interval_seconds=(
                job_settings.request_interval_seconds
            ),
        )
    )
