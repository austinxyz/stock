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
    import time
    for attempt in range(3):
        df = yf.download(symbol, period=f"{LOOKBACK_DAYS}d", auto_adjust=True,
                         progress=False, multi_level_index=False)
        df = df.dropna()
        if not df.empty:
            return df
        if attempt < 2:
            time.sleep(3)
    return df

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

# ── HTML 报告 ──────────────────────────────────────────────────────────────────
def _score_color(score: int, max_score: int) -> str:
    pct = score / max_score if max_score else 0
    if pct >= 0.7: return "#16a34a"
    if pct >= 0.4: return "#ca8a04"
    return "#9ca3af"

def _bar(score: int, max_score: int) -> str:
    color = _score_color(score, max_score)
    pct   = min(100, int(score / max_score * 100)) if max_score else 0
    return (
        f'<div style="background:#e5e7eb;border-radius:99px;height:8px;width:100%;margin-top:6px">'
        f'<div style="width:{pct}%;height:8px;border-radius:99px;background:{color}"></div></div>'
    )

def _rule_table(rows: list, active_idx: int) -> str:
    html = '<table style="width:100%;border-collapse:collapse;margin-top:8px;font-size:12px">'
    for i, (label, pts) in enumerate(rows):
        bg = "background:#dcfce7;" if i == active_idx else ""
        html += (
            f'<tr style="{bg}">'
            f'<td style="padding:3px 6px;color:#374151">{label}</td>'
            f'<td style="padding:3px 6px;text-align:right;font-weight:600">{pts}</td></tr>'
        )
    return html + '</table>'

def _ind_card(title, value, score, max_score, why, rules, active_idx) -> str:
    color = _score_color(score, max_score)
    return (
        f'<div style="background:#fff;border-radius:10px;padding:16px 20px;'
        f'box-shadow:0 1px 4px rgba(0,0,0,.08)">'
        f'<div style="font-size:12px;color:#6b7280;margin-bottom:4px">{title}</div>'
        f'<div style="font-size:22px;font-weight:700;color:{color}">{value}</div>'
        f'<div style="font-size:12px;color:#6b7280;margin-top:2px">评分 {score}/{max_score}</div>'
        f'{_bar(score, max_score)}'
        f'<div style="font-size:11px;color:#6b7280;margin-top:8px;line-height:1.5">{why}</div>'
        f'{_rule_table(rules, active_idx)}</div>'
    )

