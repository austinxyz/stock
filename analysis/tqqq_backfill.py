# -*- coding: utf-8 -*-
"""补录本周历史评分并重新生成 HTML 报告"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import yfinance as yf
import pandas as pd
import numpy as np
import csv, os, json
from datetime import date

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR   = os.path.join(SCRIPT_DIR, "report")
os.makedirs(REPORT_DIR, exist_ok=True)
CSV_FILE     = os.path.join(REPORT_DIR, "tqqq_history.csv")
HTML_FILE    = os.path.join(REPORT_DIR, "tqqq_report.html")
TOTAL_BUDGET = 10_000

CSV_FIELDS = ["date","tqqq_price","total_score","dd_score","rsi_score",
              "macd_score","bb_score","atr_score","qqq_dd_pct","tqqq_rsi",
              "bb_z","atr_ratio","suggested_amount","alert_level","buy_signal"]

# ── 指标 ───────────────────────────────────────────────────────────────────────
def calc_rsi(c, p=14):
    d=c.diff(); ag=d.clip(lower=0).ewm(alpha=1/p,min_periods=p,adjust=False).mean()
    al=(-d.clip(upper=0)).ewm(alpha=1/p,min_periods=p,adjust=False).mean()
    return float((100-100/(1+ag/al.replace(0,np.nan))).iloc[-1])

def calc_macd(c, f=12, s=26, sig=9):
    ml=c.ewm(span=f,adjust=False).mean()-c.ewm(span=s,adjust=False).mean()
    h=ml-ml.ewm(span=sig,adjust=False).mean()
    return float(h.iloc[-1]), float(h.iloc[-2])

def calc_bb_z(c, p=20):
    w=c.iloc[-(p+1):-1]; std=w.std()
    return float((c.iloc[-1]-w.mean())/std) if std else 0.0

def calc_atr(df, p=14):
    h,l,c=df['High'],df['Low'],df['Close']
    tr=pd.concat([(h-l),(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    s=tr.ewm(alpha=1/p,min_periods=p,adjust=False).mean()
    return float(s.iloc[-1]), float(s.iloc[-61:-1].mean())

def calc_dd(c, lb=60):
    return float((c.iloc[-1]-c.iloc[-lb:-1].max())/c.iloc[-lb:-1].max()*100)

def compute_scores(dd,r,hp,hn,z,an,am):
    s_dd  = 25 if dd<=-20 else 15 if dd<=-10 else 5
    s_rsi = 25 if r<=30 else 15 if r<=40 else 5 if r<=50 else 0
    s_mac = 20 if hp<0 and hn>0 else 10 if hn<0 and hn>hp else 0
    s_bb  = 15 if z<-2 else 8 if z<-1.5 else 0
    rat   = an/am if am else 1.0
    s_atr = 15 if 1<rat<1.5 else 5 if rat<=1.5 else 0
    return s_dd,s_rsi,s_mac,s_bb,s_atr,s_dd+s_rsi+s_mac+s_bb+s_atr,rat

def alert_from_pnl(pnl):
    if pnl is None: return "NONE"
    if pnl < -40:   return "ORANGE"
    if pnl < -25:   return "YELLOW"
    return "NONE"

def suggest(score, remaining):
    if score>=80: return remaining*0.50
    if score>=60: return remaining*0.35
    if score>=40: return remaining*0.15
    return 0.0

# ── CSV ────────────────────────────────────────────────────────────────────────
def read_rows():
    if not os.path.exists(CSV_FILE): return []
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def write_rows(rows):
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader(); w.writerows(rows)

# ── HTML ───────────────────────────────────────────────────────────────────────
def score_color(s):
    s=int(s)
    if s>=80: return "#16a34a"
    if s>=60: return "#ca8a04"
    if s>=40: return "#2563eb"
    return "#9ca3af"

def alert_badge(level):
    c={"RED":"#dc2626","ORANGE":"#ea580c","YELLOW":"#ca8a04","NONE":"#6b7280"}.get(level,"#6b7280")
    return f'<span style="background:{c};color:#fff;padding:2px 8px;border-radius:4px;font-size:12px">{level}</span>'

def signal_badge(active):
    if str(active)=="True":
        return '<span style="background:#16a34a;color:#fff;padding:2px 8px;border-radius:4px;font-size:12px">买入信号</span>'
    return '<span style="background:#9ca3af;color:#fff;padding:2px 8px;border-radius:4px;font-size:12px">等待中</span>'

def generate_html(all_rows):
    rows_desc    = sorted(all_rows, key=lambda r: r["date"], reverse=True)
    t            = rows_desc[0]
    ts           = int(t["total_score"])
    tc           = score_color(ts)
    chart_rows   = sorted(all_rows, key=lambda r: r["date"])[-60:]
    chart_labels = json.dumps([r["date"] for r in chart_rows])
    chart_scores = json.dumps([int(r["total_score"]) for r in chart_rows])

    table_html = ""
    for r in rows_desc:
        s=int(r["total_score"]); c=score_color(s)
        table_html += (
            f'<tr>'
            f'<td>{r["date"]}</td>'
            f'<td style="font-weight:600;color:{c}">{s}</td>'
            f'<td>${float(r["tqqq_price"]):.2f}</td>'
            f'<td>{r["dd_score"]}</td><td>{r["rsi_score"]}</td>'
            f'<td>{r["macd_score"]}</td><td>{r["bb_score"]}</td><td>{r["atr_score"]}</td>'
            f'<td>{float(r["qqq_dd_pct"]):+.1f}%</td>'
            f'<td>{float(r["tqqq_rsi"]):.1f}</td>'
            f'<td>{alert_badge(r["alert_level"])}</td>'
            f'<td>{signal_badge(r["buy_signal"])}</td>'
            f'<td>${float(r["suggested_amount"]):,.0f}</td>'
            f'</tr>'
        )

    n = len(chart_rows)
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8"><title>TQQQ 买入信号</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
body{{font-family:-apple-system,sans-serif;background:#f9fafb;margin:0;padding:24px;color:#111}}
h1{{font-size:22px;font-weight:700;margin-bottom:4px}}
.sub{{color:#6b7280;font-size:13px;margin-bottom:24px}}
.cards{{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:24px}}
.card{{background:#fff;border-radius:10px;padding:20px 24px;box-shadow:0 1px 4px rgba(0,0,0,.08);min-width:160px}}
.card .label{{font-size:12px;color:#6b7280;margin-bottom:6px}}
.card .val{{font-size:28px;font-weight:700}}
.chart-box{{background:#fff;border-radius:10px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,.08);margin-bottom:24px}}
.chart-box h2{{font-size:15px;margin:0 0 12px}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,.08);overflow:hidden}}
th{{background:#f3f4f6;padding:10px 12px;text-align:left;font-size:12px;color:#374151}}
td{{padding:9px 12px;font-size:13px;border-top:1px solid #f3f4f6}}
tr:hover td{{background:#fafafa}}
.bar-wrap{{background:#e5e7eb;border-radius:99px;height:8px;width:120px;margin-top:8px}}
.bar{{height:8px;border-radius:99px}}
</style></head><body>
<h1>TQQQ 买入信号</h1>
<div class="sub">最后更新：{t['date']} &nbsp;·&nbsp; 每个交易日早上 7:00 自动刷新</div>
<div class="cards">
  <div class="card">
    <div class="label">最新综合评分</div>
    <div class="val" style="color:{tc}">{ts}<span style="font-size:16px;color:#9ca3af">/100</span></div>
    <div class="bar-wrap"><div class="bar" style="width:{ts}%;background:{tc}"></div></div>
  </div>
  <div class="card"><div class="label">TQQQ 现价</div><div class="val">${float(t['tqqq_price']):.2f}</div></div>
  <div class="card"><div class="label">QQQ 回撤</div><div class="val" style="color:#dc2626">{float(t['qqq_dd_pct']):+.1f}%</div></div>
  <div class="card"><div class="label">TQQQ RSI</div><div class="val">{float(t['tqqq_rsi']):.1f}</div></div>
  <div class="card"><div class="label">建议投入</div><div class="val" style="color:#16a34a">${float(t['suggested_amount']):,.0f}</div></div>
  <div class="card"><div class="label">预警状态</div><div style="margin-top:10px">{alert_badge(t['alert_level'])}</div></div>
</div>
<div class="chart-box">
  <h2>历史评分走势</h2>
  <canvas id="scoreChart" height="80"></canvas>
</div>
<table><thead><tr>
  <th>日期</th><th>总分</th><th>TQQQ价</th>
  <th>回撤分</th><th>RSI分</th><th>MACD分</th><th>BB分</th><th>ATR分</th>
  <th>QQQ回撤%</th><th>RSI值</th><th>预警</th><th>信号</th><th>建议金额</th>
</tr></thead><tbody>{table_html}</tbody></table>
<script>
new Chart(document.getElementById('scoreChart'),{{
  type:'line',
  data:{{labels:{chart_labels},datasets:[
    {{label:'综合评分',data:{chart_scores},borderColor:'#4f46e5',
     backgroundColor:'rgba(79,70,229,0.1)',fill:true,tension:0.3,pointRadius:3,borderWidth:2}},
    {{label:'买入门槛(40)',data:Array({n}).fill(40),
     borderColor:'#9ca3af',borderDash:[6,4],pointRadius:0,borderWidth:1}}
  ]}},
  options:{{responsive:true,plugins:{{legend:{{position:'top'}}}},
    scales:{{y:{{min:0,max:100}},x:{{ticks:{{maxTicksLimit:10}}}}}}}}
}})
</script></body></html>""")

