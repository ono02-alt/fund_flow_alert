# fund_flow_alert

大口・機関投資家の資金流入動向を毎日自動分析し、米国・日本市場の閉場後にHTMLメールで通知するシステムです。  
GitHub Actions（publicリポジトリ）＋ Gmail SMTPで**完全無料**で運用できます。

---

## できること

- **米国セクターローテーション検出**：SPDRセクターETF 11本を毎日分析し、どのセクターに資金が流入・流出しているかを把握
- **日本セクターローテーション検出**：NF業種ETF 15セクターを分析
- **半導体関連カテゴリー資金動向**：以下9カテゴリー・約60銘柄を個別スコアリング
  - 半導体製造装置 / メモリ・ロジック半導体 / MLCC・受動部品
  - 半導体材料 / 電線・銅箔 / パワー半導体
  - 半導体検査・テスト / 半導体商社・EMS / HBM・先端パッケージ
- **資金ローテーションサマリー**：「どのセクターから → どのセクターへ」を一目で把握
- **ベンチマーク確認**：日経225・TOPIX・SP500・NASDAQ100・SOX・VIX・ドル円

---

## ファイル構成

```
fund_flow_alert/
│
├── .github/
│   └── workflows/
│       └── fund_flow_alert.yml   ← GitHub Actionsの定義（自動実行スケジュール）
│
├── src/
│   ├── main.py       ← 実行エントリーポイント（ここから全処理が始まる）
│   ├── tickers.py    ← 銘柄・セクター定義（半導体9カテゴリー、米国ETF等）
│   ├── fund_flow.py  ← 資金流入スコア計算（OBV・出来高比率・価格変化率）
│   ├── report.py     ← HTML形式のメールレポート生成
│   └── mailer.py     ← Gmail SMTPでメール送信
│
├── requirements.txt  ← 依存ライブラリ（yfinance / pandas / numpy）
└── README.md
```

---

## セットアップ手順（スマートフォンのみで完結）

### 手順1：GitHubでリポジトリを作成

1. [github.com](https://github.com) をブラウザで開いてログイン
2. 右上の `+` → **New repository**
3. Repository name: `fund_flow_alert`
4. **Public**を選択（無料枠の使用に必要）
5. **Create repository**

### 手順2：ファイルをアップロード

GitHubリポジトリのページで **Add file → Upload files** を使い、以下のディレクトリ構造を維持してアップロードします。

```
アップロードが必要なファイル（絶対パスで記載）:

/fund_flow_alert/.github/workflows/fund_flow_alert.yml
/fund_flow_alert/src/main.py
/fund_flow_alert/src/tickers.py
/fund_flow_alert/src/fund_flow.py
/fund_flow_alert/src/report.py
/fund_flow_alert/src/mailer.py
/fund_flow_alert/requirements.txt
/fund_flow_alert/README.md
```

> **注意**：GitHub Web UIでフォルダごとドラッグ＆ドロップするか、ファイル名入力欄に `src/main.py` のようにパスを含めて入力するとディレクトリが自動作成されます。

### 手順3：Gmailアプリパスワードを取得

1. [myaccount.google.com](https://myaccount.google.com) を開く
2. **セキュリティ** → **2段階認証プロセス** を有効化
3. 検索欄に「アプリパスワード」と入力 → **アプリパスワード**
4. アプリ名に `fund_flow_alert` と入力 → **作成**
5. 表示された**16文字のパスワード**をメモ（スペースなしで保存）

### 手順4：GitHub Secretsを設定

リポジトリの **Settings → Secrets and variables → Actions → New repository secret** で以下の3つを追加します。

| シークレット名 | 設定する値 |
|---|---|
| `GMAIL_ADDRESS` | 送信元GmailアドレスKO（例: yourname@gmail.com）|
| `GMAIL_APP_PASSWORD` | 手順3で取得した16文字のアプリパスワード |
| `NOTIFY_EMAIL` | 通知先メールアドレス（例: hemu19705@gmail.com）|

### 手順5：動作確認（手動実行）

1. リポジトリの **Actions** タブを開く
2. 左側から **資金流入動向レポート** を選択
3. **Run workflow** → `dry_run` を `true` に設定 → **Run workflow**
4. 実行完了後、**Artifacts** に `report-html` が表示されればOK
5. `dry_run` を `false` にして再実行するとメールが届きます

---

## 実行スケジュール

| タイミング | UTC | JST | 曜日 |
|---|---|---|---|
| 日本市場閉場後 | 06:30 | 15:30 | 月〜金 |
| 米国市場閉場後 | 21:00 | 翌06:00 | 月〜金（JST火〜土） |

---

## スコア算出ロジック

資金流入スコア（−100〜+100）は以下の3指標の加重平均で算出します。

```
流入スコア = 価格変化率 × 40%
           + 出来高比率（直近N日 ÷ 過去20日平均）× 30%
           + OBV傾き（正規化） × 30%
```

| スコア帯 | 判定 | メール表示色 |
|---|---|---|
| +40以上 | 強い流入 | 濃い緑 |
| +15〜+40 | 流入 | 薄い緑 |
| −15〜+15 | 中立 | 黄色 |
| −40〜−15 | 流出 | 薄い赤 |
| −40以下 | 強い流出 | 濃い赤 |

デフォルトの分析期間は直近**5営業日**です。`--lookback N` で変更できます。

---

## ローカル（Oracle Cloud等）での手動実行

```bash
# 依存ライブラリのインストール
pip install -r /home/ubuntu/fund_flow_alert/requirements.txt

# dry-run（メール送信なし・HTMLファイルとして保存）
python /home/ubuntu/fund_flow_alert/src/main.py --dry-run

# 分析期間を3営業日に変更してdry-run
python /home/ubuntu/fund_flow_alert/src/main.py --lookback 3 --dry-run

# 環境変数を指定してメール送信
GMAIL_ADDRESS=yourname@gmail.com \
GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx \
NOTIFY_EMAIL=hemu19705@gmail.com \
python /home/ubuntu/fund_flow_alert/src/main.py
```

---

## 注意事項

- データソースは **yfinance（Yahoo Finance）** です。個人・非商用目的での利用を想定しています。
- 上場廃止銘柄はyfinanceがエラーを返しますが、プログラムは自動でスキップして処理を継続します。
- 本ツールの分析結果は参考情報です。売買判断はご自身でお願いします。
- GitHub Actionsのログは **publicリポジトリでは誰でも閲覧可能**です。機密情報はSecrets以外に記載しないでください。
