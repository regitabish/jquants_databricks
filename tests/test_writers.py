from __future__ import annotations

import unittest
from unittest.mock import patch

from market_data.infrastructure.writers import (
    DeltaCandleWriter,
    _quote_table_name,
)


class FakePandasFrame:
    columns = [
        "Date",
        "Provider",
        "InstrumentKey",
        "InstrumentSymbol",
    ]


class FakeWrite:
    def __init__(self) -> None:
        self.saved_table: str | None = None
        self.mode_name: str | None = None

    def format(self, name: str) -> FakeWrite:
        return self

    def mode(self, name: str) -> FakeWrite:
        self.mode_name = name
        return self

    def option(self, name: str, value: str) -> FakeWrite:
        return self

    def saveAsTable(self, table: str) -> None:
        self.saved_table = table


class FakeSparkFrame:
    def __init__(self) -> None:
        self.write = FakeWrite()
        self.temp_view: str | None = None

    def createOrReplaceTempView(self, name: str) -> None:
        self.temp_view = name


class FakeCatalog:
    def __init__(self, table_exists: bool) -> None:
        self._table_exists = table_exists
        self.dropped_view: str | None = None

    def tableExists(self, table: str) -> bool:
        return self._table_exists

    def dropTempView(self, name: str) -> None:
        self.dropped_view = name


class FakeConf:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def set(self, name: str, value: str) -> None:
        self.values[name] = value


class FakeSpark:
    def __init__(self, table_exists: bool) -> None:
        self.catalog = FakeCatalog(table_exists)
        self.conf = FakeConf()
        self.frame = FakeSparkFrame()
        self.queries: list[str] = []

    def createDataFrame(self, frame: object) -> FakeSparkFrame:
        return self.frame

    def sql(self, query: str) -> None:
        self.queries.append(query)


class DeltaCandleWriterTest(unittest.TestCase):
    def test_quotes_unity_catalog_table_name(self) -> None:
        self.assertEqual(
            _quote_table_name("main.market_data.daily_candles"),
            "`main`.`market_data`.`daily_candles`",
        )

        with self.assertRaises(ValueError):
            _quote_table_name("main.market-data.daily_candles")

    @patch(
        "market_data.infrastructure.writers._to_dataframe",
        return_value=FakePandasFrame(),
    )
    def test_creates_table_on_first_run(self, _: object) -> None:
        spark = FakeSpark(table_exists=False)
        writer = DeltaCandleWriter(
            spark_session=spark,
            output_table="main.market_data.daily_candles",
            provider="jquants",
        )

        writer.write([])

        self.assertEqual(
            spark.frame.write.saved_table,
            "main.market_data.daily_candles",
        )
        self.assertEqual(spark.frame.write.mode_name, "errorifexists")

    @patch(
        "market_data.infrastructure.writers._to_dataframe",
        return_value=FakePandasFrame(),
    )
    def test_merges_existing_table_by_provider_instrument_and_date(
        self,
        _: object,
    ) -> None:
        spark = FakeSpark(table_exists=True)
        writer = DeltaCandleWriter(
            spark_session=spark,
            output_table="main.market_data.daily_candles",
            provider="jquants",
        )

        writer.write([])

        query = spark.queries[0]
        self.assertIn("target.`Provider` = source.`Provider`", query)
        self.assertIn(
            "target.`InstrumentKey` = source.`InstrumentKey`",
            query,
        )
        self.assertIn("target.`Date` = source.`Date`", query)
        self.assertIsNotNone(spark.catalog.dropped_view)


if __name__ == "__main__":
    unittest.main()