def generate_html(today: str, price: float, sr: dict,
                  tech_score: int, fund_score: int, total_score: int,
                  s_rsi: int, s_dist: int, s_bb: int, s_macd: int,
                  rsi_val: float, dist_pct: float, bb_z: float,
                  fund_data: dict,
                  s_upside: int, s_pe: int, s_revenue: int, s_rating: int,
                  sell_log: list):

    rows       = read_csv_rows()
    rows_desc  = sorted(rows, key=lambda r: r["date"], reverse=True)
    chart_rows = sorted(rows, key=lambda r: r["date"])[-60:]
    chart_labels = json.dumps([r["date"] for r in chart_rows])
    chart_tech   = json.dumps([int(r["tech_score"]) for r in chart_rows])
    chart_total  = json.dumps([int(r["total_score"]) for r in chart_rows])
    n = len(chart_rows)

    espp_value  = ESPP_SHARES * price
    rsu_value   = RSU_SHARES  * price
    total_value = espp_value + rsu_value
    total_gain  = ESPP_SHARES * (price - ESPP_AVG_COST) + RSU_SHARES * (price - RSU_AVG_COST)
    gain_color  = "#16a34a" if total_gain >= 0 else "#dc2626"

    total_sold       = calc_total_sold(sell_log)
    annual_remaining = calc_annual_remaining(sell_log)
    year_sold        = ANNUAL_BUDGET - annual_remaining
    progress_pct     = min(100, int(total_sold / SELL_TARGET * 100))
    year_pct         = min(100, int(year_sold / ANNUAL_BUDGET * 100))

    tc = "#dc2626" if total_score >= 70 else "#ca8a04" if total_score >= 50 else "#9ca3af"
    action_label, action_color = {
        "SELL": ("🔴 卖出", "#dc2626"),
        "WAIT": ("🟡 观望", "#ca8a04"),
        "HOLD": ("🟢 等待", "#16a34a"),
    }.get(sr["action"], (sr["action"], "#9ca3af"))

    # ── 卖出建议面板 ──
    if sr["action"] in ("SELL", "WAIT"):
        sell_panel = f'''<div style="background:#fff;border-radius:10px;padding:20px 24px;box-shadow:0 1px 4px rgba(0,0,0,.08);margin-bottom:24px">
  <div style="font-size:15px;font-weight:700;margin-bottom:12px">今日卖出建议</div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:16px">
    <div><div style="font-size:12px;color:#6b7280">操作</div><div style="font-size:20px;font-weight:700;color:{action_color}">{action_label}</div></div>
    <div><div style="font-size:12px;color:#6b7280">池子</div><div style="font-size:20px;font-weight:700">{sr["pool"]}</div></div>
    <div><div style="font-size:12px;color:#6b7280">建议股数</div><div style="font-size:20px;font-weight:700">{sr["shares"]} 股</div></div>
    <div><div style="font-size:12px;color:#6b7280">卖出金额</div><div style="font-size:20px;font-weight:700">${sr["proceeds"]:,.0f}</div></div>
    <div><div style="font-size:12px;color:#6b7280">预估税款 (32.1%)</div><div style="font-size:20px;font-weight:700;color:#dc2626">${sr["tax_estimate"]:,.0f}</div></div>
    <div><div style="font-size:12px;color:#6b7280">税后到手</div><div style="font-size:20px;font-weight:700;color:#16a34a">${sr["net_proceeds"]:,.0f}</div></div>
  </div>
  <div style="font-size:12px;color:#6b7280;margin-bottom:10px">{"，".join(sr["reasons"])}</div>
  <div style="font-size:12px;color:#374151;margin-bottom:4px">今年进度：已卖 ${year_sold:,.0f} / 预算 ${ANNUAL_BUDGET:,}</div>
  <div style="background:#e5e7eb;border-radius:99px;height:8px"><div style="width:{year_pct}%;height:8px;border-radius:99px;background:#2563eb"></div></div>
</div>'''
    else:
        sell_panel = f'''<div style="background:#fff;border-radius:10px;padding:20px 24px;box-shadow:0 1px 4px rgba(0,0,0,.08);margin-bottom:24px">
  <div style="font-size:15px;font-weight:700;margin-bottom:8px">今日卖出建议</div>
  <div style="font-size:18px;font-weight:700;color:{action_color}">{action_label} — 等待更好时机</div>
  <div style="font-size:12px;color:#6b7280;margin-top:8px">{"，".join(sr["reasons"])}</div>
  <div style="font-size:12px;color:#374151;margin:12px 0 4px">今年进度：已卖 ${year_sold:,.0f} / 预算 ${ANNUAL_BUDGET:,}</div>
  <div style="background:#e5e7eb;border-radius:99px;height:8px"><div style="width:{year_pct}%;height:8px;border-radius:99px;background:#2563eb"></div></div>
</div>'''

    # ── 技术指标卡片 ──
    rsi_active  = 0 if rsi_val >= 70 else 1 if rsi_val >= 60 else 2 if rsi_val >= 50 else 3
    dist_active = 0 if dist_pct >= -5 else 1 if dist_pct >= -15 else 2 if dist_pct >= -30 else 3
    bb_active   = 0 if bb_z > 2.0 else 1 if bb_z > 1.5 else 2
    macd_active = 0 if s_macd == 10 else 1 if s_macd == 5 else 2

    rsi_card = _ind_card("RSI(14)", f"{rsi_val:.1f}", s_rsi, 15,
        "RSI超过70为超买，短期价格偏高，是卖出的好时机。RSI越高说明近期涨势越急，回调风险越大。",
        [("≥70 超买", "15分"), ("≥60", "8分"), ("≥50", "3分"), ("<50", "0分")], rsi_active)

    dist_card = _ind_card("距52周高点", f"{dist_pct:+.1f}%", s_dist, 15,
        "价格越接近52周高点，说明股价处于高位，是锁定利润的好时机。在高点附近卖出可以最大化收益。",
        [("在5%内", "15分"), ("在15%内", "8分"), ("在30%内", "3分"), ("更远", "0分")], dist_active)

    bb_card = _ind_card("布林带 z-score", f"{bb_z:.2f}", s_bb, 10,
        "z-score超过2表示价格高于布林带上轨两倍标准差，处于统计意义上的高位，均值回归概率较高。",
        [(">2.0 上轨以上", "10分"), (">1.5", "5分"), ("≤1.5", "0分")], bb_active)

    macd_card = _ind_card("MACD 柱", f"评分 {s_macd}/10", s_macd, 10,
        "MACD柱由正转负或高位收窄，表示上涨动能减弱，是股价见顶的早期信号，适合提前卖出。",
        [("顶背离/零轴下穿", "10分"), ("中性（仍正）", "5分"), ("底部（负值）", "0分")], macd_active)

    # ── 基本面指标卡片 ──
    pe    = fund_data.get("pe_ratio")
    tgt   = fund_data.get("target_price")
    rgrow = fund_data.get("revenue_growth")
    rec   = fund_data.get("recommendation")
    upside_pct = ((tgt - price) / price * 100) if (tgt and price) else None

    up_active = 0 if s_upside == 15 else 1 if s_upside == 8 else 2 if s_upside == 3 else 3
    pe_active = 0 if s_pe == 15 else 1 if s_pe == 8 else 2 if s_pe == 3 else 3
    rg_active = 0 if s_revenue == 10 else 1 if s_revenue == 5 else 2
    ra_active = 0 if s_rating == 10 else 1 if s_rating == 5 else 2

    why_upside = (f"目标价上涨空间 {upside_pct:+.1f}%。空间越小说明股价已接近分析师合理估值，是卖出参考信号。"
                  if upside_pct is not None else "暂无分析师目标价数据。")
    up_card = _ind_card("分析师目标价", f"${tgt:.2f}" if tgt else "N/A", s_upside, 15,
        why_upside,
        [("<5% 接近目标", "15分"), ("<15%", "8分"), ("<30%", "3分"), ("≥30%", "0分")], up_active)

    pe_card = _ind_card("市盈率 P/E", f"{pe:.1f}" if pe else "N/A", s_pe, 15,
        "P/E越高说明市场对EBAY未来增长期望越高，估值越贵，下行风险越大，是卖出的参考信号。",
        [(">20 高估", "15分"), (">16", "8分"), (">12", "3分"), ("≤12", "0分")], pe_active)

    rg_pct_str = f"{rgrow*100:+.1f}%" if rgrow is not None else "N/A"
    rg_card = _ind_card("收入同比增速", rg_pct_str, s_revenue, 10,
        "收入负增长说明EBAY核心业务在萎缩，基本面走弱时应加快卖出节奏，降低持仓集中度风险。",
        [("负增长", "10分"), ("<5%", "5分"), ("≥5%", "0分")], rg_active)

    rec_str = f"{rec:.1f}" if rec is not None else "N/A"
    ra_card = _ind_card("分析师评级", rec_str, s_rating, 10,
        "评级均值越高（偏向持有/卖出），说明华尔街整体对EBAY前景偏谨慎，支持分批卖出。（1=强买→5=强卖）",
        [("≥3.5 偏卖出", "10分"), ("≥2.5 中性", "5分"), ("<2.5 偏买入", "0分")], ra_active)

    # ── 历史记录表 ──
    table_rows = ""
    for r in rows_desc[:60]:
        a_color = "#dc2626" if r["action"]=="SELL" else "#ca8a04" if r["action"]=="WAIT" else "#6b7280"
        table_rows += (
            f'<tr><td>{r["date"]}</td>'
            f'<td style="font-weight:600;color:{_score_color(int(r["total_score"]),100)}">{r["total_score"]}</td>'
            f'<td>{r["tech_score"]}</td><td>{r["fund_score"]}</td>'
            f'<td>${float(r["price"]):.2f}</td>'
            f'<td style="color:{a_color}">{r["action"]}</td>'
            f'<td>{r.get("pool","")}</td>'
            f'<td>{r.get("suggested_shares","")}</td>'
            f'<td>${float(r.get("tax_estimate") or 0):,.0f}</td></tr>'
        )

    html = f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8"><title>EBAY 持仓分析</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
