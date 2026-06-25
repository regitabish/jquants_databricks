"""J-Quants APIの日足ローソク足アダプター。"""

from __future__ import annotations

import re
from typing import Any

from market_data.domain import CandleRecord, DateRange, Instrument

JQUANTS_CODE_PATTERN = re.compile(r"^[0-9A-Z]{4}$")
JQUANTS_SUPPORTED_MARKETS = {None, "JPX", "TSE", "XJPX", "XTKS"}


class JQuantsDailyCandleSource:
    def __init__(self, client: Any) -> None:
        self._client = client

    def fetch(
        self,
        instrument: Instrument,
        date_range: DateRange,
    ) -> tuple[CandleRecord, ...]:
        market = instrument.market.upper() if instrument.market else None
        if market not in JQUANTS_SUPPORTED_MARKETS:
            raise ValueError(
                f"J-Quantsで利用できない市場です: {instrument.market}"
            )

        code = instrument.symbol.strip().upper()
        if not JQUANTS_CODE_PATTERN.fullmatch(code):
            raise ValueError(
                f"J-Quantsで利用できない商品シンボルです: "
                f"{instrument.symbol}"
            )

        frame = self._client.get_eq_bars_daily(
            code=code,
            from_yyyymmdd=date_range.start.isoformat(),
            to_yyyymmdd=date_range.end.isoformat(),
        )
        if frame.empty:
            return ()

        return tuple(
            CandleRecord.from_mapping(row)
            for row in frame.to_dict(orient="records")
        )
