"""OS・ランタイム機能のアダプター。"""

from __future__ import annotations

import time


class SystemSleeper:
    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)
