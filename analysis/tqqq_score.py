# -*- coding: utf-8 -*-
"""
TQQQ 买入信号评分脚本
用法: python tqqq_score.py
每日定时运行，结果追加到 tqqq_history.csv，并更新 tqqq_report.html
"""

import sys, io, os, csv, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# ── 参数（根据个人情况修改） ────────────────────────────────────────────────────
TOTAL_BUDGET  = 10_000   # 原始追加预算 ($)
USED_BUDGET   = 4_500    # 已追加投入 ($)
AVG_COST      = 45.52    # 平均成本（每股）
TOTAL_SHARES  = 252.635  # 持仓股数（2026-03-31 加仓后）
LOOKBACK_DAYS = 400      # 拉取多少天历史

# 结果保存目录
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR  = os.path.join(SCRIPT_DIR, "report")
os.makedirs(REPORT_DIR, exist_ok=True)
CSV_FILE    = os.path.join(REPORT_DIR, "tqqq_history.csv")
HTML_FILE   = os.path.join(REPORT_DIR, "tqqq_report.html")

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
    delta = closes.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)
    ag = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    al = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = ag / al.replace(0, np.nan)
    return float((100 - 100 / (1 + rs)).iloc[-1])

def calc_macd(closes, fast=12, slow=26, signal=9):
    ml  = closes.ewm(span=fast, adjust=False).mean() - closes.ewm(span=slow, adjust=False).mean()
    sl  = ml.ewm(span=signal, adjust=False).mean()
    h   = ml - sl
    return float(h.iloc[-1]), float(h.iloc[-2])

def calc_bb_z(closes, period=20):
    w   = closes.iloc[-(period+1):-1]
    std = w.std()
    return float((closes.iloc[-1] - w.mean()) / std) if std else 0.0