body{{font-family:-apple-system,sans-serif;background:#f9fafb;margin:0;padding:24px;color:#111}}
h1{{font-size:22px;font-weight:700;margin-bottom:4px}}
.sub{{color:#6b7280;font-size:13px;margin-bottom:24px}}
.cards{{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:24px}}
.card{{background:#fff;border-radius:10px;padding:20px 24px;box-shadow:0 1px 4px rgba(0,0,0,.08);min-width:150px}}
.card .label{{font-size:12px;color:#6b7280;margin-bottom:6px}}
.card .val{{font-size:28px;font-weight:700}}
.section{{font-size:15px;font-weight:700;margin:20px 0 12px}}
.ind-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin-bottom:24px}}
.chart-box{{background:#fff;border-radius:10px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,.08);margin-bottom:24px}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,.08);overflow:hidden}}
th{{background:#f3f4f6;padding:10px 12px;text-align:left;font-size:12px;color:#374151}}
td{{padding:8px 12px;font-size:13px;border-top:1px solid #f3f4f6}}
</style></head><body>
<h1>EBAY 持仓分析</h1>
<div class="sub">更新时间：{today} &nbsp;·&nbsp; ESPP {ESPP_SHARES}股@${ESPP_AVG_COST} &nbsp;|&nbsp; RSU {RSU_SHARES}股@${RSU_AVG_COST}</div>

<div class="cards">
  <div class="card">
    <div class="label">卖出信号评分</div>
    <div class="val" style="color:{tc}">{total_score}<span style="font-size:14px;color:#9ca3af">/100</span></div>
    <div style="font-size:11px;color:#6b7280;margin-top:4px">技术 {tech_score}/50 · 基本面 {fund_score}/50</div>
  </div>
  <div class="card"><div class="label">EBAY 现价</div><div class="val">${price:.2f}</div></div>
  <div class="card">
    <div class="label">总持仓市值</div>
    <div class="val">${total_value:,.0f}</div>
    <div style="font-size:11px;color:{gain_color};margin-top:4px">{'+' if total_gain>=0 else ''}${total_gain:,.0f} 浮盈</div>
  </div>
  <div class="card">
    <div class="label">ESPP 市值</div>
    <div class="val">${espp_value:,.0f}</div>
    <div style="font-size:11px;color:#6b7280;margin-top:4px">{ESPP_SHARES}股 @ ${ESPP_AVG_COST}</div>
  </div>
  <div class="card">
    <div class="label">RSU 市值</div>
    <div class="val">${rsu_value:,.0f}</div>
    <div style="font-size:11px;color:#6b7280;margin-top:4px">{RSU_SHARES}股 @ ${RSU_AVG_COST}</div>
  </div>
  <div class="card">
    <div class="label">3年目标进度</div>
    <div class="val">{progress_pct}%</div>
    <div style="font-size:11px;color:#6b7280;margin-top:4px">${total_sold:,.0f} / ${SELL_TARGET:,}</div>
  </div>
</div>

{sell_panel}

<div class="section">技术指标详情</div>
<div class="ind-grid">{rsi_card}{dist_card}{bb_card}{macd_card}</div>

<div class="section">基本面详情</div>
<div class="ind-grid">{up_card}{pe_card}{rg_card}{ra_card}</div>

<div class="chart-box">
  <div style="font-size:15px;font-weight:700;margin-bottom:12px">历史评分走势（高分=好卖点）</div>
  <canvas id="scoreChart" height="80"></canvas>
</div>

<div class="section">历史记录</div>
<table><thead><tr>
  <th>日期</th><th>总分</th><th>技术分</th><th>基本面分</th><th>价格</th>
  <th>建议</th><th>池子</th><th>股数</th><th>预估税款</th>
</tr></thead><tbody>{table_rows}</tbody></table>

<script>
new Chart(document.getElementById('scoreChart'),{{
  type:'line',
  data:{{labels:{chart_labels},datasets:[
    {{label:'综合评分',data:{chart_total},borderColor:'#dc2626',backgroundColor:'rgba(220,38,38,0.08)',fill:true,tension:0.3,pointRadius:2,borderWidth:2}},
    {{label:'技术评分',data:{chart_tech},borderColor:'#2563eb',tension:0.3,pointRadius:2,borderWidth:1.5,borderDash:[]}},
    {{label:'卖出阈值(70)',data:Array({n}).fill(70),borderColor:'#9ca3af',borderDash:[6,4],pointRadius:0,borderWidth:1}}
  ]}},
  options:{{responsive:true,plugins:{{legend:{{position:'top'}}}},scales:{{y:{{min:0,max:100}},x:{{ticks:{{maxTicksLimit:10}}}}}}}}
}})
</script></body></html>"""

    tmp = HTML_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(html)
    os.replace(tmp, HTML_FILE)

# ── 主程序 ─────────────────────────────────────────────────────────────────────
def main():
    print("\n正在拉取 EBAY 价格数据...")
    try:
        df = fetch(SYMBOL)
        if df.empty:
            print("错误：无法获取价格数据")
            sys.exit(1)
    except Exception as e:
        print(f"错误：{e}")
        sys.exit(1)

    closes   = df["Close"].squeeze()
    today    = str(df.index[-1].date())
    price    = float(closes.iloc[-1])

    # 技术指标
    rsi_val       = calc_rsi(closes)
    h_now, h_prev = calc_macd(closes)
    bb_z          = calc_bb_z(closes)
    dist_pct      = calc_distance_52w_high(closes)

    # 技术评分
    s_rsi  = score_rsi_sell(rsi_val)
    s_dist = score_distance_52w_high(dist_pct)
    s_bb   = score_bb_sell(bb_z)
    s_macd = score_macd_sell(h_prev, h_now)
    tech_score = calc_tech_score(s_rsi, s_dist, s_bb, s_macd)

    # 基本面（读缓存，不重新拉取）
    fund_data = load_fundamental_cache()
    if not fund_data:
        print("  基本面缓存不存在，正在拉取...")
        fund_data = fetch_fundamentals()
        save_fundamental_cache(fund_data)

    pe_ratio     = fund_data.get("pe_ratio") or 0.0
    target_price = fund_data.get("target_price") or 0.0
    rev_growth   = fund_data.get("revenue_growth") or 0.0
    rec_mean     = fund_data.get("recommendation") or 3.0

    s_upside  = score_analyst_upside(target_price, price)
    s_pe      = score_pe(pe_ratio)
    s_revenue = score_revenue_growth(rev_growth)
    s_rating  = score_analyst_rating(rec_mean)
    fund_score = calc_fund_score(s_upside, s_pe, s_revenue, s_rating)

    total_score = tech_score + fund_score

    # 卖出记录
    init_sell_log()
    sell_log         = read_sell_log()
    annual_remaining = calc_annual_remaining(sell_log)

    # 卖出建议
    sr = determine_sell_strategy(
        total_score      = total_score,
        rsu_shares       = RSU_SHARES,
        espp_shares      = ESPP_SHARES,
        price            = price,
        rsu_avg_cost     = RSU_AVG_COST,
        espp_avg_cost    = ESPP_AVG_COST,
        tax_rate         = TAX_RATE_LTCG,
        annual_remaining = annual_remaining,
    )

    # 控制台输出
    SEP = "─" * 56
    action_icon = {"SELL": "🔴 卖出", "WAIT": "🟡 观望", "HOLD": "🟢 等待"}.get(sr["action"], sr["action"])
    print(f"\n{SEP}")
    print(f"  EBAY 持仓分析  |  {today}")
    print(SEP)
    total_value = (ESPP_SHARES + RSU_SHARES) * price
    print(f"  现价 ${price:.2f}  |  持仓市值 ${total_value:,.0f}")
    print(f"  ESPP {ESPP_SHARES}股@${ESPP_AVG_COST}  |  RSU {RSU_SHARES}股@${RSU_AVG_COST}")
    print(SEP)
    print(f"  技术评分 {tech_score:>3}/50  |  基本面 {fund_score:>3}/50  |  综合 {total_score:>3}/100")
    print(SEP)
    print(f"  建议: {action_icon}")
    if sr["action"] in ("SELL", "WAIT"):
        print(f"  卖出 {sr['pool']} {sr['shares']}股 | 税款 ~${sr['tax_estimate']:,.0f} | 税后 ${sr['net_proceeds']:,.0f}")
    year_sold = ANNUAL_BUDGET - annual_remaining
    print(f"  今年进度: ${year_sold:,.0f} / ${ANNUAL_BUDGET:,}  剩余: ${annual_remaining:,.0f}")
    print(SEP)

    # 保存 CSV
    row = {
        "date":            today,
        "price":           f"{price:.2f}",
        "tech_score":      tech_score,
        "fund_score":      fund_score,
        "total_score":     total_score,
        "rsi_score":       s_rsi,
        "dist_score":      s_dist,
        "bb_score":        s_bb,
        "macd_score":      s_macd,
        "rsi_val":         f"{rsi_val:.2f}",
        "dist_pct":        f"{dist_pct:.2f}",
        "bb_z":            f"{bb_z:.3f}",
        "action":          sr["action"],
        "pool":            sr["pool"] or "",
        "suggested_shares": sr["shares"],
        "tax_estimate":    f"{sr['tax_estimate']:.2f}",
        "net_proceeds":    f"{sr['net_proceeds']:.2f}",
    }
    save_csv(row)

    generate_html(today, price, sr, tech_score, fund_score, total_score,
                  s_rsi, s_dist, s_bb, s_macd, rsi_val, dist_pct, bb_z,
                  fund_data, s_upside, s_pe, s_revenue, s_rating, sell_log)

    print(f"\n  已保存 → {CSV_FILE}")
    print(f"  报告   → {HTML_FILE}\n")

if __name__ == "__main__":
    main()
