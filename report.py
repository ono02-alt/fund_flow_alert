"""
report.py
分析結果をHTML形式のメールレポートに変換する
"""

from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd


# ===== カラーマッピング =====
def _score_color(score: float) -> str:
    """flowスコアに応じた背景色を返す"""
    if score >= 40:
        return "#d4edda"   # 濃い緑（強い流入）
    elif score >= 15:
        return "#e8f5e9"   # 薄い緑（流入）
    elif score >= -15:
        return "#fff8e1"   # 黄色（中立）
    elif score >= -40:
        return "#fce4ec"   # 薄い赤（流出）
    else:
        return "#ffcdd2"   # 濃い赤（強い流出）


def _pct_badge(val: float) -> str:
    color = "#2e7d32" if val > 0 else "#c62828" if val < 0 else "#555"
    sign = "▲" if val > 0 else "▼" if val < 0 else "─"
    return f'<span style="color:{color};font-weight:bold">{sign}{abs(val):.2f}%</span>'


def _score_bar(score: float) -> str:
    """スコアをミニ棒グラフで表現"""
    pct = int((score + 100) / 2)  # -100~+100 → 0~100%
    color = "#43a047" if score > 0 else "#e53935"
    return (
        f'<div style="background:#eee;border-radius:3px;height:8px;width:80px;display:inline-block;vertical-align:middle">'
        f'<div style="width:{pct}%;background:{color};height:100%;border-radius:3px"></div></div>'
    )


# ===== セクションビルダー =====
def _section_header(title: str, icon: str = "📊") -> str:
    return (
        f'<h2 style="margin:24px 0 8px;padding:8px 12px;background:#1a237e;color:#fff;'
        f'border-radius:6px;font-size:15px">{icon} {title}</h2>'
    )


def _build_sector_table(df: pd.DataFrame, top_n: int = 11) -> str:
    """セクターETF分析テーブル"""
    if df.empty:
        return "<p>データなし</p>"

    rows_html = ""
    for _, row in df.head(top_n).iterrows():
        bg = _score_color(row["flow_score"])
        rows_html += (
            f'<tr style="background:{bg}">'
            f'<td style="padding:5px 8px">{row["sector"]}</td>'
            f'<td style="padding:5px 8px;text-align:center;font-size:11px;color:#555">{row["ticker"]}</td>'
            f'<td style="padding:5px 8px;text-align:right">{_pct_badge(row["price_change_pct"])}</td>'
            f'<td style="padding:5px 8px;text-align:right">{row["volume_ratio"]:.2f}x</td>'
            f'<td style="padding:5px 8px;text-align:center">{_score_bar(row["flow_score"])} {row["flow_score"]:.0f}</td>'
            f'</tr>'
        )

    return (
        f'<table style="width:100%;border-collapse:collapse;font-size:13px">'
        f'<thead><tr style="background:#283593;color:#fff">'
        f'<th style="padding:6px 8px;text-align:left">セクター</th>'
        f'<th style="padding:6px 8px">ティッカー</th>'
        f'<th style="padding:6px 8px">価格変化</th>'
        f'<th style="padding:6px 8px">出来高比</th>'
        f'<th style="padding:6px 8px">流入スコア</th>'
        f'</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        f'</table>'
    )


def _build_category_summary_table(df_summary: pd.DataFrame) -> str:
    """半導体カテゴリーサマリーテーブル"""
    if df_summary.empty:
        return "<p>データなし</p>"

    rows_html = ""
    for _, row in df_summary.iterrows():
        bg = _score_color(row["avg_flow_score"])
        rows_html += (
            f'<tr style="background:{bg}">'
            f'<td style="padding:5px 8px;font-weight:bold">{row["category"]}</td>'
            f'<td style="padding:5px 8px;text-align:center">{_score_bar(row["avg_flow_score"])} {row["avg_flow_score"]:.0f}</td>'
            f'<td style="padding:5px 8px;text-align:right">{_pct_badge(row["avg_price_change"])}</td>'
            f'<td style="padding:5px 8px;text-align:right">{row["avg_volume_ratio"]:.2f}x</td>'
            f'<td style="padding:5px 8px;font-size:12px">{row["top_stock"]} ({row["top_stock_score"]:.0f})</td>'
            f'</tr>'
        )

    return (
        f'<table style="width:100%;border-collapse:collapse;font-size:13px">'
        f'<thead><tr style="background:#1b5e20;color:#fff">'
        f'<th style="padding:6px 8px;text-align:left">カテゴリー</th>'
        f'<th style="padding:6px 8px">平均スコア</th>'
        f'<th style="padding:6px 8px">平均価格変化</th>'
        f'<th style="padding:6px 8px">出来高比</th>'
        f'<th style="padding:6px 8px;text-align:left">トップ銘柄(スコア)</th>'
        f'</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        f'</table>'
    )


