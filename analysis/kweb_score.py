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

    s     = int(today["total_score"])
    color = _score_color(s)

    fxi_pct = float(today["fxi_vs_ma200_pct"])
    fxi_color = "#16a34a" if fxi_pct >= 0 else ("#ca8a04" if fxi_pct >= -5 else "#dc2626")

    table_rows_html = ""
    for r in rows_desc:
        sc = int(r["total_score"])
        c  = _score_color(sc)
        table_rows_html += f"""
        <tr>
          <td>{r['date']}</td>
          <td>${float(r['kweb_price']):.2f}</td>
          <td>${float(r['fxi_price']):.2f}</td>
          <td style="color:{c};font-weight:bold">{sc}</td>
          <td>{r['tech_score']}</td>
          <td>{r['macro_score']}</td>
          <td>{_alert_badge(r['alert_level'])}</td>
          <td>{_signal_badge(r['buy_signal'])}</td>
          <td>${float(r['suggested_amount']):.0f}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8">
<title>KWEB 买入信号</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  body{{font-family:sans-serif;margin:20px;background:#f9fafb}}
  .card{{background:#fff;border-radius:8px;padding:20px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.1)}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px}}
  .metric{{text-align:center}} .metric .val{{font-size:2em;font-weight:bold}} .metric .lbl{{color:#6b7280;font-size:13px}}
  table{{width:100%;border-collapse:collapse}} th,td{{padding:8px 12px;border-bottom:1px solid #e5e7eb;font-size:13px}}
  th{{background:#f3f4f6;text-align:left}}
</style></head><body>
<h2>KWEB 买入信号评分 — {today['date']}</h2>
<div class="card">
  <div class="grid">
    <div class="metric"><div class="val">${float(today['kweb_price']):.2f}</div><div class="lbl">KWEB 价格</div></div>
    <div class="metric"><div class="val" style="color:{color}">{s}</div><div class="lbl">总评分</div></div>
    <div class="metric"><div class="val">{today['tech_score']}</div><div class="lbl">技术分/75</div></div>
    <div class="metric"><div class="val">{today['macro_score']}</div><div class="lbl">宏观分/25</div></div>
    <div class="metric"><div class="val" style="color:{fxi_color}">{float(today['fxi_vs_ma200_pct']):.1f}%</div><div class="lbl">FXI vs MA200</div></div>
    <div class="metric"><div class="val">${float(today['suggested_amount']):.0f}</div><div class="lbl">建议买入</div></div>
  </div>
  <div style="margin-top:12px;text-align:center">
    {_alert_badge(today['alert_level'])} &nbsp; {_signal_badge(today['buy_signal'])}
  </div>
</div>
<div class="card">
  <canvas id="scoreChart" height="80"></canvas>
</div>
<div class="card">
  <table><thead><tr>
    <th>日期</th><th>KWEB</th><th>FXI</th><th>总分</th><th>技术</th><th>宏观</th><th>预警</th><th>信号</th><th>建议</th>
  </tr></thead><tbody>{table_rows_html}</tbody></table>
</div>
<script>
new Chart(document.getElementById('scoreChart'),{{
  type:'line',
  data:{{labels:{chart_labels},datasets:[{{label:'总评分',data:{chart_scores},borderColor:'#2563eb',tension:.3,fill:false}}]}},
  options:{{plugins:{{legend:{{display:false}}}},scales:{{y:{{min:0,max:100}}}}}}
}});
</script></body></html>"""

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
    alert_level = alerts[0][0] if alerts else "NONE"
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
