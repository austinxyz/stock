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
    last_al = float(al.iloc[-1])
    if last_al == 0:
        return 100.0
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
    if h_prev >= 0 and h_now >= 0:    return 5   # sustained positive, not shrinking
    return 0                                       # negative or bullish cross

def calc_tech_score(s_rsi: int, s_dist: int, s_bb: int, s_macd: int) -> int:
    return s_rsi + s_dist + s_bb + s_macd

# ── 基本面评分（高分 = 高估或基本面走弱 = 好卖点） ──────────────────────────────
def score_analyst_upside(target_price: float, current_price: float) -> int:
    """Analyst target price upside. High score = high overvaluation = good sell signal."""
    if target_price <= 0 or current_price <= 0:
        return 0
    upside = (target_price - current_price) / current_price
    if upside < 0.05:  return 15
    if upside < 0.15:  return 8
    if upside < 0.30:  return 3
    return 0

def score_pe(pe_ratio: float) -> int:
    """P/E ratio scoring. High PE = high valuation = good sell signal."""
    if pe_ratio <= 0: return 0
    if pe_ratio > 20: return 15
    if pe_ratio > 16: return 8
    if pe_ratio > 12: return 3
    return 0

def score_revenue_growth(growth_rate: float) -> int:
    """Revenue growth rate scoring. Declining or slow growth = good sell signal."""
    if growth_rate < 0:    return 10
    if growth_rate < 0.05: return 5
    return 0

def score_analyst_rating(recommendation_mean: float) -> int:
    """yfinance recommendationMean: 1=强买 → 5=强卖。值越高越悲观，越适合卖出。"""
    if recommendation_mean >= 3.5: return 10
    if recommendation_mean >= 2.5: return 5
    return 0

def calc_fund_score(s_upside: int, s_pe: int, s_revenue: int, s_rating: int) -> int:
    """Calculate total fundamental score."""
    return s_upside + s_pe + s_revenue + s_rating

# ── 卖出策略 ───────────────────────────────────────────────────────────────────
def determine_sell_strategy(
    total_score: int,
    rsu_shares: float,
    espp_shares: float,
    price: float,
    rsu_avg_cost: float,
    espp_avg_cost: float,
    tax_rate: float,
    annual_remaining: float,
) -> dict:
    """
    Returns dict:
      action: "SELL" | "WAIT" | "HOLD"
      pool:   "RSU" | "ESPP" | None
      shares: int
      proceeds, capital_gain, tax_estimate, net_proceeds: float
      reasons: list[str]
    """
    reasons = []

    if annual_remaining <= 0:
        reasons.append("今年年度卖出预算已用完")
        return {"action": "HOLD", "pool": None, "shares": 0,
                "proceeds": 0.0, "capital_gain": 0.0,
                "tax_estimate": 0.0, "net_proceeds": 0.0, "reasons": reasons}

    if total_score >= 70:
        action = "SELL"
        ratio  = 0.20
        reasons.append(f"综合评分 {total_score}/100，技术面卖出信号强")
    elif total_score >= 50:
        action = "WAIT"
        ratio  = 0.10
        reasons.append(f"综合评分 {total_score}/100，信号一般，可小量卖出")
    else:
        reasons.append(f"综合评分 {total_score}/100，价格可能仍有上涨空间")
        return {"action": "HOLD", "pool": None, "shares": 0,
                "proceeds": 0.0, "capital_gain": 0.0,
                "tax_estimate": 0.0, "net_proceeds": 0.0, "reasons": reasons}

    # 优先卖 RSU（资本利得低，税负小）
    if rsu_shares > 0:
        pool     = "RSU"
        avg_cost = rsu_avg_cost
        available = rsu_shares
        reasons.append(
            f"优先卖 RSU：每股资本利得 ${price - rsu_avg_cost:.2f}"
            f"（低于 ESPP 的 ${price - espp_avg_cost:.2f}）"
        )
    else:
        pool     = "ESPP"
        avg_cost = espp_avg_cost
        available = espp_shares
        reasons.append("RSU 已清空，卖出 ESPP")

    shares = min(int(annual_remaining * ratio / price), int(available))

    if shares <= 0:
        reasons.append("可用股数不足")
        return {"action": "HOLD", "pool": None, "shares": 0,
                "proceeds": 0.0, "capital_gain": 0.0,
                "tax_estimate": 0.0, "net_proceeds": 0.0, "reasons": reasons}

    proceeds     = shares * price
    capital_gain = shares * (price - avg_cost)
    tax_estimate = max(0.0, capital_gain * tax_rate)
    net_proceeds = proceeds - tax_estimate

    return {
        "action":       action,
        "pool":         pool,
        "shares":       shares,
        "proceeds":     proceeds,
        "capital_gain": capital_gain,
        "tax_estimate": tax_estimate,
        "net_proceeds": net_proceeds,
        "reasons":      reasons,
    }

# ── 基本面数据 ─────────────────────────────────────────────────────────────────
def fetch_fundamentals() -> dict:
    info = yf.Ticker(SYMBOL).info
    return {
        "pe_ratio":       info.get("trailingPE"),
        "target_price":   info.get("targetMeanPrice"),
        "revenue_growth": info.get("revenueGrowth"),
        "recommendation": info.get("recommendationMean"),
        "market_cap":     info.get("marketCap"),
        "trailing_eps":   info.get("trailingEps"),
        "dividend_yield": info.get("dividendYield"),
        "updated_at":     datetime.now().isoformat(),
    }

def load_fundamental_cache() -> dict:
    if not os.path.exists(FUND_FILE):
        return {}
    try:
        with open(FUND_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, KeyError):
        return {}

def save_fundamental_cache(data: dict):
    tmp = FUND_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, FUND_FILE)

# ── CSV (每日历史) ─────────────────────────────────────────────────────────────
def read_csv_rows() -> list:
    if not os.path.exists(CSV_FILE):
        return []
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def save_csv(row: dict):
    rows = [r for r in read_csv_rows() if r["date"] != row["date"]]
    rows.append(row)
    rows.sort(key=lambda r: r["date"])
    tmp = CSV_FILE + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, CSV_FILE)

# ── 卖出记录 ──────────────────────────────────────────────────────────────────
def init_sell_log():
    """创建卖出记录文件（只建表头，不覆盖已有数据）。"""
    if not os.path.exists(SELL_LOG_FILE):
        with open(SELL_LOG_FILE, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=SELL_LOG_FIELDS).writeheader()

def read_sell_log() -> list:
    if not os.path.exists(SELL_LOG_FILE):
        return []
    with open(SELL_LOG_FILE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def calc_annual_remaining(sell_log: list) -> float:
    year = str(datetime.now().year)
    year_proceeds = sum(float(r["proceeds"]) for r in sell_log
                        if r.get("date", "").startswith(year))
    return max(0.0, ANNUAL_BUDGET - year_proceeds)

def calc_total_sold(sell_log: list) -> float:
    return sum(float(r["proceeds"]) for r in sell_log)