# ── 主程序 ─────────────────────────────────────────────────────────────────────
print("拉取数据...")
qqq  = yf.download("QQQ",  period="400d", auto_adjust=True, progress=False, multi_level_index=False).dropna()
tqqq = yf.download("TQQQ", period="400d", auto_adjust=True, progress=False, multi_level_index=False).dropna()

week_dates = [d for d in tqqq.index.date if date(2026,3,23) <= d <= date(2026,3,29)]

existing       = read_rows()
# 强制重新计算本周所有数据
existing       = [r for r in existing if not (date(2026,3,23) <= date.fromisoformat(r["date"]) <= date(2026,3,27))]
existing_dates = {r["date"] for r in existing}

# 持仓快照：周一到周四用原始持仓，周五用加仓后持仓
position_map = {
    date(2026,3,23): {"avg_cost": 50.36, "used": 0},
    date(2026,3,24): {"avg_cost": 50.36, "used": 0},
    date(2026,3,25): {"avg_cost": 50.36, "used": 0},
    date(2026,3,26): {"avg_cost": 50.36, "used": 0},
    date(2026,3,27): {"avg_cost": 46.15, "used": 3500},
    date(2026,3,28): {"avg_cost": 46.15, "used": 3500},
    date(2026,3,29): {"avg_cost": 46.15, "used": 3500},
}

