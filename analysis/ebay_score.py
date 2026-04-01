# -*- coding: utf-8 -*-
"""
EBAY 持仓卖出分析脚本（每日）
用法: python analysis/ebay_score.py
"""
import sys, io, os, csv, json
from datetime import datetime
if sys.stdout and hasattr(sys.stdout, 'buffer') and __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import yfinance as yf
import pandas as pd
import numpy as np

# ── 用户参数 ────────────────────────────────────────────────────────────────────
SYMBOL        = "EBAY"
ESPP_SHARES   = 1_957       # ESPP 持仓股数（每次卖出后手动更新）
ESPP_AVG_COST = 30.00       # ESPP 每股成本
RSU_SHARES    = 1_016       # RSU 持仓股数（每次卖出后手动更新）
RSU_AVG_COST  = 70.00       # RSU 归属价（成本基础）
SELL_TARGET   = 150_000     # 3年总卖出目标 ($)
ANNUAL_BUDGET = 40_000      # 今年年度卖出上限 ($)
TAX_RATE_LTCG = 0.321       # 联邦15% + NIIT 3.8% + 加州13.3%
LOOKBACK_DAYS = 400

SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR    = os.path.join(SCRIPT_DIR, "report")
os.makedirs(REPORT_DIR, exist_ok=True)
CSV_FILE      = os.path.join(REPORT_DIR, "ebay_history.csv")
HTML_FILE     = os.path.join(REPORT_DIR, "ebay_daily_report.html")
FUND_FILE     = os.path.join(REPORT_DIR, "ebay_fundamental.json")
SELL_LOG_FILE = os.path.join(REPORT_DIR, "ebay_sell_log.csv")

CSV_FIELDS = [
    "date", "price", "tech_score", "fund_score", "total_score",
    "rsi_score", "dist_score", "bb_score", "macd_score",
    "rsi_val", "dist_pct", "bb_z",
    "action", "pool", "suggested_shares", "tax_estimate", "net_proceeds",
]
SELL_LOG_FIELDS = [
    "date", "pool", "shares", "price", "proceeds",
    "capital_gain", "tax_estimate", "notes",
]

# ── 技术指标 ───────────────────────────────────────────────────────────────────
def fetch(symbol):
    df = yf.download(symbol, period=f"{LOOKBACK_DAYS}d", auto_adjust=True,
                     progress=False, multi_level_index=False)
    return df.dropna()

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return float('nan')
    delta = closes.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)
    ag = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    al = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = ag / al.where(al != 0, other=np.nan)
    return float((100 - 100 / (1 + rs)).iloc[-1])

def calc_macd(closes, fast=12, slow=26, signal=9):
    ml = closes.ewm(span=fast, adjust=False).mean() - closes.ewm(span=slow, adjust=False).mean()
    h  = ml - ml.ewm(span=signal, adjust=False).mean()
    return float(h.iloc[-1]), float(h.iloc[-2])

def calc_bb_z(closes, period=20):
    if len(closes) < period:
        return 0.0
    window = closes.iloc[-period:]
    std = window.std()
    return float((closes.iloc[-1] - window.mean()) / std) if std else 0.0

def calc_distance_52w_high(closes):
    """Returns % distance from 52-week high. 0 = at high, negative = below high."""
    lookback = closes.iloc[-252:] if len(closes) >= 252 else closes
    high_52w = float(lookback.max())
    current  = float(closes.iloc[-1])
    return (current - high_52w) / high_52w * 100

# ── 技术评分（高分 = 好卖点） ──────────────────────────────────────────────────
def score_rsi_sell(rsi: float) -> int:
    if rsi >= 70: return 15
    if rsi >= 60: return 8
    if rsi >= 50: return 3
    return 0

def score_distance_52w_high(pct: float) -> int:
    """pct <= 0. Closer to 0 = nearer to 52w high = better sell signal."""
    if pct >= -5:  return 15
    if pct >= -15: return 8
    if pct >= -30: return 3
    return 0

def score_bb_sell(bb_z: float) -> int:
    if bb_z > 2.0: return 10
    if bb_z > 1.5: return 5
    return 0

def score_macd_sell(h_prev: float, h_now: float) -> int:
    """Bearish top signals score high. Bottom expansion scores 0."""
    if h_prev > 0 and h_now < h_prev: return 10  # shrinking positive or zero-cross
    if h_now >= 0:                     return 5   # still positive but not shrinking
    return 0                                       # negative histogram

def calc_tech_score(s_rsi: int, s_dist: int, s_bb: int, s_macd: int) -> int:
    return s_rsi + s_dist + s_bb + s_macd
