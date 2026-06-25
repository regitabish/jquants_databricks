"""YAMLで定義した商品ユニバースのアダプター。"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Any, Mapping, TextIO

import yaml

from market_data.domain import Instrument


class YamlInstrumentUniverse:
    """任意のファイルパスからYAMLユニバースを読み込む。"""

    def __init__(self, yaml_path: str | Path) -> None:
        self._yaml_path = Path(yaml_path)

    def load_instruments(self) -> tuple[Instrument, ...]:
        with self._yaml_path.open(encoding="utf-8") as stream:
            return _load_instruments(stream, str(self._yaml_path))


class PackagedYamlInstrumentUniverse:
    """Wheelへ同梱したYAMLユニバースを読み込む。"""

    def __init__(self, resource_name: str) -> None:
        self._resource_name = resource_name

    def load_instruments(self) -> tuple[Instrument, ...]:
        resource = files("market_data.resources").joinpath(
            self._resource_name
        )
        with resource.open("r", encoding="utf-8") as stream:
            return _load_instruments(
                stream,
                f"market_data.resources/{self._resource_name}",
            )


def _load_instruments(
    stream: TextIO,
    source_name: str,
) -> tuple[Instrument, ...]:
    settings: Any = yaml.safe_load(stream)

    if not isinstance(settings, dict):
        raise ValueError(f"{source_name} の内容が不正です。")

    universe = settings.get("universe", {})
    if not isinstance(universe, dict):
        raise ValueError(
            f"{source_name} の universe はマッピングで"
            "指定してください。"
        )

    defaults = universe.get("instrument_defaults", {})
    if not isinstance(defaults, dict):
        raise ValueError(
            f"{source_name} の instrument_defaults は"
            "マッピングで指定してください。"
        )

    raw_instruments = settings.get("instruments")
    if not isinstance(raw_instruments, list):
        raise ValueError(
            f"{source_name} の instruments はリストで指定してください。"
        )

    instruments = tuple(
        _to_instrument(raw_instrument, defaults)
        for raw_instrument in raw_instruments
    )
    _validate(instruments, universe.get("expected_size"))
    return instruments


def _to_instrument(
    raw_instrument: object,
    defaults: Mapping[str, Any],
) -> Instrument:
    if isinstance(raw_instrument, str):
        values: dict[str, Any] = {
            **defaults,
            "symbol": raw_instrument,
        }
    elif isinstance(raw_instrument, dict):
        values = {**defaults, **raw_instrument}
    else:
        raise ValueError(
            "instrumentsの要素は文字列またはマッピングで"
            "指定してください。"
        )

    symbol = values.pop("symbol", None)
    market = values.pop("market", None)
    asset_class = values.pop("asset_class", None)
    if symbol is None:
        raise ValueError("各商品にはsymbolが必要です。")

    return Instrument(
        symbol=str(symbol),
        market=str(market) if market is not None else None,
        asset_class=(
            str(asset_class) if asset_class is not None else None
        ),
        metadata=values,
    )


def _validate(
    instruments: tuple[Instrument, ...],
    expected_size: object,
) -> None:
    keys = [instrument.key for instrument in instruments]
    if len(set(keys)) != len(keys):
        raise ValueError("商品ユニバースに重複があります。")

    if expected_size is None:
        return
    if not isinstance(expected_size, int) or isinstance(
        expected_size,
        bool,
    ):
        raise ValueError("expected_sizeは整数で指定してください。")
    if len(instruments) != expected_size:
        raise ValueError(
            f"商品ユニバースが{expected_size}件ではありません: "
            f"{len(instruments)}件"
        )
