"""環境変数からJ-Quantsジョブの設定を生成する。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Mapping
from zoneinfo import ZoneInfo

from market_data.domain import DateRange


def _read(
    values: Mapping[str, str],
    name: str,
    legacy_name: str | None = None,
    default: str = "",
) -> str:
    value = values.get(name)
    if value is None and legacy_name:
        value = values.get(legacy_name)
    return default if value is None else value


def _resolve_universe_file(value: str) -> Path | None:
    if not value:
        return None

    path = Path(value)
    if (
        path.as_posix().lower() == "config/nikkei225.yaml"
        and not path.exists()
    ):
        return None
    return path


@dataclass(frozen=True)
class JQuantsJobSettings:
    api_key: str = field(repr=False)
    universe_file: Path | None
    date_range: DateRange
    output_table: str
    output_csv: Path
    write_mode: str
    request_interval_seconds: float

    @classmethod
    def from_environment(
        cls,
        environ: Mapping[str, str] | None = None,
        today: date | None = None,
    ) -> JQuantsJobSettings:
        values = os.environ if environ is None else environ

        api_key = values.get("JQUANTS_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(
                "JQUANTS_API_KEYを.envまたは環境変数に設定してください。"
            )

        start_date = _read(
            values,
            "MARKET_DATA_START_DATE",
            "JQUANTS_START_DATE",
        ).strip()
        end_date = _read(
            values,
            "MARKET_DATA_END_DATE",
            "JQUANTS_END_DATE",
        ).strip()
        if bool(start_date) != bool(end_date):
            raise RuntimeError(
                "開始日と終了日は両方指定するか、両方省略してください。"
            )

        if start_date and end_date:
            date_range = DateRange.from_strings(start_date, end_date)
        else:
            lookback_days = _read(
                values,
                "MARKET_DATA_LOOKBACK_DAYS",
                default="7",
            ).strip()
            try:
                lookback = int(lookback_days)
            except ValueError as exc:
                raise ValueError(
                    "MARKET_DATA_LOOKBACK_DAYSは整数で指定してください。"
                ) from exc
            if lookback < 1:
                raise ValueError(
                    "MARKET_DATA_LOOKBACK_DAYSは1以上にしてください。"
                )

            target_date = today or datetime.now(
                ZoneInfo("Asia/Tokyo")
            ).date()
            date_range = DateRange(
                start=target_date - timedelta(days=lookback - 1),
                end=target_date,
            )

        interval_text = _read(
            values,
            "MARKET_DATA_REQUEST_INTERVAL_SECONDS",
            "JQUANTS_REQUEST_INTERVAL_SECONDS",
            "0.2",
        ).strip()
        try:
            request_interval_seconds = float(interval_text)
        except ValueError as exc:
            raise ValueError(
                "MARKET_DATA_REQUEST_INTERVAL_SECONDSは数値で"
                "指定してください。"
            ) from exc
        if request_interval_seconds < 0:
            raise ValueError(
                "MARKET_DATA_REQUEST_INTERVAL_SECONDSは0以上に"
                "してください。"
            )

        universe_file_text = _read(
            values,
            "MARKET_DATA_UNIVERSE_FILE",
            "JQUANTS_SYMBOLS_FILE",
        ).strip()
        write_mode = _read(
            values,
            "MARKET_DATA_WRITE_MODE",
            "JQUANTS_WRITE_MODE",
            "merge",
        ).strip().lower()
        if write_mode not in {"merge", "append", "overwrite"}:
            raise ValueError(
                "MARKET_DATA_WRITE_MODEはmerge、append、overwriteの"
                "いずれかを指定してください。"
            )

        return cls(
            api_key=api_key,
            universe_file=_resolve_universe_file(universe_file_text),
            date_range=date_range,
            output_table=_read(
                values,
                "MARKET_DATA_OUTPUT_TABLE",
                "JQUANTS_OUTPUT_TABLE",
                "default.nikkei225_daily_candles",
            ),
            output_csv=Path(
                _read(
                    values,
                    "MARKET_DATA_OUTPUT_CSV",
                    "JQUANTS_OUTPUT_CSV",
                    "data/nikkei225_daily_candles.csv",
                )
            ),
            write_mode=write_mode,
            request_interval_seconds=request_interval_seconds,
        )
