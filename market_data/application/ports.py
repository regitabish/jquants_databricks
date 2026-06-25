"""ユースケースが利用する抽象ポート。"""

from __future__ import annotations

from typing import Protocol, Sequence

from market_data.domain import (
    CandleRecord,
    DateRange,
    Instrument,
    InstrumentCandle,
)


class InstrumentUniverse(Protocol):
    def load_instruments(self) -> Sequence[Instrument]:
        """取得対象の商品一覧を読み込む。"""


class DailyCandleSource(Protocol):
    def fetch(
        self,
        instrument: Instrument,
        date_range: DateRange,
    ) -> Sequence[CandleRecord]:
        """1商品分の日足ローソク足を取得する。"""


class CandleWriter(Protocol):
    def write(self, candles: Sequence[InstrumentCandle]) -> str:
        """ローソク足を保存し、保存先の説明を返す。"""


class Sleeper(Protocol):
    def sleep(self, seconds: float) -> None:
        """次のリクエストまで待機する。"""


class ProgressReporter(Protocol):
    def fetching(
        self,
        position: int,
        total: int,
        instrument: Instrument,
    ) -> None:
        """取得開始を通知する。"""

    def fetch_failed(
        self,
        instrument: Instrument,
        error: Exception,
    ) -> None:
        """取得失敗を通知する。"""

    def completed(self, row_count: int, destination: str) -> None:
        """保存完了を通知する。"""
