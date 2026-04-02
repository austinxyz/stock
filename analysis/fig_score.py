# -*- coding: utf-8 -*-
"""
FIG (Figma) 持仓信心评分脚本
用法: py analysis/fig_score.py
对比 FIG 与 PLTR、NOW、DDOG、ADBE，辅助 Roth IRA 换仓决策。
"""
import sys, io, os, csv, json, time
from datetime import datetime, timedelta
if sys.stdout and hasattr(sys.stdout, 'buffer') and __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import yfinance as yf
import pandas as pd
import numpy as np

# ── 用户参数 ────────────────────────────────────────────────────────────────────
SYMBOL        = "FIG"
SHARES        = 50
AVG_COST      = 62.82
PEERS         = ["PLTR", "NOW", "DDOG", "ADBE"]
ALL_SYMBOLS   = [SYMBOL] + PEERS
LOOKBACK_DAYS = 400
FUND_CACHE_DAYS = 7          # 基本面缓存有效期（天）

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR  = os.path.join(SCRIPT_DIR, "report")
os.makedirs(REPORT_DIR, exist_ok=True)
CSV_FILE    = os.path.join(REPORT_DIR, "fig_history.csv")
HTML_FILE   = os.path.join(REPORT_DIR, "fig_daily_report.html")
FUND_FILE   = os.path.join(REPORT_DIR, "fig_fundamental.json")

CSV_FIELDS = [
    "date", "price", "tech_score", "fund_score", "total_score",
    "rsi_score", "macd_score", "ma200_score", "dd_score",
    "rsi_val", "ma200_val", "dd_pct",
    "rank", "recommendation",
]

# ── 数据拉取 ───────────────────────────────────────────────────────────────────
def fetch(symbol: str) -> pd.DataFrame:
    for attempt in range(3):
        df = yf.download(symbol, period=f"{LOOKBACK_DAYS}d", auto_adjust=True,
                         progress=False, multi_level_index=False)
        df = df.dropna()
        if not df.empty:
            return df
        if attempt < 2:
            time.sleep(3)
    return df

# ── 技术指标计算 ───────────────────────────────────────────────────────────────
def calc_rsi(closes: pd.Series, period: int = 14) -> float:
    if len(closes) < period + 1:
        return float('nan')
    delta = closes.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)
    ag = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    al = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    last_al = float(al.iloc[-1])
    if last_al == 0:
        return 100.0
    rs = ag / al.where(al != 0, other=np.nan)
    return float((100 - 100 / (1 + rs)).iloc[-1])

def calc_macd(closes: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ml = closes.ewm(span=fast, adjust=False).mean() - closes.ewm(span=slow, adjust=False).mean()
    h  = ml - ml.ewm(span=signal, adjust=False).mean()
    return float(h.iloc[-1]), float(h.iloc[-2])

def calc_ma200(closes: pd.Series) -> float:
    period = min(200, len(closes))
    return float(closes.iloc[-period:].mean())

def calc_drawdown_from_high(closes: pd.Series) -> float:
    lookback = closes.iloc[-252:] if len(closes) >= 252 else closes
    high_52w = float(lookback.max())
    current  = float(closes.iloc[-1])
    return (current - high_52w) / high_52w * 100

# ── 技术评分（高分 = 上升趋势，值得持有） ─────────────────────────────────────
def score_rsi_hold(rsi: float) -> int:
    if 50 <= rsi <= 70: return 15
    if 35 <= rsi < 50:  return 8
    if rsi > 70:        return 8
    return 3

def score_macd_hold(h_prev: float, h_now: float) -> int:
    if h_prev < 0 and h_now > 0:            return 10   # 金叉
    if h_prev >= 0 and h_now >= h_prev and h_now > 0: return 10  # 正值扩张
    if h_now > 0:                   return 5    # 正值收窄
    return 0

def score_ma200(price: float, ma200: float) -> int:
    return 10 if price > ma200 else 0

def score_drawdown(pct: float) -> int:
    if pct >= -10: return 5
    if pct >= -25: return 3
    if pct >= -40: return 1
    return 0

def calc_tech_score(s_rsi: int, s_macd: int, s_ma200: int, s_dd: int) -> int:
    return s_rsi + s_macd + s_ma200 + s_dd

# ── 基本面评分（高分 = 基本面强，值得持有） ──────────────────────────────────────
def score_revenue_growth(growth: float) -> int:
    if growth >= 0.20: return 20
    if growth >= 0.10: return 13
    if growth >= 0.05: return 6
    return 0

def score_upside(target: float, current: float) -> int:
    if target <= 0 or current <= 0:
        return 0
    upside = (target - current) / current
    if upside >= 0.30: return 20
    if upside >= 0.15: return 13
    if upside >= 0.05: return 6
    return 0

def score_analyst_rating(rec_mean: float) -> int:
    """1=强买 → 5=强卖。值越低越看多，越值得持有。"""
    if rec_mean <= 2.0: return 20
    if rec_mean <= 2.5: return 13
    if rec_mean <= 3.0: return 6
    return 0

def calc_fund_score(s_revenue: int, s_upside: int, s_rating: int) -> int:
    return s_revenue + s_upside + s_rating