new_rows = []
for d in week_dates:
    ds = str(d)
    if ds in existing_dates:
        print(f"  {ds} 已存在，跳过")
        continue
    idx   = list(tqqq.index.date).index(d)
    q_s   = qqq['Close'].squeeze().iloc[:idx+1]
    t_s   = tqqq['Close'].squeeze().iloc[:idx+1]
    t_df  = tqqq.iloc[:idx+1]
    price = float(t_s.iloc[-1])

    dd     = calc_dd(q_s)
    rv     = calc_rsi(t_s)
    hn, hp = calc_macd(t_s)
    bz     = calc_bb_z(t_s)
    an, am = calc_atr(t_df)

    s_dd,s_rsi,s_mac,s_bb,s_atr,total,rat = compute_scores(dd,rv,hp,hn,bz,an,am)

    pos       = position_map.get(d, {"avg_cost": None, "used": 0})
    pnl       = (price - pos["avg_cost"]) / pos["avg_cost"] * 100 if pos["avg_cost"] else None
    alert     = alert_from_pnl(pnl)
    remaining = max(0.0, TOTAL_BUDGET - pos["used"])
    amount    = 0.0 if alert=="RED" else suggest(total, remaining)
    buy_sig   = total >= 40 and alert != "RED"

    row = {"date":ds,"tqqq_price":f"{price:.2f}","total_score":total,
           "dd_score":s_dd,"rsi_score":s_rsi,"macd_score":s_mac,
           "bb_score":s_bb,"atr_score":s_atr,"qqq_dd_pct":f"{dd:.2f}",
           "tqqq_rsi":f"{rv:.2f}","bb_z":f"{bz:.3f}","atr_ratio":f"{rat:.3f}",
           "suggested_amount":f"{amount:.0f}","alert_level":alert,
           "buy_signal":str(buy_sig)}
    new_rows.append(row)
    print(f"  {ds} → 评分 {total}，价格 ${price:.2f}，建议 ${amount:.0f}")

all_rows = sorted(existing + new_rows, key=lambda r: r["date"])
write_rows(all_rows)
print(f"CSV 已更新，共 {len(all_rows)} 条记录")

generate_html(all_rows)
print(f"HTML 已更新 → {HTML_FILE}")
