"""
fund_flow.py
資金流入・流出をOBV、出来高、価格変化率から分析する
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

try:
    import yfinance as yf
    _YF_AVAILABLE = True
except ImportError:
    _YF_AVAILABLE = False

logger = logging.getLogger(__name__)


def _safe_download(ticker: str, period: str = "1mo") -> Optional[pd.DataFrame]:
    """yfinanceで安全にデータ取得（エラー時はNone）"""
    if not _YF_AVAILABLE:
        logger.warning("yfinance が未インストールのためスキップ: %s", ticker)
        return None
    try:
        df = yf.download(
            ticker,
            period=period,
            progress=False,
            auto_adjust=True,
            multi_level_index=False,
        )
        if df is None or df.empty:
            return None
        return df
    except Exception as e:
        logger.warning(f"[{ticker}] データ取得失敗: {e}")
        return None


def calc_obv(df: pd.DataFrame) -> pd.Series:
    """On Balance Volume (OBV) を計算"""
    close = df["Close"]
    volume = df["Volume"]
    direction = np.sign(close.diff().fillna(0))
    obv = (direction * volume).cumsum()
    return obv


def calc_flow_score(df: pd.DataFrame, lookback: int = 5) -> Dict:
    """
    資金流入スコアを計算する
    - price_change_pct : 直近N日の価格変化率
    - volume_ratio     : 直近N日の出来高 / 過去20日平均出来高
    - obv_slope        : OBVの傾き（正=流入、負=流出）
    - flow_score       : 総合スコア (−100 〜 +100)
    """
    if df is None or len(df) < max(lookback + 1, 21):
        return {}

    close = df["Close"]
    volume = df["Volume"]

    # 価格変化率
    price_change = (close.iloc[-1] - close.iloc[-lookback]) / close.iloc[-lookback] * 100

    # 出来高比率（直近N日平均 vs 過去20日平均）
    recent_vol = volume.iloc[-lookback:].mean()
    hist_vol = volume.iloc[-20:].mean()
    vol_ratio = recent_vol / hist_vol if hist_vol > 0 else 1.0

    # OBV傾き（直近N日）
    obv = calc_obv(df)
    obv_recent = obv.iloc[-lookback:]
    x = np.arange(len(obv_recent))
    if len(x) > 1:
        obv_slope = float(np.polyfit(x, obv_recent.values, 1)[0])
        # 正規化: OBV傾きを出来高スケールで割る
        obv_norm = obv_slope / (hist_vol + 1e-9)
    else:
        obv_norm = 0.0

    # 総合スコア（重み付け）
    # price: 40%, volume_ratio: 30%, obv: 30%
    score = (
        np.clip(price_change * 4, -40, 40)
        + np.clip((vol_ratio - 1.0) * 30, -30, 30)
        + np.clip(obv_norm * 30, -30, 30)
    )
    score = float(np.clip(score, -100, 100))

    return {
        "price_change_pct": round(float(price_change), 2),
        "volume_ratio":     round(float(vol_ratio), 2),
        "obv_slope_norm":   round(float(obv_norm), 4),
        "flow_score":       round(score, 1),
        "last_close":       round(float(close.iloc[-1]), 2),
        "last_volume":      int(volume.iloc[-1]),
    }


def analyze_sector_flows(
    sector_dict: Dict[str, str],
    lookback: int = 5,
    label: str = "",
) -> pd.DataFrame:
    """
    セクターETF/指数の資金流入を分析してDataFrameで返す
    sector_dict: {セクター名: ティッカー}
    """
    rows = []
    for sector_name, ticker in sector_dict.items():
        df = _safe_download(ticker, period="2mo")
        if df is None:
            logger.warning(f"[{sector_name}({ticker})] スキップ")
            continue
        scores = calc_flow_score(df, lookback=lookback)
        if scores:
            rows.append({
                "market":       label,
                "sector":       sector_name,
                "ticker":       ticker,
                **scores,
            })

    if not rows:
        return pd.DataFrame()

    result = pd.DataFrame(rows).sort_values("flow_score", ascending=False)
    return result


def analyze_semi_category_flows(
    semi_categories: Dict[str, Dict[str, str]],
    lookback: int = 5,
) -> Dict[str, pd.DataFrame]:
    """
    半導体サブカテゴリーごとに資金流入を分析
    Returns: {カテゴリー名: DataFrame}
    """
    category_results = {}

    for category, stocks in semi_categories.items():
        rows = []
        for name, ticker in stocks.items():
            df = _safe_download(ticker, period="2mo")
            if df is None:
                continue
            scores = calc_flow_score(df, lookback=lookback)
            if scores:
                rows.append({
                    "category": category,
                    "name":     name,
                    "ticker":   ticker,
                    **scores,
                })

        if rows:
            df_cat = pd.DataFrame(rows).sort_values("flow_score", ascending=False)
            category_results[category] = df_cat

    return category_results


def get_category_summary(
    category_results: Dict[str, pd.DataFrame]
) -> pd.DataFrame:
    """カテゴリーごとの平均flowスコアを集計してランキング化"""
    rows = []
    for category, df in category_results.items():
        if df.empty:
            continue
        rows.append({
            "category":          category,
            "avg_flow_score":    round(df["flow_score"].mean(), 1),
            "avg_price_change":  round(df["price_change_pct"].mean(), 2),
            "avg_volume_ratio":  round(df["volume_ratio"].mean(), 2),
            "stock_count":       len(df),
            "top_stock":         df.iloc[0]["name"] if not df.empty else "-",
            "top_stock_score":   df.iloc[0]["flow_score"] if not df.empty else 0,
        })

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows).sort_values("avg_flow_score", ascending=False)


def detect_rotation(
    df_before: pd.DataFrame,
    df_after: pd.DataFrame,
    score_col: str = "flow_score",
    name_col: str = "sector",
) -> List[Dict]:
    """
    ローテーション（資金移動）を検出する
    スコアが大幅に上がったセクター（流入先）と下がったセクター（流出元）を返す
    """
    if df_before.empty or df_after.empty:
        return []

    # 共通キーでマージ
    merged = pd.merge(
        df_before[[name_col, score_col]].rename(columns={score_col: "score_before"}),
        df_after[[name_col, score_col]].rename(columns={score_col: "score_after"}),
        on=name_col,
        how="inner",
    )
    merged["score_delta"] = merged["score_after"] - merged["score_before"]

    rotations = []
    top_inflow = merged.nlargest(3, "score_after")
    top_outflow = merged.nsmallest(3, "score_after")

    for _, row in top_inflow.iterrows():
        rotations.append({
            "direction": "流入",
            "name": row[name_col],
            "score": row["score_after"],
            "delta": row["score_delta"],
        })
    for _, row in top_outflow.iterrows():
        rotations.append({
            "direction": "流出",
            "name": row[name_col],
            "score": row["score_after"],
            "delta": row["score_delta"],
        })

    return rotations


def get_benchmarks(benchmark_dict: Dict[str, str]) -> Dict[str, Dict]:
    """ベンチマーク指標を取得"""
    result = {}
    for name, ticker in benchmark_dict.items():
        df = _safe_download(ticker, period="5d")
        if df is None or df.empty:
            continue
        try:
            last = float(df["Close"].iloc[-1])
            prev = float(df["Close"].iloc[-2])
            change_pct = (last - prev) / prev * 100
            result[name] = {
                "last":       round(last, 2),
                "change_pct": round(change_pct, 2),
            }
        except Exception:
            pass
    return result
