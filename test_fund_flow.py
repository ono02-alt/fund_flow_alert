"""
tests/test_fund_flow.py
資金流入分析モジュールのユニットテスト
"""

import sys
import os
import types
from pathlib import Path
import pandas as pd
import numpy as np
import pytest

# srcをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# yfinanceが未インストールでもテスト可能なようにモック化
if "yfinance" not in sys.modules:
    mock_yf = types.ModuleType("yfinance")
    sys.modules["yfinance"] = mock_yf

from fund_flow import calc_obv, calc_flow_score, get_category_summary
from report import build_html_report, _score_color
from tickers import US_SECTOR_ETFS, JP_SEMI_CATEGORIES, BENCHMARKS


# ===== テスト用ダミーデータ生成 =====
def make_dummy_df(n=30, trend="up"):
    """ダミーのOHLCVデータを生成"""
    np.random.seed(42)
    base = 1000.0
    closes = []
    for i in range(n):
        if trend == "up":
            base += np.random.uniform(0, 5)
        elif trend == "down":
            base -= np.random.uniform(0, 5)
        else:
            base += np.random.uniform(-3, 3)
        closes.append(base)

    df = pd.DataFrame({
        "Open":   [c - 2 for c in closes],
        "High":   [c + 3 for c in closes],
        "Low":    [c - 3 for c in closes],
        "Close":  closes,
        "Volume": np.random.randint(100_000, 1_000_000, n).tolist(),
    })
    return df


# ===== calc_obv =====
class TestCalcObv:
    def test_returns_series(self):
        df = make_dummy_df()
        obv = calc_obv(df)
        assert isinstance(obv, pd.Series)
        assert len(obv) == len(df)

    def test_uptrend_obv_positive(self):
        """上昇トレンドではOBVが正方向に増加する傾向"""
        df = make_dummy_df(n=30, trend="up")
        obv = calc_obv(df)
        assert obv.iloc[-1] > obv.iloc[0]

    def test_downtrend_obv_negative(self):
        """下落トレンドではOBVが負方向に推移する傾向"""
        df = make_dummy_df(n=30, trend="down")
        obv = calc_obv(df)
        assert obv.iloc[-1] < obv.iloc[0]

    def test_no_nan(self):
        df = make_dummy_df()
        obv = calc_obv(df)
        assert not obv.isna().any()


# ===== calc_flow_score =====
class TestCalcFlowScore:
    def test_returns_dict(self):
        df = make_dummy_df()
        result = calc_flow_score(df)
        assert isinstance(result, dict)

    def test_required_keys(self):
        df = make_dummy_df()
        result = calc_flow_score(df)
        required = {"price_change_pct", "volume_ratio", "obv_slope_norm", "flow_score", "last_close", "last_volume"}
        assert required.issubset(result.keys())

    def test_score_range(self):
        """スコアは-100〜+100の範囲内"""
        df = make_dummy_df()
        result = calc_flow_score(df)
        assert -100 <= result["flow_score"] <= 100

    def test_uptrend_positive_score(self):
        """上昇トレンドはスコアが正になる傾向"""
        df = make_dummy_df(n=30, trend="up")
        result = calc_flow_score(df, lookback=5)
        assert result["flow_score"] > 0

    def test_downtrend_negative_score(self):
        """下落トレンドはスコアが負になる傾向"""
        df = make_dummy_df(n=30, trend="down")
        result = calc_flow_score(df, lookback=5)
        assert result["flow_score"] < 0

    def test_returns_empty_on_short_data(self):
        """データ不足時は空dictを返す"""
        df = make_dummy_df(n=5)
        result = calc_flow_score(df, lookback=5)
        assert result == {}

    def test_none_input(self):
        """Noneが渡された場合は空dictを返す"""
        result = calc_flow_score(None)
        assert result == {}

    def test_volume_ratio_positive(self):
        df = make_dummy_df()
        result = calc_flow_score(df)
        assert result["volume_ratio"] > 0