def calc_atr(df, period=14):
    h, l, c = df['High'], df['Low'], df['Close']
    tr = pd.concat([(h-l), (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
    s  = tr.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    return float(s.iloc[-1]), float(s.iloc[-61:-1].mean())

def calc_drawdown(closes, lookback=60):
    high = closes.iloc[-lookback:-1].max()
    return float((closes.iloc[-1] - high) / high * 100)

# ── 评分规则 ───────────────────────────────────────────────────────────────────
def score_drawdown(pct):
    return 25 if pct <= -20 else 15 if pct <= -10 else 5

def score_rsi(r):
    return 25 if r <= 30 else 15 if r <= 40 else 5 if r <= 50 else 0

def score_macd(prev, now):
    if prev < 0 and now > 0: return 20
    if now < 0 and now > prev: return 10
    return 0

def score_bb(z):
    return 15 if z < -2.0 else 8 if z < -1.5 else 0

def score_atr(now, mean):
    r = now / mean if mean > 0 else 1.0
    return 15 if 1.0 < r < 1.5 else 5 if r <= 1.5 else 0

def suggested_amount(score, remaining):
    if score >= 80: return remaining * 0.50
    if score >= 60: return remaining * 0.35
    if score >= 40: return remaining * 0.15
    return 0.0

# ── 止损预警 ───────────────────────────────────────────────────────────────────
def check_alerts(pnl_pct, qqq_df):
    alerts = []
    c   = qqq_df['Close']
    ma200 = c.rolling(200).mean()
    if (c < ma200).iloc[-10:].values.all():
        alerts.append(("RED", "QQQ 跌破 MA200 已持续 10 日"))
    monthly = c.resample('ME').last()
    if len(monthly) >= 4 and all(
            float(monthly.iloc[-i]) < float(monthly.iloc[-i-1]) for i in range(1, 4)):
        alerts.append(("RED", "QQQ 月线连续 3 根阴线"))
    if pnl_pct is not None:
        if pnl_pct < -40:
            alerts.append(("ORANGE", f"浮亏 {pnl_pct:.1f}%，考虑减仓 50%"))
        elif pnl_pct < -25:
            alerts.append(("YELLOW", f"浮亏 {pnl_pct:.1f}%，暂停新买入"))
    return alerts

# ── 保存 CSV ───────────────────────────────────────────────────────────────────
CSV_FIELDS = ["date","tqqq_price","total_score","dd_score","rsi_score",
              "macd_score","bb_score","atr_score","qqq_dd_pct","tqqq_rsi",
              "bb_z","atr_ratio","suggested_amount","alert_level","buy_signal"]

def save_csv(row: dict):
    write_header = not os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if write_header:
            w.writeheader()
        # 如果今天已有记录则覆盖（重写整个文件）
        if not write_header:
            rows = read_csv_rows()
            rows = [r for r in rows if r["date"] != row["date"]]
            rows.append(row)
            f.seek(0); f.truncate()
            w.writeheader()
            w.writerows(rows)
        else:
            w.writerow(row)

def read_csv_rows():
    if not os.path.exists(CSV_FILE):
        return []
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

# ── 生成 HTML 报告 ─────────────────────────────────────────────────────────────
def generate_html(today_row: dict):
    rows = read_csv_rows()
    # 最新在前
    rows_desc = sorted(rows, key=lambda r: r["date"], reverse=True)

    def score_color(s):
        s = int(s)
        if s >= 80: return "#16a34a"
        if s >= 60: return "#ca8a04"
        if s >= 40: return "#2563eb"
        return "#9ca3af"

    def alert_badge(level):
        colors = {"RED":"#dc2626","ORANGE":"#ea580c","YELLOW":"#ca8a04","NONE":"#6b7280"}
        c = colors.get(level, "#6b7280")
        return f'<span style="background:{c};color:#fff;padding:2px 8px;border-radius:4px;font-size:12px">{level}</span>'

    def signal_badge(active):
        if active == "True":
            return '<span style="background:#16a34a;color:#fff;padding:2px 8px;border-radius:4px;font-size:12px">买入信号</span>'
        return '<span style="background:#9ca3af;color:#fff;padding:2px 8px;border-radius:4px;font-size:12px">等待中</span>'

    # 评分折线图数据（最近60条）
    chart_rows = sorted(rows, key=lambda r: r["date"])[-60:]
    chart_labels = json.dumps([r["date"] for r in chart_rows])
    chart_scores = json.dumps([int(r["total_score"]) for r in chart_rows])

    table_rows_html = ""
    for r in rows_desc:
        s = int(r["total_score"])
        c = score_color(s)
        table_rows_html += f"""
        <tr>
          <td>{r['date']}</td>
          <td style="font-weight:600;color:{c}">{s}</td>
          <td>${float(r['tqqq_price']):.2f}</td>
          <td>{r['dd_score']}</td>
          <td>{r['rsi_score']}</td>
          <td>{r['macd_score']}</td>
          <td>{r['bb_score']}</td>
          <td>{r['atr_score']}</td>
          <td>{float(r['qqq_dd_pct']):+.1f}%</td>
          <td>{float(r['tqqq_rsi']):.1f}</td>
          <td>{alert_badge(r['alert_level'])}</td>
          <td>{signal_badge(r['buy_signal'])}</td>
          <td>${float(r['suggested_amount']):,.0f}</td>
        </tr>"""

    t = today_row
    ts = int(t["total_score"])
    tc = score_color(ts)

    # 各指标详情（评分规则 + 当前状态 + 原因说明）
    dd_pct_val   = float(t['qqq_dd_pct'])
    rsi_val_val  = float(t['tqqq_rsi'])
    bb_z_val     = float(t['bb_z'])
    atr_r_val    = float(t['atr_ratio'])
    s_dd_v       = int(t['dd_score'])
    s_rsi_v      = int(t['rsi_score'])
    s_macd_v     = int(t['macd_score'])
    s_bb_v       = int(t['bb_score'])
    s_atr_v      = int(t['atr_score'])

    def ind_bar(score, max_score, color):
        pct = int(score / max_score * 100) if max_score > 0 else 0
        return (f'<div style="display:flex;align-items:center;gap:8px">'
                f'<div style="flex:1;background:#e5e7eb;border-radius:99px;height:6px">'
                f'<div style="width:{pct}%;height:6px;border-radius:99px;background:{color}"></div></div>'
                f'<span style="font-size:12px;color:#374151;white-space:nowrap;min-width:50px">{score}/{max_score}</span></div>')

    def rule_table(rows_data):
        html_r = '<table style="width:100%;border-collapse:collapse;margin-top:8px;font-size:12px">'
        for row_d in rows_data:
            active = row_d.get('active', False)
            bg = 'background:#f0fdf4;font-weight:600;' if active else ''
            marker = '✓ ' if active else ''
            html_r += (f'<tr style="{bg}">'
                       f'<td style="padding:3px 6px;color:#6b7280">{marker}{row_d["cond"]}</td>'
                       f'<td style="padding:3px 6px;text-align:right;color:#374151">{row_d["score"]}分</td>'
                       f'</tr>')
        html_r += '</table>'
        return html_r

    indicators = [
        {
            "name": "QQQ 回撤幅度",
            "score": s_dd_v, "max": 25,
            "current": f"{dd_pct_val:+.2f}%",
            "color": "#4f46e5",
            "why": "QQQ（纳指ETF）大幅回撤时，TQQQ 被三倍放大同步下跌，价格越低买入成本越低、长期回报越高。回撤越深说明市场恐慌越严重，也正是价值买入的时机。",
            "rules": [
                {"cond": "QQQ 回撤 ≤ −20%（深度修正）", "score": 25, "active": dd_pct_val <= -20},
                {"cond": "QQQ 回撤 ≤ −10%（中度修正）", "score": 15, "active": -20 < dd_pct_val <= -10},
                {"cond": "QQQ 回撤 > −10%（轻微回调）",  "score":  5, "active": dd_pct_val > -10},
            ]
        },
        {
            "name": "TQQQ RSI(14)",
            "score": s_rsi_v, "max": 25,
            "current": f"{rsi_val_val:.1f}",
            "color": "#0891b2",
            "why": "RSI 是相对强弱指数，衡量过去14天涨跌力度。RSI 低于 30 通常表示严重超卖，短期反弹概率大；超卖幅度越深，买入性价比越高。",
            "rules": [
                {"cond": "RSI ≤ 30（严重超卖）", "score": 25, "active": rsi_val_val <= 30},
                {"cond": "RSI ≤ 40（偏弱区间）", "score": 15, "active": 30 < rsi_val_val <= 40},
                {"cond": "RSI ≤ 50（中性偏弱）", "score":  5, "active": 40 < rsi_val_val <= 50},
                {"cond": "RSI > 50（偏强，无信号）", "score": 0, "active": rsi_val_val > 50},
            ]
        },
        {
            "name": "MACD 柱状态",
            "score": s_macd_v, "max": 20,
            "current": ("金叉" if s_macd_v == 20 else "底部收窄" if s_macd_v == 10 else "无信号"),
            "color": "#16a34a",
            "why": "MACD 柱（Histogram）反映短期动能。柱由负转正是经典金叉信号，说明下跌动能正在转为上涨；柱虽为负但正在收窄说明空头力量减弱，可提前布局。",
            "rules": [
                {"cond": "柱由负转正（金叉，趋势反转）",   "score": 20, "active": s_macd_v == 20},
                {"cond": "柱为负但较前一日收窄（底部信号）", "score": 10, "active": s_macd_v == 10},
                {"cond": "无以上信号",                    "score":  0, "active": s_macd_v == 0},
            ]
        },
        {
            "name": "布林带位置（z-score）",
            "score": s_bb_v, "max": 15,
            "current": f"z = {bb_z_val:.2f}",
            "color": "#ca8a04",
            "why": "布林带 z-score 衡量当前价格偏离20日均线的标准差倍数。z < −2 意味着价格已跌至统计意义上的极低位，均值回归的概率很高。",
            "rules": [
                {"cond": "z < −2.0（极度低估，2σ以下）", "score": 15, "active": bb_z_val < -2.0},
                {"cond": "z < −1.5（明显低估）",         "score":  8, "active": -2.0 <= bb_z_val < -1.5},
                {"cond": "z ≥ −1.5（价格正常区间）",     "score":  0, "active": bb_z_val >= -1.5},
            ]
        },
        {
            "name": "ATR 波动率",
            "score": s_atr_v, "max": 15,
            "current": f"ATR/均值 = {atr_r_val:.2f}x",
            "color": "#9333ea",
            "why": "ATR（平均真实波幅）与60日均值之比，衡量当前波动是否异常放大。适度放大（1.0–1.5x）说明市场活跃、出现机会；极度放大（>1.5x）通常伴随崩盘风险，不宜重仓。",
            "rules": [
                {"cond": "1.0 < ATR/均值 < 1.5（适度放大）", "score": 15, "active": 1.0 < atr_r_val < 1.5},
                {"cond": "ATR/均值 ≤ 1.0（波动正常）",       "score":  5, "active": atr_r_val <= 1.0},
                {"cond": "ATR/均值 ≥ 1.5（极度波动，慎重）", "score":  0, "active": atr_r_val >= 1.5},
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

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>TQQQ 买入信号</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
  body {{ font-family: -apple-system, sans-serif; background: #f9fafb; margin: 0; padding: 24px; color: #111 }}
  h1   {{ font-size: 22px; font-weight: 700; margin-bottom: 4px }}
  .sub {{ color: #6b7280; font-size: 13px; margin-bottom: 24px }}
  .cards {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 24px }}
  .card {{ background: #fff; border-radius: 10px; padding: 20px 24px; box-shadow: 0 1px 4px rgba(0,0,0,.08); min-width: 160px }}
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
<h1>TQQQ 买入信号</h1>
<div class="sub">最后更新：{t['date']} &nbsp;·&nbsp; 每个交易日收盘后自动刷新</div>

<div class="cards">
  <div class="card">
    <div class="label">今日综合评分</div>
    <div class="val" style="color:{tc}">{ts}<span style="font-size:16px;color:#9ca3af">/100</span></div>
    <div class="score-bar-wrap"><div class="score-bar" style="width:{ts}%;background:{tc}"></div></div>
  </div>
  <div class="card">
    <div class="label">TQQQ 现价</div>
    <div class="val">${float(t['tqqq_price']):.2f}</div>
  </div>
  <div class="card">
    <div class="label">总投入</div>
    <div class="val">${TOTAL_SHARES * AVG_COST:,.0f}</div>
    <div style="font-size:11px;color:#6b7280;margin-top:4px">{TOTAL_SHARES:.2f} 股</div>
  </div>
  <div class="card">
    <div class="label">每股成本</div>
    <div class="val">${AVG_COST:.2f}</div>
  </div>
  <div class="card">
    <div class="label">QQQ 回撤</div>
    <div class="val" style="color:#dc2626">{float(t['qqq_dd_pct']):+.1f}%</div>
  </div>
  <div class="card">
    <div class="label">TQQQ RSI</div>
    <div class="val">{float(t['tqqq_rsi']):.1f}</div>
  </div>
  <div class="card">
    <div class="label">建议投入</div>
    <div class="val" style="color:#16a34a">${float(t['suggested_amount']):,.0f}</div>
  </div>
  <div class="card">
    <div class="label">预警状态</div>
    <div style="margin-top:10px">{alert_badge(t['alert_level'])}</div>
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
        <tr style="border-top:2px solid #e5e7eb"><td style="padding:5px 0;font-weight:600">剩余预算</td><td style="text-align:right;font-weight:700;font-size:16px;color:#16a34a">${int(TOTAL_BUDGET - USED_BUDGET):,}</td></tr>
      </table>
      <div style="margin-top:14px;font-size:12px;color:#6b7280;background:#f9fafb;border-radius:6px;padding:8px 10px;line-height:1.6">
        <span style="font-weight:600;color:#374151">计算公式：</span>建议投入 = 剩余预算 × 评分对应比例<br>
        若触发<span style="color:#dc2626;font-weight:600">红色预警</span>（QQQ跌破MA200持续10日 或 月线连续3根阴线），建议投入强制归零，不论评分多高。
      </div>
    </div>
    <div>
      <div style="font-size:13px;font-weight:600;color:#374151;margin-bottom:10px">评分 → 投入比例</div>
      <table style="width:100%;border-collapse:collapse;font-size:13px">
        <tr style="background:#f3f4f6"><th style="padding:6px 8px;text-align:left;font-weight:600;color:#374151">评分</th><th style="padding:6px 8px;text-align:center;font-weight:600;color:#374151">比例</th><th style="padding:6px 8px;text-align:right;font-weight:600;color:#374151">本次金额</th></tr>
        <tr style="{'background:#f0fdf4;font-weight:600' if ts >= 80 else ''}">
          <td style="padding:6px 8px;border-top:1px solid #f3f4f6">{'✓ ' if ts >= 80 else ''}≥ 80（强烈信号）</td>
          <td style="padding:6px 8px;text-align:center;border-top:1px solid #f3f4f6">50%</td>
          <td style="padding:6px 8px;text-align:right;border-top:1px solid #f3f4f6">${int((TOTAL_BUDGET - USED_BUDGET) * 0.50):,}</td>
        </tr>
        <tr style="{'background:#f0fdf4;font-weight:600' if 60 <= ts < 80 else ''}">
          <td style="padding:6px 8px;border-top:1px solid #f3f4f6">{'✓ ' if 60 <= ts < 80 else ''}≥ 60（中等信号）</td>
          <td style="padding:6px 8px;text-align:center;border-top:1px solid #f3f4f6">35%</td>
          <td style="padding:6px 8px;text-align:right;border-top:1px solid #f3f4f6">${int((TOTAL_BUDGET - USED_BUDGET) * 0.35):,}</td>
        </tr>
        <tr style="{'background:#f0fdf4;font-weight:600' if 40 <= ts < 60 else ''}">
          <td style="padding:6px 8px;border-top:1px solid #f3f4f6">{'✓ ' if 40 <= ts < 60 else ''}≥ 40（弱信号）</td>
          <td style="padding:6px 8px;text-align:center;border-top:1px solid #f3f4f6">15%</td>
          <td style="padding:6px 8px;text-align:right;border-top:1px solid #f3f4f6">${int((TOTAL_BUDGET - USED_BUDGET) * 0.15):,}</td>
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
    <th>日期</th><th>总分</th><th>TQQQ价</th>
    <th>回撤</th><th>RSI</th><th>MACD</th><th>BB</th><th>ATR</th>
    <th>QQQ回撤%</th><th>RSI值</th><th>预警</th><th>信号</th><th>建议金额</th>
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
      borderColor: '#4f46e5',
      backgroundColor: 'rgba(79,70,229,0.1)',
      fill: true,
      tension: 0.3,
      pointRadius: 3,
      borderWidth: 2
    }}, {{
      label: '买入门槛 (40)',
      data: Array({len(chart_rows)}).fill(40),
      borderColor: '#9ca3af',
      borderDash: [6,4],
      pointRadius: 0,
      borderWidth: 1
    }}]
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ position: 'top' }} }},
    scales: {{ y: {{ min: 0, max: 100 }}, x: {{ ticks: {{ maxTicksLimit: 10 }} }} }}
  }}
}})
</script>
</body></html>"""

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)

# ── 主程序 ─────────────────────────────────────────────────────────────────────
def main():
    print("\n正在拉取数据...")
    qqq_df  = fetch("QQQ")
    tqqq_df = fetch("TQQQ")

    qqq_c  = qqq_df['Close'].squeeze()
    tqqq_c = tqqq_df['Close'].squeeze()

    price = float(tqqq_c.iloc[-1])
    today = str(tqqq_df.index[-1].date())

    pnl_pct = (price - AVG_COST) / AVG_COST * 100 if AVG_COST else None

    dd_pct          = calc_drawdown(qqq_c)
    rsi_val         = calc_rsi(tqqq_c)
    hist_now, hist_prev = calc_macd(tqqq_c)
    bb_z            = calc_bb_z(tqqq_c)
    atr_now, atr_mean = calc_atr(tqqq_df)
    atr_ratio       = atr_now / atr_mean if atr_mean else 1.0

    s_dd   = score_drawdown(dd_pct)
    s_rsi  = score_rsi(rsi_val)
    s_macd = score_macd(hist_prev, hist_now)
    s_bb   = score_bb(bb_z)
    s_atr  = score_atr(atr_now, atr_mean)
    total  = s_dd + s_rsi + s_macd + s_bb + s_atr

    alerts  = check_alerts(pnl_pct, qqq_df)
    is_red  = any(a[0] == "RED" for a in alerts)
    alert_level = alerts[0][0] if alerts else "NONE"

    remaining = max(0.0, TOTAL_BUDGET - USED_BUDGET)
    amount    = 0.0 if is_red else suggested_amount(total, remaining)
    buy_signal = (total >= 40 and not is_red)

    # ── 控制台输出 ──────────────────────────────────────────────────────────────
    SEP = "─" * 52
    print(f"\n{SEP}")
    print(f"  TQQQ 买入信号评分  |  {today}")
    print(SEP)
    print(f"  TQQQ 当前价格 : ${price:.2f}")
    if pnl_pct is not None:
        arrow = "▲" if pnl_pct >= 0 else "▼"
        print(f"  持仓浮盈/亏   : {arrow} {abs(pnl_pct):.1f}%  (成本 ${AVG_COST:.2f})")
    print(SEP)
    macd_label = "金叉" if s_macd==20 else "底部收窄" if s_macd==10 else "无信号"
    print(f"  {'指标':<18} {'分值':>5}  {'满分':>4}  详情")
    print(f"  {'─'*18} {'─'*5}  {'─'*4}  {'─'*14}")
    print(f"  {'QQQ 回撤幅度':<18} {s_dd:>5}  {'25':>4}  {dd_pct:+.1f}%")
    print(f"  {'TQQQ RSI(14)':<18} {s_rsi:>5}  {'25':>4}  RSI = {rsi_val:.1f}")
    print(f"  {'MACD 柱状态':<18} {s_macd:>5}  {'20':>4}  {macd_label}")
    print(f"  {'布林带位置':<18} {s_bb:>5}  {'15':>4}  z = {bb_z:.2f}")
    print(f"  {'ATR 波动率':<18} {s_atr:>5}  {'15':>4}  ATR/均值 = {atr_ratio:.2f}x")
    print(SEP)
    bar = "█" * int(total/2) + "░" * (50 - int(total/2))
    print(f"  综合评分 [{bar}] {total}/100")
    print(SEP)
    if alerts:
        for level, msg in alerts:
            icon = "🔴" if level=="RED" else "🟠" if level=="ORANGE" else "🟡"
            print(f"  {icon} [{level}] {msg}")
        print(SEP)
    if is_red:
        print(f"  ❌ 红色预警生效 — 买入信号已屏蔽")
    elif total >= 40:
        s = "强烈" if total>=80 else "中等" if total>=60 else "弱"
        print(f"  ✅ {s}买入信号（{total} 分）")
        print(f"  💰 建议投入：${amount:,.0f}（剩余预算 ${remaining:,.0f} 的 {amount/remaining*100:.0f}%）")
    else:
        print(f"  ⏳ 信号不足（{total} 分 < 40）— 继续等待")
    print(SEP)

    # ── 保存结果 ────────────────────────────────────────────────────────────────
    row = {
        "date": today, "tqqq_price": f"{price:.2f}", "total_score": total,
        "dd_score": s_dd, "rsi_score": s_rsi, "macd_score": s_macd,
        "bb_score": s_bb, "atr_score": s_atr, "qqq_dd_pct": f"{dd_pct:.2f}",
        "tqqq_rsi": f"{rsi_val:.2f}", "bb_z": f"{bb_z:.3f}",
        "atr_ratio": f"{atr_ratio:.3f}", "suggested_amount": f"{amount:.0f}",
        "alert_level": alert_level, "buy_signal": str(buy_signal)
    }
    save_csv(row)
    generate_html(row)

    print(f"\n  已保存 → {CSV_FILE}")
    print(f"  报告   → {HTML_FILE}")
    print()

if __name__ == "__main__":
    main()
