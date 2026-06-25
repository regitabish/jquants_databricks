"""CSVおよびDeltaテーブルへの保存アダプター。"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence
from uuid import uuid4

from market_data.domain import InstrumentCandle

TABLE_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
MERGE_KEY_COLUMNS = ("Provider", "InstrumentKey", "Date")


def _to_dataframe(
    candles: Sequence[InstrumentCandle],
    provider: str,
) -> Any:
    import pandas as pd

    ingested_at = datetime.now(timezone.utc).replace(tzinfo=None)
    rows: list[dict[str, Any]] = []
    for item in candles:
        row = item.candle.to_dict()
        row["Provider"] = provider
        row["InstrumentKey"] = item.instrument.key
        row["InstrumentSymbol"] = item.instrument.symbol
        row["Market"] = item.instrument.market
        row["AssetClass"] = item.instrument.asset_class
        row["IngestedAt"] = ingested_at
        rows.append(row)

    frame = pd.DataFrame(rows)
    sort_columns = [
        column
        for column in ("InstrumentKey", "Date")
        if column in frame.columns
    ]
    if sort_columns:
        frame.sort_values(sort_columns, inplace=True)

    if all(column in frame.columns for column in MERGE_KEY_COLUMNS):
        frame.drop_duplicates(
            subset=list(MERGE_KEY_COLUMNS),
            keep="last",
            inplace=True,
        )
    return frame.reset_index(drop=True)


def _quote_table_name(table_name: str) -> str:
    parts = table_name.split(".")
    if not 1 <= len(parts) <= 3 or any(
        not TABLE_IDENTIFIER_PATTERN.fullmatch(part)
        for part in parts
    ):
        raise ValueError(
            "出力テーブル名はcatalog.schema.table形式の"
            "英数字とアンダースコアで指定してください。"
        )
    return ".".join(f"`{part}`" for part in parts)


class CsvCandleWriter:
    def __init__(
        self,
        output_path: str | Path,
        provider: str = "unknown",
    ) -> None:
        self._output_path = Path(output_path)
        self._provider = provider

    def write(self, candles: Sequence[InstrumentCandle]) -> str:
        frame = _to_dataframe(candles, self._provider)
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(self._output_path, index=False, encoding="utf-8")
        return str(self._output_path)


class DeltaCandleWriter:
    def __init__(
        self,
        spark_session: Any,
        output_table: str,
        write_mode: str = "merge",
        provider: str = "unknown",
    ) -> None:
        if write_mode not in {"merge", "append", "overwrite"}:
            raise ValueError(
                "write_modeはmerge、append、overwriteの"
                "いずれかを指定してください。"
            )
        self._spark_session = spark_session
        self._output_table = output_table
        self._quoted_output_table = _quote_table_name(output_table)
        self._write_mode = write_mode
        self._provider = provider

    def write(self, candles: Sequence[InstrumentCandle]) -> str:
        frame = _to_dataframe(candles, self._provider)
        spark_frame = self._spark_session.createDataFrame(frame)

        if self._write_mode == "merge":
            self._merge(spark_frame, frame.columns)
        else:
            (
                spark_frame.write.format("delta")
                .mode(self._write_mode)
                .option("overwriteSchema", "true")
                .saveAsTable(self._output_table)
            )

        return f"Deltaテーブル {self._output_table}"

    def _merge(self, spark_frame: Any, columns: Sequence[str]) -> None:
        missing_columns = [
            column
            for column in MERGE_KEY_COLUMNS
            if column not in columns
        ]
        if missing_columns:
            raise ValueError(
                "Delta MERGEに必要な列がありません: "
                f"{', '.join(missing_columns)}"
            )

        if not self._spark_session.catalog.tableExists(
            self._output_table
        ):
            (
                spark_frame.write.format("delta")
                .mode("errorifexists")
                .saveAsTable(self._output_table)
            )
            return

        temp_view = f"market_data_upsert_{uuid4().hex}"
        spark_frame.createOrReplaceTempView(temp_view)
        quoted_view = f"`{temp_view}`"
        try:
            self._spark_session.sql(
                f"""
                MERGE INTO {self._quoted_output_table} AS target
                USING {quoted_view} AS source
                ON target.`Provider` = source.`Provider`
                  AND target.`InstrumentKey` = source.`InstrumentKey`
                  AND target.`Date` = source.`Date`
                WHEN MATCHED THEN UPDATE SET *
                WHEN NOT MATCHED THEN INSERT *
                """
            )
        finally:
            self._spark_session.catalog.dropTempView(temp_view)