# ===== get_category_summary =====
class TestGetCategorySummary:
    def _make_category_results(self):
        rows_a = [
            {"category": "A", "name": "銘柄1", "ticker": "0001.T", "flow_score": 50, "price_change_pct": 2.0, "volume_ratio": 1.5},
            {"category": "A", "name": "銘柄2", "ticker": "0002.T", "flow_score": 30, "price_change_pct": 1.0, "volume_ratio": 1.2},
        ]
        rows_b = [
            {"category": "B", "name": "銘柄3", "ticker": "0003.T", "flow_score": -20, "price_change_pct": -1.0, "volume_ratio": 0.8},
        ]
        return {
            "カテゴリーA": pd.DataFrame(rows_a).sort_values("flow_score", ascending=False),
            "カテゴリーB": pd.DataFrame(rows_b).sort_values("flow_score", ascending=False),
        }

    def test_returns_dataframe(self):
        results = self._make_category_results()
        summary = get_category_summary(results)
        assert isinstance(summary, pd.DataFrame)

    def test_sorted_by_score(self):
        results = self._make_category_results()
        summary = get_category_summary(results)
        scores = summary["avg_flow_score"].tolist()
        assert scores == sorted(scores, reverse=True)

    def test_required_columns(self):
        results = self._make_category_results()
        summary = get_category_summary(results)
        for col in ["category", "avg_flow_score", "avg_price_change", "avg_volume_ratio", "top_stock"]:
            assert col in summary.columns

    def test_empty_input(self):
        summary = get_category_summary({})
        assert summary.empty


# ===== _score_color =====
class TestScoreColor:
    def test_high_positive(self):
        assert _score_color(50) == "#d4edda"

    def test_mild_positive(self):
        assert _score_color(20) == "#e8f5e9"

    def test_neutral(self):
        assert _score_color(0) == "#fff8e1"

    def test_mild_negative(self):
        assert _score_color(-20) == "#fce4ec"

    def test_high_negative(self):
        assert _score_color(-50) == "#ffcdd2"


# ===== build_html_report =====
class TestBuildHtmlReport:
    def _make_sector_df(self, label):
        return pd.DataFrame([{
            "market": label,
            "sector": "テストセクター",
            "ticker": "TEST",
            "price_change_pct": 1.5,
            "volume_ratio": 1.3,
            "obv_slope_norm": 0.01,
            "flow_score": 35.0,
            "last_close": 100.0,
            "last_volume": 500000,
        }])

    def test_returns_string(self):
        df = self._make_sector_df("米国")
        html = build_html_report(
            us_sector_df=df,
            jp_sector_df=df,
            semi_category_results={},
            semi_summary=pd.DataFrame(),
            benchmarks={},
        )
        assert isinstance(html, str)

    def test_contains_doctype(self):
        df = self._make_sector_df("米国")
        html = build_html_report(
            us_sector_df=df,
            jp_sector_df=df,
            semi_category_results={},
            semi_summary=pd.DataFrame(),
            benchmarks={},
        )
        assert "<!DOCTYPE html>" in html

    def test_contains_sector_name(self):
        df = self._make_sector_df("米国")
        html = build_html_report(
            us_sector_df=df,
            jp_sector_df=df,
            semi_category_results={},
            semi_summary=pd.DataFrame(),
            benchmarks={},
        )
        assert "テストセクター" in html

    def test_empty_dataframes(self):
        """空のDataFrameでもエラーなく生成できる"""
        html = build_html_report(
            us_sector_df=pd.DataFrame(),
            jp_sector_df=pd.DataFrame(),
            semi_category_results={},
            semi_summary=pd.DataFrame(),
            benchmarks={},
        )
        assert len(html) > 100

    def test_benchmark_included(self):
        df = self._make_sector_df("米国")
        benchmarks = {"SP500": {"last": 5000.0, "change_pct": 0.5}}
        html = build_html_report(
            us_sector_df=df,
            jp_sector_df=df,
            semi_category_results={},
            semi_summary=pd.DataFrame(),
            benchmarks=benchmarks,
        )
        assert "SP500" in html


# ===== tickers.py の構造チェック =====
class TestTickers:
    def test_us_sector_etfs_not_empty(self):
        assert len(US_SECTOR_ETFS) > 0

    def test_jp_semi_categories_not_empty(self):
        assert len(JP_SEMI_CATEGORIES) > 0

    def test_semi_categories_have_required_keys(self):
        required = {"半導体製造装置", "MLCC・受動部品", "メモリ・ロジック半導体", "電線・銅箔"}
        assert required.issubset(set(JP_SEMI_CATEGORIES.keys()))

    def test_each_category_has_stocks(self):
        for cat, stocks in JP_SEMI_CATEGORIES.items():
            assert len(stocks) > 0, f"カテゴリー '{cat}' に銘柄がありません"

    def test_ticker_format_jp(self):
        """日本株ティッカーは .T で終わる"""
        for cat, stocks in JP_SEMI_CATEGORIES.items():
            for name, ticker in stocks.items():
                assert ticker.endswith(".T"), f"{name}: {ticker} は .T で終わっていません"

    def test_benchmarks_not_empty(self):
        assert len(BENCHMARKS) > 0
