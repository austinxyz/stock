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

# ── 换仓建议 ───────────────────────────────────────────────────────────────────
def determine_recommendation(fig_rank: int, fig_score: int) -> dict:
    """
    Returns dict:
      action: "HOLD" | "WATCH" | "SELL"
      reason: str
    """
    if fig_rank <= 2:
        return {
            "action": "HOLD",
            "reason": f"FIG 在同类中排名第 {fig_rank}，基本面相对强劲，继续持有。",
        }
    if fig_rank == 3 or fig_score >= 55:
        return {
            "action": "WATCH",
            "reason": f"FIG 排名第 {fig_rank}（评分 {fig_score}），持仓竞争力一般，保持关注。",
        }
    return {
        "action": "SELL",
        "reason": f"FIG 排名第 {fig_rank}（评分 {fig_score}/100），在同类中处于末位，建议换仓。",
    }

# ── 基本面数据拉取与缓存 ────────────────────────────────────────────────────────
def fetch_fundamentals_for(symbol: str) -> dict:
    try:
        info = yf.Ticker(symbol).info
        return {
            "revenue_growth": info.get("revenueGrowth"),
            "target_price":   info.get("targetMeanPrice"),
            "recommendation": info.get("recommendationMean"),
            "market_cap":     info.get("marketCap"),
            "updated_at":     datetime.now().isoformat(),
        }
    except Exception as e:
        print(f"  [警告] {symbol} 基本面拉取失败: {e}")
        return {}

def load_fundamental_cache() -> dict:
    if not os.path.exists(FUND_FILE):
        return {}
    try:
        with open(FUND_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}

def save_fundamental_cache(data: dict):
    tmp = FUND_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, FUND_FILE)

def is_cache_stale(cache: dict) -> bool:
    """Returns True if any symbol is missing or cache is older than FUND_CACHE_DAYS."""
    for symbol in ALL_SYMBOLS:
        if symbol not in cache:
            return True
    try:
        sample_updated = cache[ALL_SYMBOLS[0]].get("updated_at", "")
        updated = datetime.fromisoformat(sample_updated)
        return (datetime.now() - updated).days >= FUND_CACHE_DAYS
    except (ValueError, KeyError):
        return True

def get_fundamentals() -> dict:
    """Load cache; auto-refresh if stale."""
    cache = load_fundamental_cache()
    if is_cache_stale(cache):
        print("  正在刷新基本面缓存（7天自动刷新）...")
        for symbol in ALL_SYMBOLS:
            cache[symbol] = fetch_fundamentals_for(symbol)
            time.sleep(1)
        save_fundamental_cache(cache)
    return cache

# ── CSV 历史记录 ────────────────────────────────────────────────────────────────
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

# ── HTML 报告 ──────────────────────────────────────────────────────────────────
def _score_color(score: int, max_score: int) -> str:
    pct = score / max_score if max_score else 0
    if pct >= 0.7: return "#16a34a"
    if pct >= 0.4: return "#ca8a04"
    return "#dc2626"

def _bar(score: int, max_score: int) -> str:
    color = _score_color(score, max_score)
    pct   = min(100, int(score / max_score * 100)) if max_score else 0
    return (
        f'<div style="background:#e5e7eb;border-radius:99px;height:6px;margin-top:4px">'
        f'<div style="width:{pct}%;height:6px;border-radius:99px;background:{color}"></div></div>'
    )

def _medal(rank: int) -> str:
    return {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"#{rank}")

