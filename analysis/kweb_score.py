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
USED_BUDGET   = 3_000    # 已追加金额 ($)
AVG_COST      = 28.35    # 平均成本（2026-04-08 更新）
TOTAL_SHARES  = 409.069  # 当前持仓股数（2026-04-08 加仓后）
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

# ── 预警优先级 ────────────────────────────────────────────────────────────────
_ALERT_PRIORITY = {"RED": 3, "ORANGE": 2, "YELLOW": 1, "NONE": 0}

# ── 买入建议 ──────────────────────────────────────────────────────────────────
def suggested_amount(score: int, remaining: float) -> float:
    if score >= 80: return remaining * 0.50
    if score >= 60: return remaining * 0.35
    if score >= 40: return remaining * 0.15
    return 0.0

# ── 止损预警 ───────────────────────────────────────────────────────────────────
def check_alerts(pnl_pct: float | None, fxi_df: pd.DataFrame) -> list:
    alerts = []
    fxi_closes = fxi_df['Close']
    fxi_ma200  = fxi_closes.rolling(200).mean()
    if (fxi_closes < fxi_ma200).iloc[-10:].values.all():
        alerts.append(("RED", "FXI 跌破 MA200 已持续 10 日，停止买入"))
    if pnl_pct is not None:
        if pnl_pct < -35:
            alerts.append(("RED", f"浮亏 {pnl_pct:.1f}%，考虑减仓"))
        elif pnl_pct < -20:
            alerts.append(("ORANGE", f"浮亏 {pnl_pct:.1f}%，考虑减仓 50%"))
        elif pnl_pct < -12:
            alerts.append(("YELLOW", f"浮亏 {pnl_pct:.1f}%，暂停新买入"))
    return alerts

# ── CSV 读写 ───────────────────────────────────────────────────────────────────
def read_csv_rows() -> list:
    if not os.path.exists(CSV_FILE):
        return []
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def save_csv(row: dict):
    rows = read_csv_rows()
    rows = [r for r in rows if r["date"] != row["date"]]
    rows.append(row)
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        w.writerows(rows)

# ── HTML 报告 ──────────────────────────────────────────────────────────────────
def _score_color(s: int) -> str:
    if s >= 80: return "#16a34a"
    if s >= 60: return "#ca8a04"
    if s >= 40: return "#2563eb"
    return "#9ca3af"

def _alert_badge(level: str) -> str:
    colors = {"RED": "#dc2626", "ORANGE": "#ea580c", "YELLOW": "#ca8a04", "NONE": "#6b7280"}
    c = colors.get(level, "#6b7280")
    return f'<span style="background:{c};color:#fff;padding:2px 8px;border-radius:4px;font-size:12px">{level}</span>'

def _signal_badge(active: str) -> str:
    if active == "True":
        return '<span style="background:#16a34a;color:#fff;padding:2px 8px;border-radius:4px;font-size:12px">买入信号</span>'
    return '<span style="background:#9ca3af;color:#fff;padding:2px 8px;border-radius:4px;font-size:12px">等待中</span>'

