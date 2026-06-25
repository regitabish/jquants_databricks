"""汎用の日足ローソク足取得ユースケース。"""

from __future__ import annotations

from dataclasses import dataclass

from market_data.application.ports import (
    CandleWriter,
    DailyCandleSource,
    InstrumentUniverse,
    ProgressReporter,
    Sleeper,
)
from market_data.domain import DateRange, Instrument, InstrumentCandle


@dataclass(frozen=True)
class FetchDailyCandlesRequest:
    date_range: DateRange
    request_interval_seconds: float = 0.2

    def __post_init__(self) -> None:
        if self.request_interval_seconds < 0:
            raise ValueError("リクエスト間隔は0秒以上にしてください。")


@dataclass(frozen=True)
class FetchFailure:
    instrument: Instrument
    message: str


@dataclass(frozen=True)
class FetchReport:
    row_count: int
    destination: str
    failures: tuple[FetchFailure, ...]


class NoCandleDataError(RuntimeError):
    """保存できるローソク足が1件もない場合のエラー。"""


class PartialFetchError(RuntimeError):
    """一部商品の取得に失敗した場合のエラー。"""

    def __init__(self, report: FetchReport) -> None:
        self.report = report
        failed_instruments = ", ".join(
            failure.instrument.key for failure in report.failures
        )
        super().__init__(
            f"{len(report.failures)}商品の取得に失敗しました: "
            f"{failed_instruments}"
        )


class FetchDailyCandles:
    """ユニバース内の全商品について日足を取得・保存する。"""

    def __init__(
        self,
        instrument_universe: InstrumentUniverse,
        candle_source: DailyCandleSource,
        candle_writer: CandleWriter,
        sleeper: Sleeper,
        progress_reporter: ProgressReporter,
    ) -> None:
        self._instrument_universe = instrument_universe
        self._candle_source = candle_source
        self._candle_writer = candle_writer
        self._sleeper = sleeper
        self._progress_reporter = progress_reporter

    def execute(self, request: FetchDailyCandlesRequest) -> FetchReport:
        instruments = tuple(self._instrument_universe.load_instruments())
        candles: list[InstrumentCandle] = []
        failures: list[FetchFailure] = []

        for position, instrument in enumerate(instruments, start=1):
            self._progress_reporter.fetching(
                position,
                len(instruments),
                instrument,
            )

            try:
                fetched = self._candle_source.fetch(
                    instrument,
                    request.date_range,
                )
                candles.extend(
                    InstrumentCandle(instrument=instrument, candle=candle)
                    for candle in fetched
                )
            except Exception as exc:
                failures.append(
                    FetchFailure(instrument=instrument, message=str(exc))
                )
                self._progress_reporter.fetch_failed(instrument, exc)
            finally:
                if request.request_interval_seconds > 0:
                    self._sleeper.sleep(request.request_interval_seconds)

        if not candles:
            raise NoCandleDataError("保存対象のローソク足データがありません。")

        destination = self._candle_writer.write(candles)
        report = FetchReport(
            row_count=len(candles),
            destination=destination,
            failures=tuple(failures),
        )
        self._progress_reporter.completed(report.row_count, report.destination)

        if failures:
            raise PartialFetchError(report)

        return report