def generate_html(today: str, price: float, scores: list,
                  rec: dict, fund_cache: dict):
    """
    scores: list of dicts sorted by total_score desc, each with keys:
      symbol, total_score, tech_score, fund_score,
      rsi_val, ma200_val, dd_pct, rank
    """
    fig_data   = next(s for s in scores if s["symbol"] == SYMBOL)
    total_value = SHARES * price
    cost_basis  = SHARES * AVG_COST
    pnl         = total_value - cost_basis
    pnl_color   = "#16a34a" if pnl >= 0 else "#dc2626"

    action_color = {"HOLD": "#16a34a", "WATCH": "#ca8a04", "SELL": "#dc2626"}.get(rec["action"], "#9ca3af")
    action_icon  = {"HOLD": "🟢 继续持有", "WATCH": "🟡 保持关注", "SELL": "🔴 考虑换仓"}.get(rec["action"], rec["action"])

    # ── 排名总表 ──
    rank_rows = ""
    for s in scores:
        is_fig = s["symbol"] == SYMBOL
        bg     = "background:#fffbeb;" if is_fig else ""
        tc     = _score_color(s["total_score"], 100)
        rank_rows += (
            f'<tr style="{bg}">'
            f'<td style="font-weight:700">{_medal(s["rank"])}</td>'
            f'<td style="font-weight:{"800" if is_fig else "600"}">'
            f'{"▶ " if is_fig else ""}{s["symbol"]}</td>'
            f'<td style="font-weight:700;color:{tc}">{s["total_score"]}</td>'
            f'<td>{s["tech_score"]}</td>'
            f'<td>{s["fund_score"]}</td>'
            f'</tr>'
        )

    # ── 各股评分卡片 ──
    peer_cards = ""
    for s in scores:
        sym      = s["symbol"]
        is_fig   = sym == SYMBOL
        border   = "border:2px solid #f59e0b;" if is_fig else ""
        tc       = _score_color(s["total_score"], 100)
        fd       = fund_cache.get(sym, {})
        tgt      = fd.get("target_price")
        rec_val  = fd.get("recommendation")
        rgrow    = fd.get("revenue_growth")
        peer_cards += f'''<div style="background:#fff;border-radius:10px;padding:16px 20px;box-shadow:0 1px 4px rgba(0,0,0,.08);{border}">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
    <span style="font-size:16px;font-weight:800">{_medal(s["rank"])} {sym}</span>
    <span style="font-size:22px;font-weight:700;color:{tc}">{s["total_score"]}<span style="font-size:12px;color:#9ca3af">/100</span></span>
  </div>
  <div style="font-size:12px;color:#6b7280;margin-bottom:6px">技术 {s["tech_score"]}/40 · 基本面 {s["fund_score"]}/60</div>
  {_bar(s["total_score"], 100)}
  <div style="margin-top:10px;font-size:12px;color:#374151;display:grid;grid-template-columns:1fr 1fr;gap:4px">
    <div>RSI: {s["rsi_val"]:.1f}</div>
    <div>目标价: {"$"+str(round(tgt,2)) if tgt else "N/A"}</div>
    <div>回撤: {s["dd_pct"]:+.1f}%</div>
    <div>评级: {f"{rec_val:.1f}" if rec_val else "N/A"}</div>
    <div>vs 200MA: {"↑" if s["ma200_val"] and price > s["ma200_val"] else "↓"}</div>
    <div>增速: {f"{rgrow*100:+.1f}%" if rgrow else "N/A"}</div>
  </div>
</div>'''

    # ── 换仓建议面板 ──
    top_peer = next((s for s in scores if s["symbol"] != SYMBOL), None)
    if rec["action"] == "SELL" and top_peer:
        rotation_html = f'''<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:10px;padding:20px 24px;margin-bottom:24px">
  <div style="font-size:15px;font-weight:700;margin-bottom:10px">🔄 换仓建议</div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:12px">
    <div><div style="font-size:12px;color:#6b7280">卖出</div><div style="font-size:18px;font-weight:700;color:#dc2626">FIG × {SHARES}股</div></div>
    <div><div style="font-size:12px;color:#6b7280">预计金额</div><div style="font-size:18px;font-weight:700">${total_value:,.0f}</div></div>
    <div><div style="font-size:12px;color:#6b7280">买入</div><div style="font-size:18px;font-weight:700;color:#16a34a">{top_peer["symbol"]}</div></div>
    <div><div style="font-size:12px;color:#6b7280">税务</div><div style="font-size:18px;font-weight:700;color:#16a34a">$0（Roth IRA）</div></div>
  </div>
  <div style="font-size:12px;color:#6b7280">{rec["reason"]}</div>
</div>'''
    else:
        rotation_html = f'''<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;padding:16px 24px;margin-bottom:24px">
  <div style="font-size:16px;font-weight:700;color:{action_color}">{action_icon}</div>
  <div style="font-size:12px;color:#6b7280;margin-top:6px">{rec["reason"]}</div>
</div>'''

    # ── 历史走势图 ──
    rows       = read_csv_rows()
    chart_rows = sorted(rows, key=lambda r: r["date"])[-60:]
    chart_labels = json.dumps([r["date"] for r in chart_rows])
    chart_scores = json.dumps([int(r["total_score"]) for r in chart_rows])
    n = len(chart_rows)

    # ── 历史记录表 ──
    table_rows = ""
    for r in sorted(rows, key=lambda x: x["date"], reverse=True)[:30]:
        rc = _score_color(int(r["total_score"]), 100)
        ac = {"SELL": "#dc2626", "WATCH": "#ca8a04", "HOLD": "#16a34a"}.get(r["recommendation"], "#9ca3af")
        table_rows += (
            f'<tr><td>{r["date"]}</td>'
            f'<td style="font-weight:600;color:{rc}">{r["total_score"]}</td>'
            f'<td>{r["tech_score"]}</td><td>{r["fund_score"]}</td>'
            f'<td>${float(r["price"]):.2f}</td>'
            f'<td>#{r["rank"]}</td>'
            f'<td style="color:{ac}">{r["recommendation"]}</td></tr>'
        )

    html = f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8"><title>FIG 持仓分析</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
