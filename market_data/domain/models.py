"""外部サービスや特定市場に依存しないドメインモデル。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from types import MappingProxyType
from typing import Any, Mapping


@dataclass(frozen=True)
class Instrument:
    """株式・商品・通貨など、価格を取得する対象。"""

    symbol: str
    market: str | None = None
    asset_class: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        symbol = str(self.symbol).strip()
        if not symbol:
            raise ValueError("商品シンボルは空にできません。")

        market = self.market.strip() if self.market else None
        asset_class = self.asset_class.strip() if self.asset_class else None
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "market", market)
        object.__setattr__(self, "asset_class", asset_class)
        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(dict(self.metadata)),
        )

    @property
    def key(self) -> str:
        """市場を含めた保存・表示用の一意キー。"""

        if self.market:
            return f"{self.market}:{self.symbol}"
        return self.symbol


@dataclass(frozen=True)
class DateRange:
    """マーケットデータの取得期間。"""

    start: date
    end: date

    def __post_init__(self) -> None:
        if self.start > self.end:
            raise ValueError("取得開始日は終了日以前にしてください。")

    @classmethod
    def from_strings(cls, start: str, end: str) -> DateRange:
        try:
            start_date = date.fromisoformat(start)
            end_date = date.fromisoformat(end)
        except ValueError as exc:
            raise ValueError("取得期間はYYYY-MM-DD形式で指定してください。") from exc
        return cls(start=start_date, end=end_date)


@dataclass(frozen=True)
class CandleRecord:
    """プロバイダー固有の追加列を保持できるローソク足レコード。"""

    values: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "values",
            MappingProxyType(dict(self.values)),
        )

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> CandleRecord:
        return cls(values=values)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.values)


@dataclass(frozen=True)
class InstrumentCandle:
    """取得対象の商品とローソク足の関連。"""

    instrument: Instrument
    candle: CandleRecord