def generate_html(today: dict):
    rows      = read_csv_rows()
    rows_desc = sorted(rows, key=lambda r: r["date"], reverse=True)
    chart_rows   = sorted(rows, key=lambda r: r["date"])[-60:]
    chart_labels = json.dumps([r["date"] for r in chart_rows])
    chart_scores = json.dumps([int(r["total_score"]) for r in chart_rows])

    t   = today
    ts  = int(t["total_score"])
    tc  = _score_color(ts)

    kweb_price_v     = float(t["kweb_price"])
    fxi_price_v      = float(t["fxi_price"])
    dd_pct_v         = float(t["dd_pct"])
    rsi_v            = float(t["rsi_val"])
    bb_z_v           = float(t["bb_z"])
    fxi_ma200_pct_v  = float(t["fxi_vs_ma200_pct"])
    fxi_mom_v        = float(t["fxi_momentum_pct"])
    s_dd             = int(t["dd_score"])
    s_rsi            = int(t["rsi_score"])
    s_macd           = int(t["macd_score"])
    s_bb             = int(t["bb_score"])
    s_fxi_ma200      = int(t["fxi_ma200_score"])
    s_fxi_mom        = int(t["fxi_momentum_score"])
    tech_v           = int(t["tech_score"])
    macro_v          = int(t["macro_score"])
    pnl_pct_v        = (kweb_price_v - AVG_COST) / AVG_COST * 100 if AVG_COST > 0 else 0.0
    pnl_color        = "#16a34a" if pnl_pct_v >= 0 else "#dc2626"
    fxi_color        = "#16a34a" if fxi_ma200_pct_v >= 0 else ("#ca8a04" if fxi_ma200_pct_v >= -5 else "#dc2626")
    remaining        = TOTAL_BUDGET - USED_BUDGET

    def ind_bar(score, max_score, color):
        pct = int(score / max_score * 100) if max_score > 0 else 0
        return (f'<div style="display:flex;align-items:center;gap:8px">'
                f'<div style="flex:1;background:#e5e7eb;border-radius:99px;height:6px">'
                f'<div style="width:{pct}%;height:6px;border-radius:99px;background:{color}"></div></div>'
                f'<span style="font-size:12px;color:#374151;white-space:nowrap;min-width:50px">{score}/{max_score}</span></div>')

    def rule_table(rows_data):
        html_r = '<table style="width:100%;border-collapse:collapse;margin-top:8px;font-size:12px">'
        for row_d in rows_data:
            active = row_d.get("active", False)
            bg = "background:#f0fdf4;font-weight:600;" if active else ""
            marker = "✓ " if active else ""
            html_r += (f'<tr style="{bg}">'
                       f'<td style="padding:3px 6px;color:#6b7280">{marker}{row_d["cond"]}</td>'
                       f'<td style="padding:3px 6px;text-align:right;color:#374151">{row_d["score"]}分</td>'
                       f'</tr>')
        html_r += "</table>"
        return html_r

    macd_label = "金叉" if s_macd == 15 else ("底部收窄" if s_macd == 8 else "无信号")
    indicators = [
        {
            "name": "KWEB 60日回撤",
            "score": s_dd, "max": 25,
            "current": f"{dd_pct_v:+.2f}%",
            "color": "#4f46e5",
            "why": "相对近60日高点的回撤幅度。KWEB 受情绪冲击时可快速大跌，回撤越深说明市场恐慌越严重，也正是逢低布局的时机。",
            "rules": [
                {"cond": "回撤 ≤ −20%（深度修正）", "score": 25, "active": dd_pct_v <= -20},
                {"cond": "回撤 ≤ −10%（中度修正）", "score": 15, "active": -20 < dd_pct_v <= -10},
                {"cond": "回撤 > −10%（轻微回调）",  "score":  5, "active": dd_pct_v > -10},
            ]
        },
        {
            "name": "KWEB RSI(14)",
            "score": s_rsi, "max": 20,
            "current": f"{rsi_v:.1f}",
            "color": "#0891b2",
            "why": "RSI 衡量过去14天涨跌力度。低于30通常表示严重超卖，短期反弹概率大；中国互联网板块情绪化较强，超卖反弹幅度往往更大。",
            "rules": [
                {"cond": "RSI ≤ 30（严重超卖）",    "score": 20, "active": rsi_v <= 30},
                {"cond": "RSI ≤ 40（偏弱区间）",    "score": 12, "active": 30 < rsi_v <= 40},
                {"cond": "RSI ≤ 50（中性偏弱）",    "score":  4, "active": 40 < rsi_v <= 50},
                {"cond": "RSI > 50（偏强，无信号）", "score":  0, "active": rsi_v > 50},
            ]
        },
        {
            "name": "MACD 柱状态",
            "score": s_macd, "max": 15,
            "current": macd_label,
            "color": "#16a34a",
            "why": "MACD 柱由负转正是金叉信号，说明下跌动能转为上涨；柱虽为负但收窄说明空头力量减弱，可提前布局。",
            "rules": [
                {"cond": "柱由负转正（金叉，趋势反转）",    "score": 15, "active": s_macd == 15},
                {"cond": "柱为负但较前日收窄（底部信号）",  "score":  8, "active": s_macd == 8},
                {"cond": "无以上信号",                     "score":  0, "active": s_macd == 0},
            ]
        },
        {
            "name": "布林带位置（z-score）",
            "score": s_bb, "max": 15,
            "current": f"z = {bb_z_v:.2f}",
            "color": "#ca8a04",
            "why": "布林带 z-score 衡量价格偏离20日均线的标准差倍数。z < −2 意味着价格在统计上极度低估，均值回归概率高。",
            "rules": [
                {"cond": "z < −2.0（极度低估，2σ以下）", "score": 15, "active": bb_z_v < -2.0},
                {"cond": "z < −1.5（明显低估）",         "score":  8, "active": -2.0 <= bb_z_v < -1.5},
                {"cond": "z ≥ −1.5（价格正常区间）",     "score":  0, "active": bb_z_v >= -1.5},
            ]
        },
        {
            "name": "FXI vs 200日均线",
            "score": s_fxi_ma200, "max": 15,
            "current": f"{fxi_ma200_pct_v:+.1f}%",
            "color": "#dc2626",
            "why": "FXI（iShares 中国大盘ETF）相对其200日均线的位置，是中国股市中长期趋势的代理指标。FXI 高于 MA200 表明大盘处于多头，宏观环境有利于 KWEB 买入。",
            "rules": [
                {"cond": "FXI 高于 MA200（多头趋势）",         "score": 15, "active": fxi_ma200_pct_v >= 0},
                {"cond": "FXI 低于 MA200 但在 5% 以内（边缘）", "score":  8, "active": -5 <= fxi_ma200_pct_v < 0},
                {"cond": "FXI 低于 MA200 超过 5%（空头趋势）",  "score":  0, "active": fxi_ma200_pct_v < -5},
            ]
        },
        {
            "name": "FXI 20日动量",
            "score": s_fxi_mom, "max": 10,
            "current": f"{fxi_mom_v:+.1f}%",
            "color": "#9333ea",
            "why": "FXI 近20个交易日的价格变化率，衡量中国大盘短期动能。正动量说明资金回流中国市场，有利于 KWEB 继续上涨。",
            "rules": [
                {"cond": "FXI 20日涨幅 > 3%（强劲动能）",   "score": 10, "active": fxi_mom_v > 3},
                {"cond": "FXI 20日涨幅 > 0%（正向动能）",   "score":  5, "active": 0 < fxi_mom_v <= 3},
                {"cond": "FXI 20日下跌（动能为负）",         "score":  0, "active": fxi_mom_v <= 0},
            ]
        },
    ]

    ind_html = ""
    for ind in indicators:
        ind_html += f"""
        <div style="background:#fff;border-radius:10px;padding:20px 24px;box-shadow:0 1px 4px rgba(0,0,0,.08)">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px">
            <div>
              <div style="font-size:14px;font-weight:600;color:#111;margin-bottom:2px">{ind['name']}</div>
              <div style="font-size:12px;color:#6b7280">当前值：<span style="color:#374151;font-weight:600">{ind['current']}</span></div>
            </div>
            <div style="text-align:right">
              <div style="font-size:22px;font-weight:700;color:{ind['color']}">{ind['score']}<span style="font-size:12px;color:#9ca3af">/{ind['max']}</span></div>
            </div>
          </div>
          {ind_bar(ind['score'], ind['max'], ind['color'])}
          <div style="margin-top:12px;font-size:12px;color:#6b7280;line-height:1.6;background:#f9fafb;border-radius:6px;padding:8px 10px">
            <span style="font-weight:600;color:#374151">为什么：</span>{ind['why']}
          </div>
          {rule_table(ind['rules'])}
        </div>"""

    table_rows_html = ""
    for r in rows_desc:
        sc = int(r["total_score"])
        c  = _score_color(sc)
        table_rows_html += f"""
        <tr>
          <td>{r['date']}</td>
          <td style="font-weight:600;color:{c}">{sc}</td>
          <td>${float(r['kweb_price']):.2f}</td>
          <td>${float(r['fxi_price']):.2f}</td>
          <td>{r['dd_score']}</td>
          <td>{r['rsi_score']}</td>
          <td>{r['macd_score']}</td>
          <td>{r['bb_score']}</td>
          <td>{r['fxi_ma200_score']}</td>
          <td>{r['fxi_momentum_score']}</td>
          <td>{float(r['dd_pct']):+.1f}%</td>
          <td>{float(r['rsi_val']):.1f}</td>
          <td>{_alert_badge(r['alert_level'])}</td>
          <td>{_signal_badge(r['buy_signal'])}</td>
          <td>${float(r['suggested_amount']):,.0f}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>KWEB 买入信号</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
  body {{ font-family: -apple-system, sans-serif; background: #f9fafb; margin: 0; padding: 24px; color: #111 }}
  h1   {{ font-size: 22px; font-weight: 700; margin-bottom: 4px }}
  .sub {{ color: #6b7280; font-size: 13px; margin-bottom: 24px }}
  .cards {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 24px }}
  .card {{ background: #fff; border-radius: 10px; padding: 20px 24px; box-shadow: 0 1px 4px rgba(0,0,0,.08); min-width: 150px }}
  .card .label {{ font-size: 12px; color: #6b7280; margin-bottom: 6px }}
  .card .val   {{ font-size: 28px; font-weight: 700 }}
  .chart-box {{ background: #fff; border-radius: 10px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.08); margin-bottom: 24px }}
  .chart-box h2 {{ font-size: 15px; margin: 0 0 12px }}
  .section-title {{ font-size: 15px; font-weight: 600; margin: 0 0 12px; color: #111 }}
  .ind-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; margin-bottom: 24px }}
  table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 10px;
           box-shadow: 0 1px 4px rgba(0,0,0,.08); overflow: hidden }}
  th {{ background: #f3f4f6; padding: 10px 12px; text-align: left; font-size: 12px; color: #374151 }}
  td {{ padding: 9px 12px; font-size: 13px; border-top: 1px solid #f3f4f6 }}
  tr:hover td {{ background: #fafafa }}
  .score-bar-wrap {{ background: #e5e7eb; border-radius: 99px; height: 8px; width: 120px; margin-top: 8px }}
  .score-bar {{ height: 8px; border-radius: 99px }}
</style>
</head>
<body>
<h1>KWEB 买入信号</h1>
<div class="sub">最后更新：{t['date']} &nbsp;·&nbsp; 每个交易日收盘后自动刷新</div>

<div class="cards">
  <div class="card">
    <div class="label">今日综合评分</div>
    <div class="val" style="color:{tc}">{ts}<span style="font-size:16px;color:#9ca3af">/100</span></div>
    <div class="score-bar-wrap"><div class="score-bar" style="width:{ts}%;background:{tc}"></div></div>
  </div>
  <div class="card">
    <div class="label">KWEB 现价</div>
    <div class="val">${kweb_price_v:.2f}</div>
  </div>
  <div class="card">
    <div class="label">FXI 现价</div>
    <div class="val">${fxi_price_v:.2f}</div>
  </div>
  <div class="card">
    <div class="label">总投入</div>
    <div class="val">${TOTAL_SHARES * AVG_COST:,.0f}</div>
    <div style="font-size:11px;color:#6b7280;margin-top:4px">{TOTAL_SHARES:.1f} 股</div>
  </div>
  <div class="card">
    <div class="label">每股成本</div>
    <div class="val">${AVG_COST:.2f}</div>
  </div>
  <div class="card">
    <div class="label">持仓盈亏</div>
    <div class="val" style="color:{pnl_color}">{pnl_pct_v:+.1f}%</div>
  </div>
  <div class="card">
    <div class="label">FXI vs MA200</div>
    <div class="val" style="color:{fxi_color}">{fxi_ma200_pct_v:+.1f}%</div>
  </div>
  <div class="card">
    <div class="label">KWEB RSI</div>
    <div class="val">{rsi_v:.1f}</div>
  </div>
  <div class="card">
    <div class="label">建议投入</div>
    <div class="val" style="color:#16a34a">${float(t['suggested_amount']):,.0f}</div>
  </div>
  <div class="card">
    <div class="label">预警状态</div>
    <div style="margin-top:10px">{_alert_badge(t['alert_level'])}</div>
  </div>
</div>

<div class="chart-box">
  <h2>历史评分走势</h2>
  <canvas id="scoreChart" height="80"></canvas>
</div>

<div class="section-title">今日评分详情</div>
<div class="ind-grid">{ind_html}</div>

<div class="section-title" style="margin-top:8px">建议投入计算</div>
<div style="background:#fff;border-radius:10px;padding:20px 24px;box-shadow:0 1px 4px rgba(0,0,0,.08);margin-bottom:24px">
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;flex-wrap:wrap">
    <div>
      <div style="font-size:13px;font-weight:600;color:#374151;margin-bottom:10px">预算状态</div>
      <table style="width:100%;border-collapse:collapse;font-size:13px">
        <tr><td style="padding:5px 0;color:#6b7280">总追加预算</td><td style="text-align:right;font-weight:600">${TOTAL_BUDGET:,}</td></tr>
        <tr style="border-top:1px solid #f3f4f6"><td style="padding:5px 0;color:#6b7280">已投入</td><td style="text-align:right;font-weight:600;color:#dc2626">−${USED_BUDGET:,}</td></tr>
        <tr style="border-top:2px solid #e5e7eb"><td style="padding:5px 0;font-weight:600">剩余预算</td><td style="text-align:right;font-weight:700;font-size:16px;color:#16a34a">${int(remaining):,}</td></tr>
      </table>
      <div style="margin-top:14px;font-size:12px;color:#6b7280;background:#f9fafb;border-radius:6px;padding:8px 10px;line-height:1.6">
        <span style="font-weight:600;color:#374151">计算公式：</span>建议投入 = 剩余预算 × 评分对应比例<br>
        若触发<span style="color:#dc2626;font-weight:600">红色预警</span>（FXI跌破MA200持续10日 或 浮亏超35%），建议投入强制归零，不论评分多高。
      </div>
    </div>
    <div>
      <div style="font-size:13px;font-weight:600;color:#374151;margin-bottom:10px">评分 → 投入比例</div>
      <table style="width:100%;border-collapse:collapse;font-size:13px">
        <tr style="background:#f3f4f6"><th style="padding:6px 8px;text-align:left;font-weight:600;color:#374151">评分</th><th style="padding:6px 8px;text-align:center;font-weight:600;color:#374151">比例</th><th style="padding:6px 8px;text-align:right;font-weight:600;color:#374151">本次金额</th></tr>
        <tr style="{'background:#f0fdf4;font-weight:600' if ts >= 80 else ''}">
          <td style="padding:6px 8px;border-top:1px solid #f3f4f6">{'✓ ' if ts >= 80 else ''}≥ 80（强烈信号）</td>
          <td style="padding:6px 8px;text-align:center;border-top:1px solid #f3f4f6">50%</td>
          <td style="padding:6px 8px;text-align:right;border-top:1px solid #f3f4f6">${int(remaining * 0.50):,}</td>
        </tr>
        <tr style="{'background:#f0fdf4;font-weight:600' if 60 <= ts < 80 else ''}">
          <td style="padding:6px 8px;border-top:1px solid #f3f4f6">{'✓ ' if 60 <= ts < 80 else ''}≥ 60（中等信号）</td>
          <td style="padding:6px 8px;text-align:center;border-top:1px solid #f3f4f6">35%</td>
          <td style="padding:6px 8px;text-align:right;border-top:1px solid #f3f4f6">${int(remaining * 0.35):,}</td>
        </tr>
        <tr style="{'background:#f0fdf4;font-weight:600' if 40 <= ts < 60 else ''}">
          <td style="padding:6px 8px;border-top:1px solid #f3f4f6">{'✓ ' if 40 <= ts < 60 else ''}≥ 40（弱信号）</td>
          <td style="padding:6px 8px;text-align:center;border-top:1px solid #f3f4f6">15%</td>
          <td style="padding:6px 8px;text-align:right;border-top:1px solid #f3f4f6">${int(remaining * 0.15):,}</td>
        </tr>
        <tr style="{'background:#f0fdf4;font-weight:600' if ts < 40 else ''}">
          <td style="padding:6px 8px;border-top:1px solid #f3f4f6">{'✓ ' if ts < 40 else ''}< 40（信号不足）</td>
          <td style="padding:6px 8px;text-align:center;border-top:1px solid #f3f4f6">0%</td>
          <td style="padding:6px 8px;text-align:right;border-top:1px solid #f3f4f6">$0</td>
        </tr>
      </table>
    </div>
  </div>
</div>

<div class="section-title">历史记录</div>
<table>
<thead>
  <tr>
    <th>日期</th><th>总分</th><th>KWEB价</th><th>FXI价</th>
    <th>回撤</th><th>RSI</th><th>MACD</th><th>BB</th><th>FXI-MA200</th><th>FXI动量</th>
    <th>回撤%</th><th>RSI值</th><th>预警</th><th>信号</th><th>建议金额</th>
  </tr>
</thead>
<tbody>{table_rows_html}</tbody>
</table>

<script>
new Chart(document.getElementById('scoreChart'), {{
  type: 'line',
  data: {{
    labels: {chart_labels},
    datasets: [{{
      label: '综合评分',
      data: {chart_scores},
      borderColor: '#dc2626',
      backgroundColor: 'rgba(220,38,38,0.08)',
      fill: true,
      tension: 0.3,
      pointRadius: 3,
      borderWidth: 2
    }}, {{
      label: '买入门槛 (40)',
      data: Array({len(chart_rows)}).fill(40),
      borderColor: '#9ca3af',
      borderDash: [6, 4],
      pointRadius: 0,
      borderWidth: 1.5
    }}]
  }},
  options: {{
    plugins: {{ legend: {{ display: true, position: 'top' }} }},
    scales: {{ y: {{ min: 0, max: 100 }} }}
  }}
}});
</script>
</body></html>"""

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  → HTML: {HTML_FILE}")

