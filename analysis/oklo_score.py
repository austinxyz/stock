# -*- coding: utf-8 -*-
"""
OKLO 个股买入信号评分脚本
用法:
  python oklo_score.py          # 每日快跑（技术面 + 缓存基本面）
  python oklo_score.py --full   # 深度分析（重新拉取基本面 + SEC 公告）
"""

import sys, io, os, csv, json, argparse, html as html_lib
from datetime import datetime, timedelta
if sys.stdout and hasattr(sys.stdout, 'buffer') and __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import yfinance as yf
import pandas as pd
import numpy as np
import requests

# ── 用户参数 ────────────────────────────────────────────────────────────────────
SYMBOL         = "OKLO"
SHARES         = 122.48        # 2026-04-02 加仓后：101.022 + 21.458 股
AVG_COST       = 91.70         # 平均成本（2026-04-02 更新）
STOP_LOSS_PCT  = 0.70          # 最大亏损容忍（70%）
STOP_LOSS_PRICE = round(AVG_COST * (1 - STOP_LOSS_PCT), 2)  # $27.51
ADD_BUDGET     = 3_000         # 剩余加仓预算（已用 $2000）
LOOKBACK_DAYS  = 400

SCRIPT_DIR       = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR       = os.path.join(SCRIPT_DIR, "report")
os.makedirs(REPORT_DIR, exist_ok=True)
CSV_FILE         = os.path.join(REPORT_DIR, "oklo_history.csv")
HTML_FILE        = os.path.join(REPORT_DIR, "oklo_report.html")
FUNDAMENTAL_FILE = os.path.join(REPORT_DIR, "oklo_fundamental.json")

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

# ── 基本面数据（yfinance + SEC EDGAR）──────────────────────────────────────────
def fetch_fundamentals():
    """拉取基本面数据，返回 dict。失败时返回空 dict。"""
    info = {}
    try:
        ticker = yf.Ticker(SYMBOL)
        d = ticker.info
        total_cash = d.get("totalCash") or 0
        op_cf      = d.get("operatingCashflow") or 0
        if op_cf < 0:
            runway_months = (total_cash / abs(op_cf)) * 12
        else:
            runway_months = 999
        info = {
            "market_cap":         d.get("marketCap"),
            "total_cash":         total_cash,
            "operating_cf":       op_cf,
            "cash_runway_months": round(runway_months, 1),
            "analyst_target":     d.get("targetMeanPrice"),
            "total_revenue":      d.get("totalRevenue"),
            "updated_at":         datetime.now().strftime("%Y-%m-%d"),
        }
    except Exception as e:
        print(f"  [警告] 基本面数据拉取失败: {e}")
    return info

def fetch_sec_8k(cik="0001824920", count=10):
    """从 SEC EDGAR 拉取最近 N 条 8-K 公告。OKLO CIK: 0001824920"""
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    headers = {"User-Agent": "personal-stock-tracker admin@example.com"}
    filings = []
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        recent       = data.get("filings", {}).get("recent", {})
        forms        = recent.get("form", [])
        dates        = recent.get("filingDate", [])
        accessions   = recent.get("accessionNumber", [])
        descriptions = recent.get("primaryDocument", [])
        for i, form in enumerate(forms):
            if form == "8-K" and len(filings) < count:
                if not descriptions[i]:
                    continue
                acc = accessions[i].replace("-", "")
                filing_url = (f"https://www.sec.gov/Archives/edgar/data/"
                              f"{int(cik)}/{acc}/{descriptions[i]}")
                filings.append({
                    "date":  dates[i],
                    "title": f"8-K ({dates[i]})",
                    "url":   filing_url,
                })
    except Exception as e:
        print(f"  [警告] SEC EDGAR 拉取失败: {e}")
    return filings

def load_fundamental_cache():
    if not os.path.exists(FUNDAMENTAL_FILE):
        return {}, []
    try:
        with open(FUNDAMENTAL_FILE, encoding="utf-8") as f:
            cached = json.load(f)
        return cached.get("data", {}), cached.get("filings", [])
    except (json.JSONDecodeError, KeyError):
        print("  [警告] 基本面缓存文件损坏，将重新拉取")
        return {}, []

def save_fundamental_cache(fund_data, filings):
    tmp_path = FUNDAMENTAL_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump({"data": fund_data, "filings": filings}, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, FUNDAMENTAL_FILE)

# ── 基本面评分规则 ──────────────────────────────────────────────────────────────
def score_cash_runway(months):
    """满分 20"""
    if months is None: return 0
    if months > 24: return 20
    if months > 12: return 13
    if months > 6:  return 6
    return 0

