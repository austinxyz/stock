# -*- coding: utf-8 -*-
"""
KWEB 买入信号评分脚本
用法: py analysis/kweb_score.py
每日定时运行，结果追加到 kweb_history.csv，并更新 kweb_report.html
"""
import sys, io, os, csv, json, time
from datetime import datetime
if sys.stdout and hasattr(sys.stdout, 'buffer') and __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import yfinance as yf
import pandas as pd
import numpy as np

# ── 用户参数（每次加仓后手动更新） ──────────────────────────────────────────────
SYMBOL        = "KWEB"
MACRO_SYMBOL  = "FXI"
TOTAL_BUDGET  = 5_000    # 追加总预算 ($)
USED_BUDGET   = 0        # 已追加金额 ($)
AVG_COST      = 28.04    # 平均成本（每股）
TOTAL_SHARES  = 306.6    # 当前持仓股数
LOOKBACK_DAYS = 400

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR  = os.path.join(SCRIPT_DIR, "report")
os.makedirs(REPORT_DIR, exist_ok=True)
CSV_FILE    = os.path.join(REPORT_DIR, "kweb_history.csv")
HTML_FILE   = os.path.join(REPORT_DIR, "kweb_report.html")

CSV_FIELDS = [
    "date", "kweb_price", "fxi_price", "total_score",
    "tech_score", "macro_score",
    "dd_score", "rsi_score", "macd_score", "bb_score",
    "fxi_ma200_score", "fxi_momentum_score",
    "dd_pct", "rsi_val", "bb_z", "fxi_vs_ma200_pct", "fxi_momentum_pct",
    "suggested_amount", "alert_level", "buy_signal",
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

# ── 技术指标 ───────────────────────────────────────────────────────────────────
def calc_rsi(closes: pd.Series, period: int = 14) -> float:
    delta = closes.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)
    ag = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    al = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = ag / al.replace(0, np.nan)
    return float((100 - 100 / (1 + rs)).iloc[-1])

def calc_macd(closes: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ml  = closes.ewm(span=fast, adjust=False).mean() - closes.ewm(span=slow, adjust=False).mean()
    sl  = ml.ewm(span=signal, adjust=False).mean()
    h   = ml - sl
    return float(h.iloc[-1]), float(h.iloc[-2])

def calc_bb_z(closes: pd.Series, period: int = 20) -> float:
    w   = closes.iloc[-(period+1):-1]
    std = w.std()
    return float((closes.iloc[-1] - w.mean()) / std) if std else 0.0

def calc_drawdown(closes: pd.Series, lookback: int = 60) -> float:
    high = closes.iloc[-lookback:-1].max()
    return float((closes.iloc[-1] - high) / high * 100)

def calc_fxi_macro(fxi_df: pd.DataFrame):
    """Returns (fxi_vs_ma200_pct, fxi_momentum_pct)"""
    closes = fxi_df['Close']
    ma200  = float(closes.rolling(200).mean().iloc[-1])
    fxi_now = float(closes.iloc[-1])
    fxi_vs_ma200_pct = (fxi_now - ma200) / ma200 * 100
    fxi_20d_ago = float(closes.iloc[-21])
    fxi_momentum_pct = (fxi_now - fxi_20d_ago) / fxi_20d_ago * 100
    return fxi_vs_ma200_pct, fxi_momentum_pct

# ── 评分规则（技术分，满分75） ──────────────────────────────────────────────────
def score_drawdown(pct: float) -> int:
    if pct <= -20: return 25
    if pct <= -10: return 15
    return 5

def score_rsi(r: float) -> int:
    if r <= 30: return 20
    if r <= 40: return 12
    if r <= 50: return 4
    return 0

def score_macd(prev: float, now: float) -> int:
    if prev < 0 and now > 0: return 15
    if now < 0 and now > prev: return 8
    return 0

def score_bb(z: float) -> int:
    if z < -2.0: return 15
    if z < -1.5: return 8
    return 0

# ── 评分规则（宏观分，满分25） ──────────────────────────────────────────────────
def score_fxi_ma200(fxi_vs_ma200_pct: float) -> int:
    """fxi_vs_ma200_pct = (fxi_price - ma200) / ma200 * 100"""
    if fxi_vs_ma200_pct >= 0: return 15
    if fxi_vs_ma200_pct >= -5: return 8
    return 0

def score_fxi_momentum(momentum_pct: float) -> int:
    """momentum_pct = (fxi_now - fxi_20d_ago) / fxi_20d_ago * 100"""
    if momentum_pct >= 3: return 10
    if momentum_pct >= 0: return 5
    return 0
