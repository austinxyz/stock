# -*- coding: utf-8 -*-
"""
EBAY 月度持仓风险报告
用法: python analysis/ebay_monthly.py
每月月初手动运行，同时刷新基本面缓存。
"""
import sys, io, os, json
if sys.stdout and hasattr(sys.stdout, 'buffer') and __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ebay_score as m
from datetime import datetime
from collections import defaultdict

MONTHLY_HTML = os.path.join(m.REPORT_DIR, "ebay_monthly_report.html")


def _scenario_rows(price: float) -> str:
    total_shares = m.ESPP_SHARES + m.RSU_SHARES
    total_value  = total_shares * price
    html = ""
    for label, pct, advice in [
        ("轻度回调", -0.15, "正常执行卖出计划"),
        ("中度下跌", -0.30, "加快卖出节奏"),
        ("重度下跌", -0.40, "立即评估，加速清仓"),
    ]:
        loss      = total_value * pct
        new_price = price * (1 + pct)
        flag      = " ⚠️" if pct <= -0.30 else ""
        html += (
            f'<tr><td>{label}</td>'
            f'<td style="color:#dc2626">{pct*100:.0f}%</td>'
            f'<td style="color:#dc2626">${loss:,.0f}</td>'
            f'<td>${new_price:.2f}</td>'
            f'<td>{advice}{flag}</td></tr>'
        )
    return html


def generate_monthly_html(price: float, today: str, sell_log: list) -> None:
    total_sold       = m.calc_total_sold(sell_log)
    annual_remaining = m.calc_annual_remaining(sell_log)
    year_str         = str(datetime.now().year)
    year_sold        = m.ANNUAL_BUDGET - annual_remaining
    remaining_target = m.SELL_TARGET - total_sold

    progress_pct = min(100, int(total_sold / m.SELL_TARGET * 100))
    year_pct     = min(100, int(year_sold / m.ANNUAL_BUDGET * 100))

    espp_value  = m.ESPP_SHARES * price
    rsu_value   = m.RSU_SHARES  * price
    total_value = espp_value + rsu_value
    total_gain  = (m.ESPP_SHARES * (price - m.ESPP_AVG_COST)
                   + m.RSU_SHARES * (price - m.RSU_AVG_COST))

    # 今年资本利得和税务
    year_cg      = sum(float(r.get("capital_gain", 0)) for r in sell_log
                       if r.get("date", "").startswith(year_str))
    year_tax_est = year_cg * m.TAX_RATE_LTCG

    # 下月建议金额（剩余目标 / 剩余月数）
    years_used   = len({r.get("date", "")[:4] for r in sell_log if r.get("date", "")})
    years_left   = max(1, 3 - years_used)
    monthly_sugg = remaining_target / (years_left * 12)
    pool_next    = "RSU" if m.RSU_SHARES > 0 else "ESPP"

    # 卖出记录表
    log_rows = ""
    for r in sorted(sell_log, key=lambda x: x.get("date", ""), reverse=True):
        log_rows += (
            f'<tr><td>{r.get("date","")}</td>'
            f'<td>{r.get("pool","")}</td>'
            f'<td>{r.get("shares","")}</td>'
            f'<td>${float(r.get("price",0)):.2f}</td>'
            f'<td>${float(r.get("proceeds",0)):,.0f}</td>'
            f'<td style="color:#dc2626">${float(r.get("tax_estimate",0)):,.0f}</td>'
            f'<td>{r.get("notes","")}</td></tr>'
        )
    if not log_rows:
        log_rows = '<tr><td colspan="7" style="text-align:center;color:#9ca3af">暂无卖出记录</td></tr>'

    gain_color = "#16a34a" if total_gain >= 0 else "#dc2626"

    html = f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8"><title>EBAY 月度报告</title>