def score_analyst_target(target, current_price):
    """满分 15"""
    if not target or not current_price: return 0
    upside = target / current_price
    if upside > 2.0: return 15
    if upside > 1.5: return 10
    if upside > 1.1: return 5
    return 0

def score_pipeline(days_since_last_filing):
    """满分 10"""
    if days_since_last_filing is None: return 0
    if days_since_last_filing <= 30: return 10
    if days_since_last_filing <= 90: return 5
    return 0

def score_thesis(has_negative_event):
    """满分 5"""
    return 0 if has_negative_event else 5

def calc_fund_score(s_runway, s_target, s_pipeline, s_thesis):
    return s_runway + s_target + s_pipeline + s_thesis  # 满分 50

def days_since_latest_8k(filings):
    if not filings:
        return None
    latest_date = datetime.strptime(filings[0]["date"], "%Y-%m-%d")
    return (datetime.now() - latest_date).days

# ── 策略逻辑 ───────────────────────────────────────────────────────────────────
def determine_strategy(price, tech_score, cash_runway, has_negative_event, add_budget):
    stop_reasons = []
    add_reasons  = []
    hold_reasons = []

    if price <= STOP_LOSS_PRICE:
        stop_reasons.append(f"现价低于止损线 ${STOP_LOSS_PRICE}（成本×30%）")
    if cash_runway is not None and cash_runway <= 6:
        stop_reasons.append(f"现金跑道仅剩 {cash_runway:.1f} 个月（<6个月硬止损）")
    if has_negative_event:
        stop_reasons.append("检测到重大负面事件（监管受阻或合同取消）")

    can_add = (
        price > STOP_LOSS_PRICE and
        tech_score >= 35 and
        (cash_runway is None or cash_runway > 12) and
        not has_negative_event
    )

    add_amount = 0.0
    if can_add:
        add_reasons.append(f"技术评分 {tech_score}/50 ≥ 35（超卖信号）")
        runway_str = f"{cash_runway:.0f}" if cash_runway is not None else "未知"
        add_reasons.append(f"现金跑道 {runway_str} 个月 > 12个月")
        add_reasons.append("无止损触发条件")
        if tech_score >= 45:
            add_amount = add_budget * 0.40
            add_reasons.append(f"技术分≥45，建议投入预算40%（${add_amount:,.0f}）")
        else:
            add_amount = add_budget * 0.20
            add_reasons.append(f"技术分35-44，建议投入预算20%（${add_amount:,.0f}）")
    else:
        if tech_score < 35:
            hold_reasons.append(f"技术评分 {tech_score}/50 < 35，信号不足")
        if cash_runway is not None and cash_runway <= 12:
            hold_reasons.append(f"现金跑道 {cash_runway:.0f} 个月，偏紧，不宜追加")

    if stop_reasons:
        strategy = "STOP_LOSS"
    elif can_add:
        strategy = "ADD"
    else:
        strategy = "HOLD"

    return {
        "strategy":   strategy,
        "add_amount": add_amount,
        "reasons": {"stop_loss": stop_reasons, "add": add_reasons, "hold": hold_reasons}
    }

# ── CSV 持久化 ──────────────────────────────────────────────────────────────────
def read_csv_rows():
    if not os.path.exists(CSV_FILE):
        return []
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def save_csv(row: dict):
    rows = read_csv_rows()
    rows = [r for r in rows if r["date"] != row["date"]]
    rows.append(row)
    tmp_path = CSV_FILE + ".tmp"
    with open(tmp_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp_path, CSV_FILE)