def _build_category_detail(
    category_results: Dict[str, pd.DataFrame],
    top_n: int = 5,
) -> str:
    """カテゴリーごとの銘柄詳細"""
    html = ""
    for cat_name, df in category_results.items():
        if df.empty:
            continue
        rows_html = ""
        for _, row in df.head(top_n).iterrows():
            bg = _score_color(row["flow_score"])
            rows_html += (
                f'<tr style="background:{bg}">'
                f'<td style="padding:4px 6px">{row["name"]}</td>'
                f'<td style="padding:4px 6px;text-align:center;font-size:11px;color:#555">{row["ticker"]}</td>'
                f'<td style="padding:4px 6px;text-align:right">{_pct_badge(row["price_change_pct"])}</td>'
                f'<td style="padding:4px 6px;text-align:right">{row["volume_ratio"]:.2f}x</td>'
                f'<td style="padding:4px 6px;text-align:center">{row["flow_score"]:.0f}</td>'
                f'</tr>'
            )

        html += (
            f'<h4 style="margin:12px 0 4px;color:#1b5e20;font-size:13px">📌 {cat_name}</h4>'
            f'<table style="width:100%;border-collapse:collapse;font-size:12px;margin-bottom:8px">'
            f'<thead><tr style="background:#388e3c;color:#fff">'
            f'<th style="padding:4px 6px;text-align:left">銘柄</th>'
            f'<th style="padding:4px 6px">コード</th>'
            f'<th style="padding:4px 6px">価格変化</th>'
            f'<th style="padding:4px 6px">出来高比</th>'
            f'<th style="padding:4px 6px">スコア</th>'
            f'</tr></thead>'
            f'<tbody>{rows_html}</tbody>'
            f'</table>'
        )
    return html


def _build_benchmark_table(benchmarks: Dict[str, Dict]) -> str:
    """ベンチマーク一覧"""
    if not benchmarks:
        return "<p>データなし</p>"

    rows_html = ""
    for name, data in benchmarks.items():
        bg = "#e8f5e9" if data["change_pct"] > 0 else "#fce4ec"
        rows_html += (
            f'<tr style="background:{bg}">'
            f'<td style="padding:5px 8px">{name}</td>'
            f'<td style="padding:5px 8px;text-align:right">{data["last"]:,.2f}</td>'
            f'<td style="padding:5px 8px;text-align:right">{_pct_badge(data["change_pct"])}</td>'
            f'</tr>'
        )

    return (
        f'<table style="width:100%;border-collapse:collapse;font-size:13px">'
        f'<thead><tr style="background:#37474f;color:#fff">'
        f'<th style="padding:6px 8px;text-align:left">指標</th>'
        f'<th style="padding:6px 8px">直近値</th>'
        f'<th style="padding:6px 8px">前日比</th>'
        f'</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        f'</table>'
    )


