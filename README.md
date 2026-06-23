# fund_flow_alert

大口・機関投資家の資金流入動向を分析し、米国・日本市場の閉場後にメールで通知するシステムです。  
GitHub Actions（publicリポジトリ）で完全無料運用。

---

## 機能

| 機能 | 内容 |
|------|------|
| 米国セクター分析 | SPDRセクターETF（XLK/XLF/XLE等）11セクターの資金流入を毎日分析 |
| 日本セクター分析 | NF業種ETF（1615〜1630.T）15セクターの資金動向を分析 |
| 半導体カテゴリー分析 | 9カテゴリー・約60銘柄の資金流入をスコアリング |
| ローテーション検出 | 「どこから → どこへ」資金が移動しているか可視化 |
| HTMLメール通知 | Gmail SMTPで閉場後に自動送信 |

### 半導体関連 9カテゴリー

1. **半導体製造装置**（東京エレクトロン、アドバンテスト、SCREENなど）
2. **メモリ・ロジック半導体**（キオクシア、ルネサス、ソシオネクストなど）
3. **MLCC・受動部品**（村田製作所、太陽誘電、TDKなど）
4. **半導体材料**（信越化学、JSR、SUMCO、東京応化など）
5. **電線・銅箔**（古河電工、住友電工、フジクラ、三井金属など）
6. **パワー半導体**（三菱電機、富士電機、ロームなど）
7. **半導体検査・テスト**（アドバンテスト、日本電子、日本マイクロニクスなど）
8. **半導体商社・EMS**（丸文、マクニカHD、加賀電子など）
9. **HBM・先端パッケージ**（イビデン、新光電気工業、メイコーなど）

---

## ファイル構成

```
fund_flow_alert/
├── .github/
│   └── workflows/
│       └── fund_flow_alert.yml   # GitHub Actions ワークフロー
├── src/
│   ├── main.py        # エントリーポイント
│   ├── tickers.py     # 銘柄・セクター定義マスタ
│   ├── fund_flow.py   # 資金流入分析エンジン（OBV・出来高・価格変化）
│   ├── report.py      # HTMLレポート生成
│   └── mailer.py      # Gmail SMTP 送信
├── tests/
│   └── test_fund_flow.py  # ユニットテスト
├── requirements.txt
└── README.md
```

---

## セットアップ手順

### 1. リポジトリを作成（公開設定で無料）

スマートフォンのブラウザから [github.com](https://github.com) を開き、  
**New repository** → リポジトリ名: `fund_flow_alert` → **Public** を選択して作成。

### 2. ファイルをアップロード

GitHubのリポジトリページから **Add file → Upload files** でファイルをアップロード。  
ディレクトリ構造ごとアップロードする場合は、GitHub Desktopアプリ（PC）か  
以下のコマンド（Termius経由でOracle Cloudから操作）を使います。

```bash
cd /home/ubuntu
git clone https://github.com/<YOUR_USERNAME>/fund_flow_alert.git
cp -r /path/to/fund_flow_alert/* /home/ubuntu/fund_flow_alert/
cd /home/ubuntu/fund_flow_alert
git add .
git commit -m "initial commit"
git push origin main
```

### 3. Gmailアプリパスワードを取得

1. Googleアカウント → **セキュリティ** → **2段階認証プロセス** を有効化
2. **アプリパスワード** → アプリ名: `fund_flow_alert` → 生成（16文字のパスワードが表示される）

### 4. GitHub Secrets を設定

リポジトリの **Settings → Secrets and variables → Actions → New repository secret** で以下を追加：

| シークレット名 | 値 |
|---|---|
| `GMAIL_ADDRESS` | 送信元Gmailアドレス（例: yourname@gmail.com）|
| `GMAIL_APP_PASSWORD` | 手順3で取得した16文字のアプリパスワード |
| `NOTIFY_EMAIL` | 通知先メールアドレス（例: hemu19705@gmail.com）|

### 5. 動作確認（手動実行）

リポジトリの **Actions → 資金流入動向レポート → Run workflow** を押す。  
`dry_run` を `true` にするとメール送信せずHTMLファイルをアーティファクトとして保存できます。

---

## 実行スケジュール

| タイミング | UTC | JST |
|---|---|---|
| 日本市場閉場後 | 毎週月〜金 06:30 UTC | 毎週月〜金 15:30 JST |
| 米国市場閉場後 | 毎週月〜金 21:00 UTC | 毎週火〜土 06:00 JST |

---

## スコア算出ロジック

```
流入スコア（-100〜+100） =
    価格変化率 × 40%
  + 出来高比率（直近N日 / 過去20日平均） × 30%
  + OBV傾き（正規化） × 30%
```

| スコア帯 | 判定 | 表示色 |
|---|---|---|
| +40以上 | 強い流入 | 濃い緑 |
| +15〜+40 | 流入 | 薄い緑 |
| -15〜+15 | 中立 | 黄色 |
| -40〜-15 | 流出 | 薄い赤 |
| -40以下 | 強い流出 | 濃い赤 |

---

## ローカルでの手動実行

```bash
# 依存ライブラリのインストール
pip install -r /home/ubuntu/fund_flow_alert/requirements.txt

# dry-run（メール送信なし・HTML保存）
python /home/ubuntu/fund_flow_alert/src/main.py --dry-run

# 実際に送信
GMAIL_ADDRESS=yourname@gmail.com \
GMAIL_APP_PASSWORD=xxxxxxxxxxxx \
NOTIFY_EMAIL=hemu19705@gmail.com \
python /home/ubuntu/fund_flow_alert/src/main.py

# 分析期間を変更（例: 3営業日）
python /home/ubuntu/fund_flow_alert/src/main.py --lookback 3 --dry-run
```

---

## テスト実行

```bash
cd /home/ubuntu/fund_flow_alert
python -m pytest tests/ -v
```

---

## 注意事項

- データソースは **yfinance（Yahoo Finance）** です。個人・教育目的での利用を想定しています。
- 日本市場のセクター分析はNF業種ETF（1615〜1630.T）を使用しています。流動性が低い場合はデータ取得に失敗することがあります。
- 本ツールの分析結果は投資判断の参考情報です。売買はご自身の判断で行ってください。
- GitHub Actionsの実行ログは **publicリポジトリでは誰でも閲覧可能**です。機密情報はSecrets以外には記載しないでください。