# ── HTML 报告 ──────────────────────────────────────────────────────────────────
def generate_html(today, price, pnl_pct, tech_score, fund_score, total_score,
                  s_dd, s_rsi, s_macd, s_bb, dd_pct, rsi_val, bb_z,
                  fund_data, filings, cash_runway, analyst_target, days_8k,
                  s_runway, s_target, s_pipeline, s_thesis,
                  strategy, add_amount, reasons):

    rows = read_csv_rows()
    rows_desc  = sorted(rows, key=lambda r: r["date"], reverse=True)
    chart_rows = sorted(rows, key=lambda r: r["date"])[-60:]
    chart_labels = json.dumps([r["date"] for r in chart_rows])
    chart_tech   = json.dumps([int(r["tech_score"]) for r in chart_rows])
    chart_total  = json.dumps([int(r["total_score"]) for r in chart_rows])

    market_value  = price * SHARES
    cost_value    = AVG_COST * SHARES
    pnl_dollars   = market_value - cost_value
    dist_stop_pct = (price - STOP_LOSS_PRICE) / STOP_LOSS_PRICE * 100
    pnl_color     = "#16a34a" if pnl_pct >= 0 else "#dc2626"
    stop_color    = "#16a34a" if price > STOP_LOSS_PRICE * 1.2 else ("#ca8a04" if price > STOP_LOSS_PRICE else "#dc2626")

    strategy_colors = {"STOP_LOSS": "#dc2626", "ADD": "#16a34a", "HOLD": "#ca8a04"}
    strategy_labels = {"STOP_LOSS": "止损", "ADD": "加仓", "HOLD": "持有"}

    def score_color(s, max_s):
        pct = s / max_s if max_s else 0
        if pct >= 0.8: return "#16a34a"
        if pct >= 0.6: return "#ca8a04"
        if pct >= 0.4: return "#2563eb"
        return "#9ca3af"

    def bar(score, max_score, color):
        pct = int(score / max_score * 100) if max_score else 0
        return (f'<div style="display:flex;align-items:center;gap:8px">'
                f'<div style="flex:1;background:#e5e7eb;border-radius:99px;height:6px">'
                f'<div style="width:{pct}%;height:6px;border-radius:99px;background:{color}"></div></div>'
                f'<span style="font-size:12px;color:#374151;min-width:40px">{score}/{max_score}</span></div>')

    def reasons_list(items, color):
        if not items:
            return '<span style="color:#9ca3af;font-size:12px">无触发条件</span>'
        return "".join(
            f'<div style="font-size:12px;color:{color};margin:2px 0">• {r}</div>'
            for r in items
        )

    tech_cards = [
        {"name": "52周回撤", "score": s_dd, "max": 15,
         "current": f"{dd_pct:+.1f}%", "color": "#4f46e5",
         "why": "股价距52周高点回撤越深，相对价值越高，超跌反弹概率越大。",
         "rules": [
             {"cond": "≤ -50%", "pts": 15, "active": dd_pct <= -50},
             {"cond": "≤ -30%", "pts": 10, "active": -50 < dd_pct <= -30},
             {"cond": "≤ -15%", "pts": 5,  "active": -30 < dd_pct <= -15},
             {"cond": "> -15%", "pts": 0,  "active": dd_pct > -15},
         ]},
        {"name": "RSI(14)", "score": s_rsi, "max": 15,
         "current": f"{rsi_val:.1f}", "color": "#0891b2",
         "why": "RSI < 30 为严重超卖，个股超卖比ETF更极端，反弹空间更大。",
         "rules": [
             {"cond": "≤ 30（严重超卖）", "pts": 15, "active": rsi_val <= 30},
             {"cond": "≤ 35",             "pts": 10, "active": 30 < rsi_val <= 35},
             {"cond": "≤ 45",             "pts": 5,  "active": 35 < rsi_val <= 45},
             {"cond": "> 45",             "pts": 0,  "active": rsi_val > 45},
         ]},
        {"name": "MACD 柱", "score": s_macd, "max": 10,
         "current": ("金叉" if s_macd == 10 else "底部收窄" if s_macd == 5 else "无信号"),
         "color": "#16a34a",
         "why": "MACD柱由负转正是趋势反转信号；负区收窄说明下跌动能减弱。",
         "rules": [
             {"cond": "负转正（金叉）", "pts": 10, "active": s_macd == 10},
             {"cond": "负区收窄",       "pts": 5,  "active": s_macd == 5},
             {"cond": "无信号",         "pts": 0,  "active": s_macd == 0},
         ]},
        {"name": "布林带 z-score", "score": s_bb, "max": 10,
         "current": f"z = {bb_z:.2f}", "color": "#ca8a04",
         "why": "z < -2 说明价格偏离20日均线2个标准差，均值回归概率高。",
         "rules": [
             {"cond": "z < -2.0", "pts": 10, "active": bb_z < -2.0},
             {"cond": "z < -1.5", "pts": 5,  "active": -2.0 <= bb_z < -1.5},
             {"cond": "z ≥ -1.5", "pts": 0,  "active": bb_z >= -1.5},
         ]},
    ]

    def tech_card_html(c):
        rules_html = "".join(
            f'<tr style="{"background:#f0fdf4;font-weight:600;" if r["active"] else ""}">'
            f'<td style="padding:3px 6px;color:#6b7280">{"✓ " if r["active"] else ""}{r["cond"]}</td>'
            f'<td style="padding:3px 6px;text-align:right">{r["pts"]}分</td></tr>'
            for r in c["rules"]
        )
        return f"""
        <div style="background:#fff;border-radius:10px;padding:18px 20px;box-shadow:0 1px 4px rgba(0,0,0,.08)">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px">
            <div>
              <div style="font-size:14px;font-weight:600">{c['name']}</div>
              <div style="font-size:12px;color:#6b7280">当前：<span style="font-weight:600;color:#374151">{c['current']}</span></div>
            </div>
            <div style="font-size:20px;font-weight:700;color:{c['color']}">{c['score']}<span style="font-size:11px;color:#9ca3af">/{c['max']}</span></div>
          </div>
          {bar(c['score'], c['max'], c['color'])}
          <div style="margin-top:10px;font-size:12px;color:#6b7280;background:#f9fafb;border-radius:6px;padding:6px 8px">
            <b style="color:#374151">为什么：</b>{c['why']}
          </div>
          <table style="width:100%;border-collapse:collapse;margin-top:6px;font-size:12px">{rules_html}</table>
        </div>"""

    tech_cards_html = "".join(tech_card_html(c) for c in tech_cards)

    fund_updated = fund_data.get("updated_at", "未知")
    runway_months_val = cash_runway or 0
    runway_color = "#16a34a" if runway_months_val > 12 else ("#ca8a04" if runway_months_val > 6 else "#dc2626")

    filings_html = "".join(
        f'<div style="padding:6px 0;border-bottom:1px solid #f3f4f6;font-size:12px">'
        f'<span style="color:#6b7280">{html_lib.escape(fl["date"])}</span>&nbsp;'
        f'<a href="{fl["url"] if fl["url"].startswith("https://") else "#"}" target="_blank" style="color:#4f46e5">{html_lib.escape(fl["title"])}</a></div>'
        for fl in filings[:8]
    ) or '<div style="font-size:12px;color:#9ca3af">无数据（运行 --full 获取）</div>'

    # 基本面指标卡片
    analyst_upside = (analyst_target / price) if (analyst_target and price) else None
    analyst_upside_str = f"{analyst_upside*100:.0f}%" if analyst_upside else "N/A"
    fund_cards = [
        {
            "name": "现金跑道",
            "score": s_runway, "max": 20,
            "current": f"{cash_runway:.0f} 个月" if cash_runway else "N/A",
            "color": runway_color,
            "why": "OKLO 是早期公司，尚未盈利。现金跑道决定公司能撑多久——跑道越长，就有越多时间推进项目、等待监管批准、实现首批合同收入，融资压力也越小。",
            "rules": [
                {"cond": "> 24 个月（充裕）",        "pts": 20, "active": runway_months_val > 24},
                {"cond": "> 12 个月（安全）",         "pts": 13, "active": 12 < runway_months_val <= 24},
                {"cond": "> 6 个月（偏紧）",          "pts": 6,  "active": 6 < runway_months_val <= 12},
                {"cond": "≤ 6 个月（危险，硬止损）",  "pts": 0,  "active": 0 < runway_months_val <= 6},
                {"cond": "无数据",                   "pts": 0,  "active": runway_months_val == 0},
            ]
        },
        {
            "name": "分析师目标价",
            "score": s_target, "max": 15,
            "current": f"${analyst_target:.2f}（上涨空间 {analyst_upside_str}）" if analyst_target else "N/A",
            "color": "#9333ea",
            "why": "华尔街分析师综合公司基本面、行业前景、估值模型给出目标价。目标价相对现价的上涨空间越大，说明市场专业机构认为当前股价越被低估，是买入信心的参考依据。",
            "rules": [
                {"cond": "目标价 > 现价 200%（强烈看多）", "pts": 15, "active": bool(analyst_upside and analyst_upside > 2.0)},
                {"cond": "目标价 > 现价 150%",            "pts": 10, "active": bool(analyst_upside and 1.5 < analyst_upside <= 2.0)},
                {"cond": "目标价 > 现价 110%",            "pts": 5,  "active": bool(analyst_upside and 1.1 < analyst_upside <= 1.5)},
                {"cond": "目标价 ≤ 现价 110% 或无数据",   "pts": 0,  "active": not analyst_upside or analyst_upside <= 1.1},
            ]
        },
        {
            "name": "营收 / 合同管道",
            "score": s_pipeline, "max": 10,
            "current": f"最新 8-K {days_8k} 天前" if days_8k is not None else "无数据",
            "color": "#0891b2",
            "why": "对 OKLO 这类早期核能公司，传统营收意义有限，更重要的是合同管道和业务进展。近期有 8-K 公告（LOI、合同签署、技术里程碑）说明公司业务在持续推进，论点在兑现。",
            "rules": [
                {"cond": "30 天内有新公告（活跃推进）",  "pts": 10, "active": days_8k is not None and days_8k <= 30},
                {"cond": "90 天内有公告（正常节奏）",    "pts": 5,  "active": days_8k is not None and 30 < days_8k <= 90},
                {"cond": "> 90 天无公告或无数据",        "pts": 0,  "active": days_8k is None or days_8k > 90},
            ]
        },
        {
            "name": "论点完整性",
            "score": s_thesis, "max": 5,
            "current": "无重大负面事件" if s_thesis == 5 else "检测到负面事件",
            "color": "#16a34a" if s_thesis == 5 else "#dc2626",
            "why": "你买入 OKLO 的核心逻辑是：AI 用电需求 → 核能必要 → OKLO SMR 受益。如果 NRC 拒绝关键许可、主要客户取消合同，核心逻辑可能已破坏，即使技术面再好也应重新评估持仓。",
            "rules": [
                {"cond": "无重大负面事件（监管通过、合同正常）", "pts": 5, "active": s_thesis == 5},
                {"cond": "有重大负面事件（监管受阻 / 合同取消）", "pts": 0, "active": s_thesis == 0},
            ]
        },
    ]

    fund_cards_html = "".join(tech_card_html(c) for c in fund_cards)

    def strategy_col(key, label, icon, color, rs):
        is_active = (strategy == key)
        bg = f"background:{color}10;border:2px solid {color};" if is_active else "background:#f9fafb;border:2px solid #e5e7eb;"
        badge = (f'<div style="font-size:11px;font-weight:600;background:{color};color:#fff;'
                 f'padding:2px 8px;border-radius:99px;display:inline-block;margin-bottom:8px">当前建议</div>'
                 if is_active else '')
        return (f'<div style="{bg}border-radius:10px;padding:18px;flex:1">'
                f'<div style="font-size:16px;font-weight:700;color:{color if is_active else "#9ca3af"};margin-bottom:8px">{icon} {label}</div>'
                f'{badge}{reasons_list(rs, color if is_active else "#6b7280")}</div>')

    strategy_html = (f'<div style="display:flex;gap:16px;flex-wrap:wrap">'
                     f'{strategy_col("STOP_LOSS","止损","🔴","#dc2626",reasons["stop_loss"])}'
                     f'{strategy_col("HOLD","持有","🟡","#ca8a04",reasons["hold"])}'
                     f'{strategy_col("ADD","加仓","🟢","#16a34a",reasons["add"])}'
                     f'</div>')

    # 加仓金额计算说明
    def add_row(label, ratio, amount, active):
        bg = 'background:#f0fdf4;font-weight:600;' if active else ''
        mark = '✓ ' if active else ''
        return (f'<tr style="{bg}"><td style="padding:6px 8px;border-top:1px solid #f3f4f6">{mark}{label}</td>'
                f'<td style="padding:6px 8px;text-align:center;border-top:1px solid #f3f4f6">{ratio}</td>'
                f'<td style="padding:6px 8px;text-align:right;border-top:1px solid #f3f4f6">${amount:,}</td></tr>')

    add_budget_html = f"""
    <div style="background:#fff;border-radius:10px;padding:20px 24px;box-shadow:0 1px 4px rgba(0,0,0,.08);margin-top:16px">
      <div style="font-size:14px;font-weight:600;margin-bottom:14px">加仓金额计算</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px">
        <div>
          <div style="font-size:12px;font-weight:600;color:#374151;margin-bottom:8px">预算状态</div>
          <table style="width:100%;border-collapse:collapse;font-size:13px">
            <tr><td style="padding:5px 0;color:#6b7280">加仓总预算</td><td style="text-align:right;font-weight:600">${ADD_BUDGET:,}</td></tr>
          </table>
          <div style="margin-top:12px;font-size:12px;color:#6b7280;background:#f9fafb;border-radius:6px;padding:8px 10px;line-height:1.7">
            <b style="color:#374151">逻辑：</b>技术面越超卖（分数越高），说明价格越便宜、买入性价比越高，应当投入更大比例。分批加仓而非一次全仓，是为了给更极端的低点留有余地。<br>
            <b style="color:#374151">计算：</b>加仓金额 = 加仓预算 × 技术评分对应比例
          </div>
        </div>
        <div>
          <div style="font-size:12px;font-weight:600;color:#374151;margin-bottom:8px">技术评分 → 加仓比例</div>
          <table style="width:100%;border-collapse:collapse;font-size:13px">
            <tr style="background:#f3f4f6"><th style="padding:6px 8px;text-align:left">技术评分</th><th style="padding:6px 8px;text-align:center">比例</th><th style="padding:6px 8px;text-align:right">本次金额</th></tr>
            {add_row("≥ 45（强烈超卖）", "40%", int(ADD_BUDGET * 0.40), tech_score >= 45)}
            {add_row("35 – 44（超卖）", "20%", int(ADD_BUDGET * 0.20), 35 <= tech_score < 45)}
            {add_row("< 35（信号不足）", "0%", 0, tech_score < 35)}
          </table>
        </div>
      </div>
    </div>"""

    def strat_badge(s):
        c = {"STOP_LOSS":"#dc2626","ADD":"#16a34a","HOLD":"#ca8a04"}.get(s,"#9ca3af")
        l = {"STOP_LOSS":"止损","ADD":"加仓","HOLD":"持有"}.get(s, s)
        return f'<span style="background:{c};color:#fff;padding:1px 7px;border-radius:4px;font-size:11px">{l}</span>'

    table_rows_html = "".join(
        f"<tr><td>{r['date']}</td>"
        f"<td style='font-weight:600;color:{score_color(int(r['total_score']),100)}'>{r['total_score']}</td>"
        f"<td>{r['tech_score']}</td><td>{r['fund_score']}</td>"
        f"<td>${float(r['price']):.2f}</td>"
        f"<td>{strat_badge(r['strategy'])}</td></tr>"
        for r in rows_desc
    )

    add_badge = (f'<div style="font-size:12px;color:#16a34a;margin-top:4px">建议加仓 ${add_amount:,.0f}</div>'
                 if strategy == "ADD" else '')

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>OKLO 持仓分析</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
  body{{font-family:-apple-system,sans-serif;background:#f9fafb;margin:0;padding:24px;color:#111}}
  h1{{font-size:22px;font-weight:700;margin-bottom:4px}}
  .sub{{color:#6b7280;font-size:13px;margin-bottom:20px}}
  .cards{{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:20px}}
  .card{{background:#fff;border-radius:10px;padding:18px 22px;box-shadow:0 1px 4px rgba(0,0,0,.08);min-width:140px}}
  .card .label{{font-size:11px;color:#6b7280;margin-bottom:4px}}
  .card .val{{font-size:26px;font-weight:700}}
  .section{{font-size:15px;font-weight:600;margin:20px 0 10px}}
  .ind-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px;margin-bottom:20px}}
  .chart-box{{background:#fff;border-radius:10px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,.08);margin-bottom:20px}}
  table{{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,.08);overflow:hidden}}
  th{{background:#f3f4f6;padding:9px 12px;text-align:left;font-size:12px;color:#374151}}
  td{{padding:8px 12px;font-size:13px;border-top:1px solid #f3f4f6}}
  tr:hover td{{background:#fafafa}}
</style>
</head>
<body>
<h1>OKLO 持仓分析</h1>
<div class="sub">更新时间：{today} &nbsp;·&nbsp; {SHARES}股 @ 成本 ${AVG_COST}</div>

<div class="cards">
  <div class="card">
    <div class="label">综合评分</div>
    <div class="val" style="color:{score_color(total_score,100)}">{total_score}<span style="font-size:14px;color:#9ca3af">/100</span></div>
    <div style="font-size:11px;color:#6b7280;margin-top:4px">技术 {tech_score}/50 · 基本面 {fund_score}/50</div>
  </div>
  <div class="card">
    <div class="label">现价</div>
    <div class="val">${price:.2f}</div>
  </div>
  <div class="card">
    <div class="label">总投入</div>
    <div class="val">${cost_value:,.0f}</div>
    <div style="font-size:11px;color:#6b7280;margin-top:4px">{SHARES:.2f} 股</div>
  </div>
  <div class="card">
    <div class="label">每股成本</div>
    <div class="val">${AVG_COST:.2f}</div>
  </div>
  <div class="card">
    <div class="label">持仓浮亏/盈</div>
    <div class="val" style="color:{pnl_color}">{"▲" if pnl_pct>=0 else "▼"}{abs(pnl_pct):.1f}%</div>
    <div style="font-size:11px;color:{pnl_color}">${pnl_dollars:+,.0f}</div>
  </div>
  <div class="card">
    <div class="label">止损线</div>
    <div class="val" style="color:{stop_color}">${STOP_LOSS_PRICE}</div>
    <div style="font-size:11px;color:{stop_color}">距离 {dist_stop_pct:+.1f}%</div>
  </div>
  <div class="card">
    <div class="label">策略建议</div>
    <div style="margin-top:10px;font-size:18px;font-weight:700;color:{strategy_colors.get(strategy,'#9ca3af')}">{strategy_labels.get(strategy,strategy)}</div>
    {add_badge}
  </div>
  <div class="card">
    <div class="label">现金跑道</div>
    <div class="val" style="color:{runway_color}">{f'{cash_runway:.0f}月' if cash_runway else 'N/A'}</div>
  </div>
</div>

<div class="section">策略建议详情</div>
{strategy_html}
{add_budget_html}

<div class="section">技术指标详情</div>
<div class="ind-grid">{tech_cards_html}</div>

<div class="section">基本面详情 <span style="font-size:12px;font-weight:400;color:#9ca3af">（上次更新：{fund_updated} · 运行 --full 刷新）</span></div>
<div class="ind-grid" style="margin-bottom:16px">{fund_cards_html}</div>

<div style="background:#fff;border-radius:10px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,.08);margin-bottom:20px;display:grid;grid-template-columns:1fr 1fr;gap:20px">
  <div>
    <div style="font-size:13px;font-weight:600;margin-bottom:10px">原始财务数据</div>
    <table style="box-shadow:none">
      <tr><td style="color:#6b7280;border:none;padding:5px 0">总现金</td><td style="font-weight:600;border:none;padding:5px 0">{f'${fund_data.get("total_cash",0)/1e6:.0f}M' if fund_data.get("total_cash") else 'N/A'}</td></tr>
      <tr><td style="color:#6b7280;padding:5px 0">经营现金流</td><td style="font-weight:600;padding:5px 0">{f'${fund_data.get("operating_cf",0)/1e6:.0f}M' if fund_data.get("operating_cf") else 'N/A'}</td></tr>
      <tr><td style="color:#6b7280;padding:5px 0">市值</td><td style="font-weight:600;padding:5px 0">{f'${fund_data.get("market_cap",0)/1e9:.1f}B' if fund_data.get("market_cap") else 'N/A'}</td></tr>
      <tr><td style="color:#6b7280;padding:5px 0">总收入</td><td style="font-weight:600;padding:5px 0">{f'${fund_data.get("total_revenue",0)/1e6:.0f}M' if fund_data.get("total_revenue") else 'N/A'}</td></tr>
    </table>
  </div>
  <div>
    <div style="font-size:13px;font-weight:600;margin-bottom:10px">近期 SEC 8-K 公告</div>
    {filings_html}
  </div>
</div>

<div class="chart-box">
  <div style="font-size:14px;font-weight:600;margin-bottom:12px">历史评分走势</div>
  <canvas id="scoreChart" height="80"></canvas>
</div>

<div class="section">历史记录</div>
<table>
<thead><tr><th>日期</th><th>总分</th><th>技术分</th><th>基本面分</th><th>价格</th><th>策略</th></tr></thead>
<tbody>{table_rows_html}</tbody>
</table>

<script>
new Chart(document.getElementById('scoreChart'), {{
  type: 'line',
  data: {{
    labels: {chart_labels},
    datasets: [
      {{label:'综合评分',data:{chart_total},borderColor:'#4f46e5',backgroundColor:'rgba(79,70,229,0.08)',fill:true,tension:0.3,pointRadius:3,borderWidth:2}},
      {{label:'技术评分',data:{chart_tech},borderColor:'#0891b2',backgroundColor:'transparent',tension:0.3,pointRadius:2,borderWidth:1.5,borderDash:[4,3]}},
      {{label:'买入门槛(总分60)',data:Array({len(chart_rows)}).fill(60),borderColor:'#9ca3af',pointRadius:0,borderWidth:1,borderDash:[6,4]}}
    ]
  }},
  options:{{responsive:true,plugins:{{legend:{{position:'top'}}}},scales:{{y:{{min:0,max:100}},x:{{ticks:{{maxTicksLimit:10}}}}}}}}
}})
</script>
</body></html>"""

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)

# ── 主程序 ─────────────────────────────────────────────────────────────────────
def main():
    args = parse_args()
    print("\n正在拉取价格数据...")
    try:
        df = fetch(SYMBOL)
        if df.empty:
            raise ValueError("yfinance 返回空数据，请检查 symbol 或网络连接")
        closes = df['Close'].squeeze()
        price  = float(closes.iloc[-1])
        today  = str(df.index[-1].date())
    except Exception as e:
        print(f"[错误] 价格数据拉取失败：{e}")
        sys.exit(1)
    pnl_pct = (price - AVG_COST) / AVG_COST * 100

    # 技术指标
    dd_pct        = calc_drawdown_52w(closes)
    rsi_val       = calc_rsi(closes)
    h_now, h_prev = calc_macd(closes)
    bb_z          = calc_bb_z(closes)

    # 技术评分
    s_dd   = score_drawdown_52w(dd_pct)
    s_rsi  = score_rsi(rsi_val)
    s_macd = score_macd(h_prev, h_now)
    s_bb   = score_bb(bb_z)
    tech_score = calc_tech_score(s_dd, s_rsi, s_macd, s_bb)

    # 基本面
    if args.full:
        print("正在拉取基本面数据（--full 模式）...")
        fund_data = fetch_fundamentals()
        filings   = fetch_sec_8k()
        save_fundamental_cache(fund_data, filings)
    else:
        fund_data, filings = load_fundamental_cache()
        if not fund_data:
            print("  [提示] 无基本面缓存，建议运行 --full 获取完整数据")

    cash_runway    = fund_data.get("cash_runway_months")
    analyst_target = fund_data.get("analyst_target")
    days_8k        = days_since_latest_8k(filings)

    # 基本面评分
    s_runway   = score_cash_runway(cash_runway or 0)
    s_target   = score_analyst_target(analyst_target, price)
    s_pipeline = score_pipeline(days_8k)
    # TODO: 负面事件检测尚未实现，当前固定为"无负面事件"（5分）
    # 未来可解析 SEC 8-K 标题关键词（"license denied", "contract terminated"）自动检测
    s_thesis = score_thesis(False)
    fund_score = calc_fund_score(s_runway, s_target, s_pipeline, s_thesis)

    total_score = tech_score + fund_score

    # 策略
    sr = determine_strategy(
        price=price,
        tech_score=tech_score,
        cash_runway=cash_runway,
        has_negative_event=(s_thesis == 0),
        add_budget=ADD_BUDGET
    )
    strategy   = sr["strategy"]
    add_amount = sr["add_amount"]
    reasons    = sr["reasons"]

    # 控制台输出
    SEP = "─" * 56
    arrow = "▲" if pnl_pct >= 0 else "▼"
    print(f"\n{SEP}")
    print(f"  OKLO 持仓分析  |  {today}")
    print(SEP)
    print(f"  现价 ${price:.2f}  |  成本 ${AVG_COST:.2f}  |  {arrow} {abs(pnl_pct):.1f}%")
    dist_stop = (price - STOP_LOSS_PRICE) / STOP_LOSS_PRICE * 100
    print(f"  止损线 ${STOP_LOSS_PRICE}  |  距止损 {dist_stop:+.1f}%")
    print(SEP)
    print(f"  技术评分 {tech_score:>3}/50  |  基本面 {fund_score:>3}/50  |  综合 {total_score:>3}/100")
    print(SEP)
    icons = {"STOP_LOSS": "🔴 止损", "ADD": "🟢 加仓", "HOLD": "🟡 持有"}
    print(f"  策略建议: {icons.get(strategy, strategy)}")
    if strategy == "ADD":
        print(f"  建议加仓金额: ${add_amount:,.0f}")
    print(SEP)

    # 保存 CSV
    alert = "RED" if strategy == "STOP_LOSS" else "NONE"
    row = {
        "date": today, "price": f"{price:.2f}",
        "tech_score": tech_score, "fund_score": fund_score, "total_score": total_score,
        "dd_score": s_dd, "rsi_score": s_rsi, "macd_score": s_macd, "bb_score": s_bb,
        "dd_pct": f"{dd_pct:.2f}", "rsi_val": f"{rsi_val:.2f}", "bb_z": f"{bb_z:.3f}",
        "strategy": strategy,
        "cash_runway_months": f"{cash_runway:.1f}" if cash_runway is not None else "",
        "analyst_target": f"{analyst_target:.2f}" if analyst_target else "",
        "alert_level": alert,
    }
    save_csv(row)
    generate_html(today, price, pnl_pct, tech_score, fund_score, total_score,
                  s_dd, s_rsi, s_macd, s_bb, dd_pct, rsi_val, bb_z,
                  fund_data, filings, cash_runway, analyst_target, days_8k,
                  s_runway, s_target, s_pipeline, s_thesis,
                  strategy, add_amount, reasons)

    print(f"\n  已保存 → {CSV_FILE}")
    print(f"  报告   → {HTML_FILE}\n")

if __name__ == "__main__":
    main()
