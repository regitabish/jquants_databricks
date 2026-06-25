# market_data_databricks

複数市場・資産クラスの価格データをDatabricksへ取り込むための基盤です。
現在はJ-Quants API V2と日経225ユニバースを実装しています。

## 構成

```text
databricks.yml                 Bundle本体
resources/
  daily_market_data_job.yml    Lakeflow Job定義
  market_data_schema.yml       Unity Catalog Schema定義
market_data/
  domain/                      汎用ドメインモデル
  application/                 取得ユースケースとポート
  infrastructure/              J-Quants、YAML、CSV、Delta
  entrypoints/databricks.py    Python wheel task入口
  resources/nikkei225.yaml     Wheel同梱ユニバース
pyproject.toml                 Wheelパッケージ定義
```

ドメインの`Instrument`は特定市場のコード形式に依存しません。東証4桁コードの
検証はJ-Quantsアダプターが担当するため、別のデータソースを追加すれば
米国株、商品、暗号資産などへ拡張できます。

## ローカル実行

```bash
pip install -r requirements.txt
```

`.env.example`をコピーしてAPIキーを設定します。

```dotenv
JQUANTS_API_KEY=your_api_key
MARKET_DATA_LOOKBACK_DAYS=7
MARKET_DATA_OUTPUT_CSV=data/nikkei225_daily_candles.csv
```

実行すると、PySparkがないローカル環境ではCSVへ保存します。

```bash
python databricks/fetch_daily_candles.py
```

## Databricks Bundle

Jobはserverless Python wheel taskとして定義されています。平日18:00
（Asia/Tokyo）に直近7日を再取得し、Unity Catalog管理Deltaテーブルへ
冪等にMERGEします。

MERGEキーは次の3列です。

```text
Provider + InstrumentKey + Date
```

### 前提条件

- Unity Catalogが有効なWorkspace
- Databricks CLI 0.229.0以上
- Pythonの`build`パッケージ
- `main` Catalogを利用できること
- serverlessからJ-Quants APIへHTTPS接続できること

CatalogやSchema名は[databricks.yml](databricks.yml)の変数で変更できます。
BundleはSchemaを作成しますが、Catalog自体は事前に存在する必要があります。
デプロイ・実行主体にはCatalogの利用とSchema作成権限が必要です。

### Secret作成

既定ではSecret Scope `market-data`、Key `jquants-api-key`を使用します。

```bash
databricks secrets create-scope market-data
databricks secrets put-secret market-data jquants-api-key
```

Secret値そのものはJobパラメーターや環境変数へ保存せず、Wheel実行時に
Databricks Secretsから取得します。

### 検証・デプロイ

CLIの認証後、開発環境へデプロイします。

```bash
python -m pip install build
databricks bundle validate -t dev
databricks bundle deploy -t dev
databricks bundle run daily_market_data -t dev
```

開発環境では`main.market_data_dev.daily_candles`へ保存され、スケジュールは
停止状態です。

本番環境は次のコマンドでデプロイします。

```bash
databricks bundle validate -t prod
databricks bundle deploy -t prod
```

本番では`main.market_data.daily_candles`へ保存されます。事故防止のため、
本番も初期状態ではスケジュール停止です。有効化する場合は次のように
デプロイします。

```bash
databricks bundle deploy -t prod \
  --var="schedule_pause_status=UNPAUSED"
```

サービスプリンシパルで運用する場合は、対象Workspaceに合わせてBundleの
`run_as`と権限を追加してください。

変数はデプロイ時に上書きできます。

```bash
databricks bundle deploy -t dev \
  --var="catalog=my_catalog,schema=market_data_dev"
```

## Deltaテーブル

初回実行時は管理Deltaテーブルを作成し、2回目以降はMERGEします。
保存列には以下の汎用メタデータが追加されます。

- `Provider`
- `InstrumentKey`
- `InstrumentSymbol`
- `Market`
- `AssetClass`
- `IngestedAt`

`MARKET_DATA_WRITE_MODE`またはJobパラメーターには`merge`、`append`、
`overwrite`を指定できます。定期Jobの既定値は`merge`です。

## ユニバース

既定の日経225ユニバースはWheelへ同梱されます。独自YAMLを使う場合は
`MARKET_DATA_UNIVERSE_FILE`、またはWheelタスクの`universe_file`
パラメーターで外部ファイルを指定できます。

```yaml
universe:
  expected_size: 2
  instrument_defaults:
    asset_class: equity

instruments:
  - symbol: AAPL
    market: NASDAQ
  - symbol: MSFT
    market: NASDAQ
```

## テストとWheelビルド

```bash
python -m unittest discover -s tests -v
python -m build --wheel
```