# ── 主程序 ─────────────────────────────────────────────────────────────────────
def main():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"\n{'='*50}")
    print(f"KWEB 买入信号评分  {today}")
    print(f"{'='*50}")

    print("拉取行情数据...")
    kweb_df = fetch(SYMBOL)
    fxi_df  = fetch(MACRO_SYMBOL)

    if kweb_df.empty or fxi_df.empty:
        print("ERROR: 数据拉取失败，请检查网络")
        return

    kweb_close = kweb_df['Close']
    kweb_price = float(kweb_close.iloc[-1])
    fxi_price  = float(fxi_df['Close'].iloc[-1])

    # 技术指标
    rsi     = calc_rsi(kweb_close)
    h_now, h_prev = calc_macd(kweb_close)
    bb_z    = calc_bb_z(kweb_close)
    dd_pct  = calc_drawdown(kweb_close)

    # 宏观指标
    fxi_vs_ma200_pct, fxi_momentum_pct = calc_fxi_macro(fxi_df)

    # 评分
    dd_score           = score_drawdown(dd_pct)
    rsi_score          = score_rsi(rsi)
    macd_score         = score_macd(h_prev, h_now)
    bb_score           = score_bb(bb_z)
    fxi_ma200_score    = score_fxi_ma200(fxi_vs_ma200_pct)
    fxi_momentum_score = score_fxi_momentum(fxi_momentum_pct)

    tech_score  = dd_score + rsi_score + macd_score + bb_score
    macro_score = fxi_ma200_score + fxi_momentum_score
    total_score = tech_score + macro_score

    # 持仓盈亏
    pnl_pct = ((kweb_price - AVG_COST) / AVG_COST * 100) if AVG_COST > 0 else None

    # 买入建议
    remaining = TOTAL_BUDGET - USED_BUDGET
    amount    = suggested_amount(total_score, remaining)
    buy_signal = total_score >= 60

    # 预警
    alerts     = check_alerts(pnl_pct, fxi_df)
    alert_level = max((level for level, _ in alerts), key=lambda x: _ALERT_PRIORITY.get(x, 0)) if alerts else "NONE"
    if alert_level == "RED":
        amount = 0.0
        buy_signal = False

    # 输出
    print(f"\nKWEB: ${kweb_price:.2f}  |  FXI: ${fxi_price:.2f}")
    print(f"总评分: {total_score}/100  (技术:{tech_score}/75  宏观:{macro_score}/25)")
    print(f"  回撤:{dd_score}  RSI:{rsi_score}  MACD:{macd_score}  BB:{bb_score}")
    print(f"  FXI-MA200:{fxi_ma200_score}  FXI动量:{fxi_momentum_score}")
    print(f"FXI vs MA200: {fxi_vs_ma200_pct:.1f}%  |  FXI 20日动量: {fxi_momentum_pct:.1f}%")
    if pnl_pct is not None:
        print(f"持仓盈亏: {pnl_pct:.1f}%")
    print(f"建议买入: ${amount:.0f}  |  信号: {'✅ 买入' if buy_signal else '⏳ 等待'}")
    for level, msg in alerts:
        print(f"  [{level}] {msg}")

    row = {
        "date": today,
        "kweb_price": f"{kweb_price:.4f}",
        "fxi_price": f"{fxi_price:.4f}",
        "total_score": total_score,
        "tech_score": tech_score,
        "macro_score": macro_score,
        "dd_score": dd_score,
        "rsi_score": rsi_score,
        "macd_score": macd_score,
        "bb_score": bb_score,
        "fxi_ma200_score": fxi_ma200_score,
        "fxi_momentum_score": fxi_momentum_score,
        "dd_pct": f"{dd_pct:.2f}",
        "rsi_val": f"{rsi:.2f}",
        "bb_z": f"{bb_z:.4f}",
        "fxi_vs_ma200_pct": f"{fxi_vs_ma200_pct:.2f}",
        "fxi_momentum_pct": f"{fxi_momentum_pct:.2f}",
        "suggested_amount": f"{amount:.2f}",
        "alert_level": alert_level,
        "buy_signal": str(buy_signal),
    }
    save_csv(row)
    generate_html(row)
    print(f"  → CSV: {CSV_FILE}")

if __name__ == "__main__":
    main()
