"""標準出力への進捗表示。"""

from __future__ import annotations

from market_data.domain import Instrument


class ConsoleProgressReporter:
    def fetching(
        self,
        position: int,
        total: int,
        instrument: Instrument,
    ) -> None:
        print(
            f"[{position:03}/{total}] "
            f"{instrument.key} の日足を取得中"
        )

    def fetch_failed(
        self,
        instrument: Instrument,
        error: Exception,
    ) -> None:
        print(f"  {instrument.key} の取得失敗: {error}")

    def completed(self, row_count: int, destination: str) -> None:
        print(f"{row_count}行を {destination} に保存しました。")