<style>
body{{font-family:-apple-system,sans-serif;background:#f9fafb;margin:0;padding:24px;color:#111}}
h1{{font-size:22px;font-weight:700;margin-bottom:4px}}
.sub{{color:#6b7280;font-size:13px;margin-bottom:24px}}
.section{{font-size:16px;font-weight:700;margin:28px 0 14px;padding-bottom:6px;border-bottom:2px solid #e5e7eb}}
.cards{{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:20px}}
.card{{background:#fff;border-radius:10px;padding:16px 20px;box-shadow:0 1px 4px rgba(0,0,0,.08);min-width:140px}}
.card .label{{font-size:12px;color:#6b7280;margin-bottom:4px}}
.card .val{{font-size:24px;font-weight:700}}
.prog-wrap{{background:#e5e7eb;border-radius:99px;height:12px;margin:6px 0 2px}}
.prog{{height:12px;border-radius:99px}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,.08);overflow:hidden;margin-bottom:24px}}
th{{background:#f3f4f6;padding:10px 12px;text-align:left;font-size:12px;color:#374151}}
td{{padding:8px 12px;font-size:13px;border-top:1px solid #f3f4f6}}
.tip{{background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:14px 18px;font-size:13px;line-height:1.7;margin-bottom:16px}}
</style></head><body>
<h1>EBAY 月度持仓报告</h1>
<div class="sub">生成时间：{today} &nbsp;·&nbsp; EBAY 现价 ${price:.2f}</div>

<div class="section">第1节：持仓快照</div>
<div class="cards">
  <div class="card"><div class="label">EBAY 现价</div><div class="val">${price:.2f}</div></div>
  <div class="card">
    <div class="label">总持仓市值</div><div class="val">${total_value:,.0f}</div>
    <div style="font-size:11px;color:{gain_color};margin-top:4px">{'+' if total_gain>=0 else ''}${total_gain:,.0f} 浮盈</div>
  </div>
  <div class="card">
    <div class="label">ESPP</div><div class="val">${espp_value:,.0f}</div>
    <div style="font-size:11px;color:#6b7280;margin-top:4px">{m.ESPP_SHARES}股 @ ${m.ESPP_AVG_COST}</div>
  </div>
  <div class="card">
    <div class="label">RSU</div><div class="val">${rsu_value:,.0f}</div>
    <div style="font-size:11px;color:#6b7280;margin-top:4px">{m.RSU_SHARES}股 @ ${m.RSU_AVG_COST}</div>
  </div>
</div>

<div class="section">第2节：卖出进度</div>
<div style="background:#fff;border-radius:10px;padding:20px 24px;box-shadow:0 1px 4px rgba(0,0,0,.08);margin-bottom:24px">
  <div style="margin-bottom:14px">
    <div style="font-size:13px;color:#374151;margin-bottom:4px">
      3年总目标：${total_sold:,.0f} / ${m.SELL_TARGET:,}（{progress_pct}%）
    </div>
    <div class="prog-wrap"><div class="prog" style="width:{progress_pct}%;background:#2563eb"></div></div>
  </div>
  <div>
    <div style="font-size:13px;color:#374151;margin-bottom:4px">
      今年预算：${year_sold:,.0f} / ${m.ANNUAL_BUDGET:,}（{year_pct}%）
    </div>
    <div class="prog-wrap"><div class="prog" style="width:{year_pct}%;background:#16a34a"></div></div>
  </div>
  <div style="margin-top:12px;font-size:13px;color:#6b7280">
    剩余目标：${remaining_target:,.0f} &nbsp;|&nbsp; 今年剩余预算：${annual_remaining:,.0f}
  </div>
</div>

<div class="section">第3节：税务估算（{year_str}年）</div>
<div class="cards">
  <div class="card"><div class="label">今年已实现资本利得</div><div class="val">${year_cg:,.0f}</div></div>
  <div class="card">
    <div class="label">预估税款（32.1%）</div>
    <div class="val" style="color:#dc2626">${year_tax_est:,.0f}</div>
  </div>
  <div class="card">
    <div class="label">今年剩余可卖（预算内）</div>
    <div class="val" style="color:#16a34a">${annual_remaining:,.0f}</div>
  </div>
</div>

<div class="section">第4节：情景风险分析</div>
<table><thead><tr>
  <th>场景</th><th>跌幅</th><th>持仓损失</th><th>跌后股价</th><th>建议行动</th>
</tr></thead><tbody>{_scenario_rows(price)}</tbody></table>

<div class="section">第5节：下月建议</div>
<div class="tip">
  📋 按当前节奏，建议下月卖出约 <strong>${monthly_sugg:,.0f}</strong>。<br>
  建议分 2 次执行，每次约 ${monthly_sugg/2:,.0f}，在每日综合评分 ≥60 时操作。<br>
  优先卖出 <strong>{pool_next}</strong>（税负更低）。<br>
  RSU 每股税款约 ${(price - m.RSU_AVG_COST) * m.TAX_RATE_LTCG:.2f}，
  ESPP 每股税款约 ${(price - m.ESPP_AVG_COST) * m.TAX_RATE_LTCG:.2f}。
</div>

<div class="section">卖出记录</div>
<table><thead><tr>
  <th>日期</th><th>池子</th><th>股数</th><th>价格</th><th>金额</th><th>预估税款</th><th>备注</th>
</tr></thead><tbody>{log_rows}</tbody></table>
</body></html>"""

    tmp = MONTHLY_HTML + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(html)
    os.replace(tmp, MONTHLY_HTML)
    print(f"  月度报告 → {MONTHLY_HTML}")


def main():
    print("\n正在拉取基本面数据（月度模式，重新获取）...")
    try:
        fund_data = m.fetch_fundamentals()
        m.save_fundamental_cache(fund_data)
        print("  基本面缓存已更新")
    except Exception as e:
        print(f"  基本面拉取失败：{e}，使用缓存")

    print("正在拉取价格数据...")
    df    = m.fetch(m.SYMBOL)
    price = float(df["Close"].squeeze().iloc[-1])
    today = str(df.index[-1].date())

    m.init_sell_log()
    sell_log = m.read_sell_log()

    total_sold       = m.calc_total_sold(sell_log)
    annual_remaining = m.calc_annual_remaining(sell_log)
    year_sold        = m.ANNUAL_BUDGET - annual_remaining

    SEP = "─" * 56
    print(f"\n{SEP}")
    print(f"  EBAY 月度报告  |  {today}")
    print(SEP)
    print(f"  现价 ${price:.2f}  |  持仓 {m.ESPP_SHARES + m.RSU_SHARES}股")
    print(f"  3年目标进度: ${total_sold:,.0f} / ${m.SELL_TARGET:,}")
    print(f"  今年: ${year_sold:,.0f} / ${m.ANNUAL_BUDGET:,}  剩余: ${annual_remaining:,.0f}")
    print(SEP)

    generate_monthly_html(price, today, sell_log)
    print(f"  基本面缓存 → {m.FUND_FILE}\n")


if __name__ == "__main__":
    main()