def _build_rotation_summary(
    us_df: pd.DataFrame,
    jp_df: pd.DataFrame,
    semi_summary: pd.DataFrame,
) -> str:
    """ローテーションサマリー（どこからどこへ）"""
    lines = []

    def top_bottom(df: pd.DataFrame, name_col: str, label: str):
        if df.empty:
            return
        top3 = df.head(3)[name_col].tolist()
        bottom3 = df.tail(3)[name_col].tolist()
        lines.append(
            f'<li style="margin:4px 0"><b>【{label}】</b>'
            f'&nbsp;流入 → <span style="color:#2e7d32;font-weight:bold">'
            f'{" / ".join(top3)}</span>'
            f'&nbsp;&nbsp;流出 → <span style="color:#c62828;font-weight:bold">'
            f'{" / ".join(bottom3)}</span></li>'
        )

    top_bottom(us_df, "sector", "米国セクター")
    top_bottom(jp_df, "sector", "日本セクター")
    top_bottom(semi_summary, "category", "半導体カテゴリー")

    if not lines:
        return "<p>分析不可</p>"

    return (
        f'<div style="background:#e3f2fd;padding:12px;border-radius:6px;border-left:4px solid #1565c0">'
        f'<ul style="margin:0;padding-left:18px;font-size:13px">'
        + "".join(lines)
        + f'</ul></div>'
    )


# ===== メインビルダー =====
def build_html_report(
    us_sector_df: pd.DataFrame,
    jp_sector_df: pd.DataFrame,
    semi_category_results: Dict[str, pd.DataFrame],
    semi_summary: pd.DataFrame,
    benchmarks: Dict[str, Dict],
    analysis_date: Optional[datetime] = None,
    lookback_days: int = 5,
) -> str:
    """HTMLメールレポートを生成"""

    if analysis_date is None:
        analysis_date = datetime.now()

    date_str = analysis_date.strftime("%Y年%m月%d日（%a）")
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M JST")

    rotation_html = _build_rotation_summary(us_sector_df, jp_sector_df, semi_summary)
    us_table = _build_sector_table(us_sector_df)
    jp_table = _build_sector_table(jp_sector_df)
    semi_summary_table = _build_category_summary_table(semi_summary)
    semi_detail_html = _build_category_detail(semi_category_results)
    benchmark_table = _build_benchmark_table(benchmarks)

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>資金流入動向レポート {date_str}</title>
</head>
<body style="font-family:'Helvetica Neue',Arial,sans-serif;max-width:700px;margin:0 auto;padding:16px;background:#fafafa;color:#212121">

<!-- ヘッダー -->
<div style="background:linear-gradient(135deg,#1a237e,#283593);color:#fff;padding:16px 20px;border-radius:8px;margin-bottom:16px">
  <h1 style="margin:0;font-size:18px">📡 大口・機関投資家 資金流入動向レポート</h1>
  <p style="margin:4px 0 0;font-size:13px;opacity:0.85">{date_str}　／　直近{lookback_days}営業日ベース</p>
</div>

<!-- ベンチマーク -->
{_section_header("主要指標・ベンチマーク", "🌐")}
{benchmark_table}

<!-- ローテーションサマリー -->
{_section_header("資金ローテーションサマリー（どこからどこへ）", "🔄")}
{rotation_html}

<!-- 米国セクター -->
{_section_header("米国セクター別資金動向（SPDRセクターETF基準）", "🇺🇸")}
<p style="font-size:12px;color:#555;margin:4px 0 8px">流入スコア: OBV傾き・出来高比率・価格変化率の加重合計（−100〜+100）</p>
{us_table}

<!-- 日本セクター -->
{_section_header("日本セクター別資金動向（NF業種ETF基準）", "🇯🇵")}
{jp_table}

<!-- 半導体カテゴリーサマリー -->
{_section_header("半導体関連カテゴリー資金動向サマリー", "💡")}
<p style="font-size:12px;color:#555;margin:4px 0 8px">カテゴリー内銘柄の平均スコアでランキング</p>
{semi_summary_table}

<!-- 半導体カテゴリー詳細 -->
{_section_header("半導体カテゴリー別銘柄詳細（トップ5）", "🔬")}
{semi_detail_html}

<!-- フッター -->
<div style="margin-top:24px;padding:12px;background:#eceff1;border-radius:6px;font-size:11px;color:#607d8b">
  <p style="margin:0">⚠️ 本レポートは yfinance（Yahoo Finance）のデータを元に自動生成されています。</p>
  <p style="margin:4px 0 0">投資判断は必ずご自身でご確認ください。生成時刻: {generated_at}</p>
  <p style="margin:4px 0 0">スコア算出: 価格変化率×40% + 出来高比率×30% + OBV傾き×30%</p>
</div>

</body>
</html>"""

    return html
