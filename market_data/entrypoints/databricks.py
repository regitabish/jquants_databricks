"""Databricks Python wheel task用エントリーポイント。"""

from __future__ import annotations

import os
from typing import Callable, Mapping

from market_data.infrastructure.settings import JQuantsJobSettings


def _environment_overrides(
    *,
    start_date: str = "",
    end_date: str = "",
    lookback_days: str = "",
    universe_file: str = "",
    output_table: str = "",
    write_mode: str = "",
    request_interval_seconds: str = "",
) -> dict[str, str]:
    candidates = {
        "MARKET_DATA_START_DATE": start_date,
        "MARKET_DATA_END_DATE": end_date,
        "MARKET_DATA_LOOKBACK_DAYS": lookback_days,
        "MARKET_DATA_UNIVERSE_FILE": universe_file,
        "MARKET_DATA_OUTPUT_TABLE": output_table,
        "MARKET_DATA_WRITE_MODE": write_mode,
        "MARKET_DATA_REQUEST_INTERVAL_SECONDS": request_interval_seconds,
    }
    return {
        name: value.strip()
        for name, value in candidates.items()
        if value and value.strip()
    }


def _load_environment(
    overrides: Mapping[str, str],
    dotenv_loader: Callable[[], object] | None = None,
) -> dict[str, str]:
    """`.env`を読み込んだ後、Jobパラメーターを上書きする。"""

    if dotenv_loader is None:
        from dotenv import load_dotenv

        dotenv_loader = load_dotenv

    dotenv_loader()
    return {**os.environ, **overrides}


def main(
    start_date: str = "",
    end_date: str = "",
    lookback_days: str = "",
    universe_file: str = "",
    output_table: str = "",
    write_mode: str = "",
    request_interval_seconds: str = "",
    secret_scope: str = "",
    secret_key: str = "",
) -> None:
    """Jobパラメーターを設定へ変換し、J-Quants取込を実行する。"""

    environ = _load_environment(
        _environment_overrides(
            start_date=start_date,
            end_date=end_date,
            lookback_days=lookback_days,
            universe_file=universe_file,
            output_table=output_table,
            write_mode=write_mode,
            request_interval_seconds=request_interval_seconds,
        )
    )

    from market_data.bootstrap import run_jquants_job

    try:
        from pyspark.dbutils import DBUtils
        from pyspark.sql import SparkSession
    except ModuleNotFoundError:
        settings = JQuantsJobSettings.from_environment(environ)
        run_jquants_job(spark_session=None, settings=settings)
        return

    spark = SparkSession.builder.appName(
        "market-data-jquants-ingestion"
    ).getOrCreate()

    if not environ.get("JQUANTS_API_KEY", "").strip():
        if not secret_scope.strip() or not secret_key.strip():
            raise RuntimeError(
                "JQUANTS_API_KEY環境変数、またはsecret_scopeと"
                "secret_keyを指定してください。"
            )
        environ["JQUANTS_API_KEY"] = DBUtils(spark).secrets.get(
            scope=secret_scope.strip(),
            key=secret_key.strip(),
        )

    typed_environ: Mapping[str, str] = environ
    settings = JQuantsJobSettings.from_environment(typed_environ)
    run_jquants_job(spark_session=spark, settings=settings)