body{{font-family:-apple-system,sans-serif;background:#f9fafb;margin:0;padding:24px;color:#111}}
h1{{font-size:22px;font-weight:700;margin-bottom:4px}}
.sub{{color:#6b7280;font-size:13px;margin-bottom:24px}}
.cards{{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:24px}}
.card{{background:#fff;border-radius:10px;padding:20px 24px;box-shadow:0 1px 4px rgba(0,0,0,.08);min-width:140px}}
.card .label{{font-size:12px;color:#6b7280;margin-bottom:6px}}
.card .val{{font-size:28px;font-weight:700}}
.section{{font-size:15px;font-weight:700;margin:20px 0 12px}}
.peer-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin-bottom:24px}}
.chart-box{{background:#fff;border-radius:10px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,.08);margin-bottom:24px}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,.08);overflow:hidden;margin-bottom:24px}}
th{{background:#f3f4f6;padding:10px 12px;text-align:left;font-size:12px;color:#374151}}
td{{padding:8px 12px;font-size:13px;border-top:1px solid #f3f4f6}}
</style></head><body>
<h1>FIG (Figma) 持仓分析</h1>
<div class="sub">更新时间：{today} &nbsp;·&nbsp; {SHARES}股 @ ${AVG_COST} 成本 &nbsp;·&nbsp; 🏦 Roth IRA</div>

<div class="cards">
  <div class="card">
    <div class="label">持仓信心评分</div>
    <div class="val" style="color:{_score_color(fig_data['total_score'],100)}">{fig_data["total_score"]}<span style="font-size:14px;color:#9ca3af">/100</span></div>
    <div style="font-size:11px;color:#6b7280;margin-top:4px">同类排名 {_medal(fig_data["rank"])}</div>
  </div>
  <div class="card"><div class="label">FIG 现价</div><div class="val">${price:.2f}</div></div>
  <div class="card">
    <div class="label">持仓市值</div>
    <div class="val">${total_value:,.0f}</div>
    <div style="font-size:11px;color:{pnl_color};margin-top:4px">{'+' if pnl>=0 else ''}${pnl:,.0f} 浮{'盈' if pnl>=0 else '亏'}</div>
  </div>
  <div class="card">
    <div class="label">建议</div>
    <div class="val" style="font-size:20px;color:{action_color}">{action_icon}</div>
  </div>
</div>

{rotation_html}

<div class="section">同类横向排名</div>
<table><thead><tr>
  <th>排名</th><th>标的</th><th>总分</th><th>技术面</th><th>基本面</th>
</tr></thead><tbody>{rank_rows}</tbody></table>

<div class="section">各标的详情</div>
<div class="peer-grid">{peer_cards}</div>

<div class="chart-box">
  <div style="font-size:15px;font-weight:700;margin-bottom:12px">FIG 历史信心评分走势</div>
  <canvas id="scoreChart" height="80"></canvas>
</div>

<div class="section">历史记录</div>
<table><thead><tr>
  <th>日期</th><th>总分</th><th>技术</th><th>基本面</th><th>价格</th><th>排名</th><th>建议</th>
</tr></thead><tbody>{table_rows}</tbody></table>

<script>
new Chart(document.getElementById('scoreChart'),{{
  type:'line',
  data:{{labels:{chart_labels},datasets:[
    {{label:'FIG 信心评分',data:{chart_scores},borderColor:'#f59e0b',backgroundColor:'rgba(245,158,11,0.08)',fill:true,tension:0.3,pointRadius:2,borderWidth:2}},
    {{label:'换仓阈值(55)',data:Array({n}).fill(55),borderColor:'#dc2626',borderDash:[6,4],pointRadius:0,borderWidth:1}}
  ]}}}},
  options:{{responsive:true,plugins:{{legend:{{position:'top'}}}},scales:{{y:{{min:0,max:100}},x:{{ticks:{{maxTicksLimit:10}}}}}}}}
}})
</script></body></html>"""

    tmp = HTML_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(html)
    os.replace(tmp, HTML_FILE)
