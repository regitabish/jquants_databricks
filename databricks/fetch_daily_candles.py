# Databricks notebook source
"""設定された商品ユニバースの日足を取得するエントリーポイント。"""

from __future__ import annotations

import sys
from pathlib import Path

if "__file__" in globals():
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
else:
    current_directory = Path.cwd()
    PROJECT_ROOT = (
        current_directory.parent
        if current_directory.name == "databricks"
        else current_directory
    )
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from market_data.entrypoints.databricks import main


if __name__ == "__main__":
    main()
