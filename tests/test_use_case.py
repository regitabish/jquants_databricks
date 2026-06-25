from __future__ import annotations

import unittest
from datetime import date

from market_data.application import (
    FetchDailyCandles,
    FetchDailyCandlesRequest,
    NoCandleDataError,
    PartialFetchError,
)
from market_data.domain import (
    CandleRecord,
    DateRange,
    Instrument,
    InstrumentCandle,
)


class FakeInstrumentUniverse:
    def __init__(self, instruments: list[Instrument]) -> None:
        self._instruments = tuple(instruments)

    def load_instruments(self) -> tuple[Instrument, ...]:
        return self._instruments


class FakeCandleSource:
    def __init__(
        self,
        responses: dict[str, list[dict[str, object]] | Exception],
    ) -> None:
        self._responses = responses

    def fetch(
        self,
        instrument: Instrument,
        date_range: DateRange,
    ) -> tuple[CandleRecord, ...]:
        response = self._responses[instrument.key]
        if isinstance(response, Exception):
            raise response
        return tuple(CandleRecord(row) for row in response)


class SpyWriter:
    def __init__(self) -> None:
        self.items: list[InstrumentCandle] = []

    def write(
        self,
        candles: tuple[InstrumentCandle, ...] | list[InstrumentCandle],
    ) -> str:
        self.items = list(candles)
        return "test-output"


class SpySleeper:
    def __init__(self) -> None:
        self.calls: list[float] = []

    def sleep(self, seconds: float) -> None:
        self.calls.append(seconds)


class SpyReporter:
    def __init__(self) -> None:
        self.completed_rows: int | None = None

    def fetching(
        self,
        position: int,
        total: int,
        instrument: Instrument,
    ) -> None:
        pass

    def fetch_failed(
        self,
        instrument: Instrument,
        error: Exception,
    ) -> None:
        pass

    def completed(self, row_count: int, destination: str) -> None:
        self.completed_rows = row_count


class FetchDailyCandlesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.date_range = DateRange(date(2026, 1, 1), date(2026, 1, 31))
        self.writer = SpyWriter()
        self.sleeper = SpySleeper()
        self.reporter = SpyReporter()

    def build_use_case(
        self,
        instruments: list[Instrument],
        responses: dict[str, list[dict[str, object]] | Exception],
    ) -> FetchDailyCandles:
        return FetchDailyCandles(
            instrument_universe=FakeInstrumentUniverse(instruments),
            candle_source=FakeCandleSource(responses),
            candle_writer=self.writer,
            sleeper=self.sleeper,
            progress_reporter=self.reporter,
        )

    def test_fetches_multiple_asset_classes_with_same_use_case(self) -> None:
        instruments = [
            Instrument("7203", market="JPX", asset_class="equity"),
            Instrument("XAUUSD", market="OTC", asset_class="commodity"),
        ]
        use_case = self.build_use_case(
            instruments,
            {
                "JPX:7203": [{"Date": "2026-01-05", "Close": 100}],
                "OTC:XAUUSD": [{"Date": "2026-01-05", "Close": 200}],
            },
        )

        report = use_case.execute(
            FetchDailyCandlesRequest(self.date_range, 0.1)
        )

        self.assertEqual(report.row_count, 2)
        self.assertEqual(
            [item.instrument.key for item in self.writer.items],
            ["JPX:7203", "OTC:XAUUSD"],
        )
        self.assertEqual(self.sleeper.calls, [0.1, 0.1])
        self.assertEqual(self.reporter.completed_rows, 2)

    def test_writes_successes_before_reporting_partial_failure(self) -> None:
        instruments = [
            Instrument("7203", market="JPX"),
            Instrument("AAPL", market="NASDAQ"),
        ]
        use_case = self.build_use_case(
            instruments,
            {
                "JPX:7203": [{"Date": "2026-01-05", "Close": 100}],
                "NASDAQ:AAPL": RuntimeError("API error"),
            },
        )

        with self.assertRaises(PartialFetchError) as context:
            use_case.execute(FetchDailyCandlesRequest(self.date_range, 0))

        self.assertEqual(context.exception.report.row_count, 1)
        self.assertEqual(len(self.writer.items), 1)

    def test_does_not_write_when_no_candles_were_fetched(self) -> None:
        instruments = [
            Instrument("7203", market="JPX"),
            Instrument("AAPL", market="NASDAQ"),
        ]
        use_case = self.build_use_case(
            instruments,
            {
                "JPX:7203": [],
                "NASDAQ:AAPL": RuntimeError("API error"),
            },
        )

        with self.assertRaises(NoCandleDataError):
            use_case.execute(FetchDailyCandlesRequest(self.date_range, 0))

        self.assertEqual(self.writer.items, [])


if __name__ == "__main__":
    unittest.main()
