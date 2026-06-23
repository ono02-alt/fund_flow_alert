#!/usr/bin/env python3
"""
main.py
資金流入動向分析のメインエントリーポイント

使い方:
    python main.py [--dry-run] [--lookback N] [--to EMAIL]

オプション:
    --dry-run        メール送信せず、HTML を report_output.html に保存
    --lookback N     分析期間（営業日）デフォルト5
    --to EMAIL       送信先メールアドレス（環境変数 NOTIFY_EMAIL より優先）
"""

import argparse
import logging
import sys
import os
from datetime import datetime
from pathlib import Path

# src/ ディレクトリをパスに追加（GitHub Actions 実行時も考慮）
sys.path.insert(0, str(Path(__file__).parent))

from tickers import (
    US_SECTOR_ETFS,
    JP_SECTOR_INDICES,
    JP_SEMI_CATEGORIES,
    BENCHMARKS,
    LOOKBACK_DAYS,
)
from fund_flow import (
    analyze_sector_flows,
    analyze_semi_category_flows,
    get_category_summary,
    get_benchmarks,
)
from report import build_html_report
from mailer import send_report

# ===== ロギング設定 =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="資金流入動向レポート生成・送信")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="メール送信せず report_output.html に保存"
    )
    parser.add_argument(
        "--lookback", type=int, default=LOOKBACK_DAYS,
        help=f"分析期間（営業日）デフォルト {LOOKBACK_DAYS}"
    )
    parser.add_argument(
        "--to", type=str, default=None,
        help="送信先メールアドレス"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    lookback = args.lookback
    now = datetime.now()

    logger.info(f"=== 資金流入動向レポート 開始 {now.strftime('%Y-%m-%d %H:%M')} ===")
    logger.info(f"分析期間: 直近 {lookback} 営業日")

    # 1. ベンチマーク取得
    logger.info("ベンチマーク取得中...")
    benchmarks = get_benchmarks(BENCHMARKS)
    logger.info(f"  取得完了: {list(benchmarks.keys())}")

    # 2. 米国セクター分析
    logger.info("米国セクター分析中...")
    us_sector_df = analyze_sector_flows(
        US_SECTOR_ETFS, lookback=lookback, label="米国"
    )
    if not us_sector_df.empty:
        logger.info(f"  米国セクター上位: {us_sector_df.head(3)['sector'].tolist()}")

    # 3. 日本セクター分析
    logger.info("日本セクター分析中...")
    jp_sector_df = analyze_sector_flows(
        JP_SECTOR_INDICES, lookback=lookback, label="日本"
    )
    if not jp_sector_df.empty:
        logger.info(f"  日本セクター上位: {jp_sector_df.head(3)['sector'].tolist()}")

    # 4. 半導体カテゴリー分析
    logger.info("半導体カテゴリー分析中...")
    semi_category_results = analyze_semi_category_flows(
        JP_SEMI_CATEGORIES, lookback=lookback
    )
    semi_summary = get_category_summary(semi_category_results)
    if not semi_summary.empty:
        logger.info(f"  半導体カテゴリー上位: {semi_summary.head(3)['category'].tolist()}")

    # 5. HTMLレポート生成
    logger.info("HTMLレポート生成中...")
    html = build_html_report(
        us_sector_df=us_sector_df,
        jp_sector_df=jp_sector_df,
        semi_category_results=semi_category_results,
        semi_summary=semi_summary,
        benchmarks=benchmarks,
        analysis_date=now,
        lookback_days=lookback,
    )

    # 6. 送信 or dry-run
    if args.dry_run:
        output_path = Path(__file__).parent.parent / "report_output.html"
        output_path.write_text(html, encoding="utf-8")
        logger.info(f"[dry-run] HTMLを保存しました: {output_path}")
        print(f"\n[dry-run] レポート保存先: {output_path}")
        return 0

    logger.info("メール送信中...")
    success = send_report(html, to_addr=args.to)
    if success:
        logger.info("=== 完了 ===")
        return 0
    else:
        logger.error("メール送信に失敗しました")
        return 1


if __name__ == "__main__":
    sys.exit(main())
