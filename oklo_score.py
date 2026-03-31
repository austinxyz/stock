# -*- coding: utf-8 -*-
"""
OKLO 个股买入信号评分脚本
用法:
  python oklo_score.py          # 每日快跑（技术面 + 缓存基本面）
  python oklo_score.py --full   # 深度分析（重新拉取基本面 + SEC 公告）
"""

import sys, io, os, csv, json, argparse
from datetime import datetime, timedelta
if sys.stdout and hasattr(sys.stdout, 'buffer') and __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import yfinance as yf
import pandas as pd
import numpy as np
import requests

# ── 用户参数 ────────────────────────────────────────────────────────────────────
SYMBOL         = "OKLO"
SHARES         = 80
AVG_COST       = 115.38
STOP_LOSS_PCT  = 0.70          # 最大亏损容忍（70%）
STOP_LOSS_PRICE = round(AVG_COST * (1 - STOP_LOSS_PCT), 2)  # $34.61
ADD_BUDGET     = 5_000
LOOKBACK_DAYS  = 400

SCRIPT_DIR       = os.path.dirname(os.path.abspath(__file__))
CSV_FILE         = os.path.join(SCRIPT_DIR, "oklo_history.csv")
HTML_FILE        = os.path.join(SCRIPT_DIR, "oklo_report.html")
FUNDAMENTAL_FILE = os.path.join(SCRIPT_DIR, "oklo_fundamental.json")

CSV_FIELDS = [
    "date", "price", "tech_score", "fund_score", "total_score",
    "dd_score", "rsi_score", "macd_score", "bb_score",
    "dd_pct", "rsi_val", "bb_z", "strategy",
    "cash_runway_months", "analyst_target", "alert_level"
]

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--full", action="store_true", help="重新拉取基本面和SEC公告")
    return p.parse_args()

# ── 数据拉取 ───────────────────────────────────────────────────────────────────
def fetch(symbol):
    df = yf.download(symbol, period=f"{LOOKBACK_DAYS}d", auto_adjust=True,
                     progress=False, multi_level_index=False)
    return df.dropna()

# ── 技术指标 ───────────────────────────────────────────────────────────────────
def calc_rsi(closes, period=14):
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
    rs = ag / al.where(al != 0, np.nan)
    return float((100 - 100 / (1 + rs)).iloc[-1])

def calc_macd(closes, fast=12, slow=26, signal=9):
    ml = closes.ewm(span=fast, adjust=False).mean() - closes.ewm(span=slow, adjust=False).mean()
    sl = ml.ewm(span=signal, adjust=False).mean()
    h  = ml - sl
    return float(h.iloc[-1]), float(h.iloc[-2])

def calc_bb_z(closes, period=20):
    w   = closes.iloc[-period:]
    std = w.std()
    return float((closes.iloc[-1] - w.mean()) / std) if std else 0.0

def calc_drawdown_52w(closes):
    """当前价格相对过去252个交易日最高价的回撤百分比"""
    if len(closes) < 2:
        return 0.0
    lookback = min(252, len(closes) - 1)
    high = closes.iloc[-lookback:-1].max()
    return float((closes.iloc[-1] - high) / high * 100)

# ── 技术评分规则 ────────────────────────────────────────────────────────────────
def score_drawdown_52w(pct):
    """满分 15"""
    if pct <= -50: return 15
    if pct <= -30: return 10
    if pct <= -15: return 5
    return 0

def score_rsi(r):
    """满分 15"""
    if r <= 30: return 15
    if r <= 35: return 10
    if r <= 45: return 5
    return 0

def score_macd(prev, now):
    """满分 10。prev=前日柱，now=今日柱"""
    if prev < 0 and now > 0: return 10   # 金叉
    if now < 0 and now > prev: return 5  # 底部收窄
    return 0

def score_bb(z):
    """满分 10"""
    if z < -2.0: return 10
    if z < -1.5: return 5
    return 0

def calc_tech_score(s_dd, s_rsi, s_macd, s_bb):
    return s_dd + s_rsi + s_macd + s_bb  # 满分 50
