# -*- coding: utf-8 -*-
"""
OKLO 月度持仓风险报告
用法: python analysis/oklo_monthly.py
每月月初手动运行，同时刷新基本面缓存。
"""
import sys, io, os, json
if sys.stdout and hasattr(sys.stdout, 'buffer') and __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oklo_score as m
from datetime import datetime

MONTHLY_HTML = os.path.join(m.REPORT_DIR, "oklo_monthly_report.html")


def _scenario_rows(price: float) -> str:
    total_value = m.SHARES * price
    html = ""
    for label, pct, advice, warn in [
        ("+30% 上涨", +0.30, "考虑部分止盈，评估加仓需求", False),
        ("轻度回调", -0.15, "正常持有，可小量加仓", False),
        ("中度下跌", -0.30, "评估基本面，谨慎加仓", True),
        ("重度下跌", -0.40, "触发止损区域，立即评估", True),
    ]:
        new_price   = price * (1 + pct)
        value_delta = total_value * pct
        at_stop     = new_price <= m.STOP_LOSS_PRICE
        flag = " 🚨 触及止损" if at_stop else (" ⚠️" if warn else "")
        color = "#dc2626" if pct < 0 else "#16a34a"
        html += (
            f'<tr>'
            f'<td>{label}</td>'
            f'<td style="color:{color}">{pct*100:+.0f}%</td>'
            f'<td style="color:{color}">${value_delta:,.0f}</td>'
            f'<td>${new_price:.2f}</td>'
            f'<td>{advice}{flag}</td>'
            f'</tr>'
        )
    return html


def generate_monthly_html(price: float, today: str, fund_data: dict, filings: list) -> None:
    total_value    = m.SHARES * price
    total_cost     = m.SHARES * m.AVG_COST
    unrealized_pnl = total_value - total_cost
    pnl_pct        = unrealized_pnl / total_cost * 100
    pnl_color      = "#16a34a" if unrealized_pnl >= 0 else "#dc2626"

    stop_distance_pct = (price - m.STOP_LOSS_PRICE) / price * 100

    # 基本面
    runway    = fund_data.get("cash_runway_months")
    analyst_t = fund_data.get("analyst_target")
    upside_pct = ((analyst_t - price) / price * 100) if analyst_t else None

    # 加仓进度（ADD_BUDGET 是剩余可用，不是已用）
    total_add_budget = 5_000      # 原始加仓预算（$3000剩余 + $2000已用）
    used_add_budget  = total_add_budget - m.ADD_BUDGET
    add_pct          = min(100, int(used_add_budget / total_add_budget * 100))

    # 历史记录（最近30天）
    rows       = m.read_csv_rows()
    recent     = sorted(rows, key=lambda r: r["date"], reverse=True)[:30]
    table_rows = ""
    for r in recent:
        score = int(r.get("total_score", 0))
        sc = "#16a34a" if score >= 70 else "#ca8a04" if score >= 50 else "#9ca3af"
        strat = r.get("strategy", "")
        st_color = "#16a34a" if "买入" in strat else "#ca8a04" if "观望" in strat else "#9ca3af"
        table_rows += (
            f'<tr>'
            f'<td>{r["date"]}</td>'
            f'<td style="font-weight:600;color:{sc}">{score}</td>'
            f'<td>{r.get("tech_score","")}</td>'
            f'<td>{r.get("fund_score","")}</td>'
            f'<td>${float(r["price"]):.2f}</td>'
            f'<td style="color:{st_color}">{strat}</td>'
            f'</tr>'
        )

    # SEC 公告
    filing_rows = ""
    for f in (filings or [])[:5]:
        filing_rows += (
            f'<tr>'
            f'<td>{f.get("date","")}</td>'
            f'<td><a href="{f.get("url","")}" target="_blank" '
            f'style="color:#2563eb;text-decoration:none">{f.get("title","")}</a></td>'
            f'</tr>'
        )
    if not filing_rows:
        filing_rows = '<tr><td colspan="2" style="color:#9ca3af;text-align:center">暂无公告数据</td></tr>'

    # 下月建议
    shares_can_add = int(m.ADD_BUDGET * 0.5 / price) if m.ADD_BUDGET > 0 else 0
    next_advice = (
        f"剩余加仓预算 ${m.ADD_BUDGET:,}，建议在综合评分 ≥70 时分批买入。"
        f"下月可参考买入约 {shares_can_add} 股（预算的50%），"
        f"每股成本约 ${price:.2f}，止损设在 ${m.STOP_LOSS_PRICE}。"
        if m.ADD_BUDGET > 0
        else "加仓预算已用完，保持持仓，等待更有利的加仓时机。"
    )

    upside_str = f"{upside_pct:+.1f}%" if upside_pct is not None else "N/A"
    runway_str = f"{runway:.1f} 个月" if runway and runway < 999 else ("充裕" if runway else "N/A")

    html = f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8"><title>OKLO 月度报告</title>
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
.warn{{background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:14px 18px;font-size:13px;line-height:1.7;margin-bottom:16px}}
</style></head><body>
<h1>OKLO 月度持仓报告</h1>
<div class="sub">生成时间：{today} &nbsp;·&nbsp; OKLO 现价 ${price:.2f}</div>

<div class="section">第1节：持仓快照</div>
<div class="cards">
  <div class="card"><div class="label">OKLO 现价</div><div class="val">${price:.2f}</div></div>
  <div class="card">
    <div class="label">持仓市值</div>
    <div class="val">${total_value:,.0f}</div>
    <div style="font-size:11px;color:{pnl_color};margin-top:4px">{'+' if unrealized_pnl>=0 else ''}{pnl_pct:.1f}% 浮{"盈" if unrealized_pnl>=0 else "亏"} ${unrealized_pnl:,.0f}</div>
  </div>
  <div class="card">
    <div class="label">平均成本</div>
    <div class="val">${m.AVG_COST:.2f}</div>
    <div style="font-size:11px;color:#6b7280;margin-top:4px">{m.SHARES} 股</div>
  </div>
  <div class="card">
    <div class="label">止损价</div>
    <div class="val" style="color:#dc2626">${m.STOP_LOSS_PRICE}</div>
    <div style="font-size:11px;color:#6b7280;margin-top:4px">距止损 {stop_distance_pct:.1f}%</div>
  </div>
</div>

<div class="section">第2节：基本面摘要</div>
<div class="cards">
  <div class="card">
    <div class="label">现金跑道</div>
    <div class="val">{runway_str}</div>
    <div style="font-size:11px;color:#6b7280;margin-top:4px">运营现金流覆盖</div>
  </div>
  <div class="card">
    <div class="label">分析师目标价</div>
    <div class="val">${f"{analyst_t:.2f}" if analyst_t else "N/A"}</div>
    <div style="font-size:11px;color:#6b7280;margin-top:4px">上涨空间 {upside_str}</div>
  </div>
</div>
<div style="font-size:11px;color:#9ca3af;margin-top:-12px;margin-bottom:20px">
  基本面数据更新于：{fund_data.get("updated_at","未知")}
</div>

<div class="section">第3节：加仓预算进度</div>
<div style="background:#fff;border-radius:10px;padding:20px 24px;box-shadow:0 1px 4px rgba(0,0,0,.08);margin-bottom:24px">
  <div style="font-size:13px;color:#374151;margin-bottom:4px">
    已用加仓预算：${used_add_budget:,} / ${total_add_budget:,}（{add_pct}%）
  </div>
  <div class="prog-wrap"><div class="prog" style="width:{add_pct}%;background:#f97316"></div></div>
  <div style="margin-top:10px;font-size:13px;color:#6b7280">
    剩余预算：<strong>${m.ADD_BUDGET:,}</strong>
  </div>
</div>

<div class="section">第4节：情景风险分析</div>
<table><thead><tr>
  <th>场景</th><th>涨跌幅</th><th>持仓变化</th><th>目标价格</th><th>建议行动</th>
</tr></thead><tbody>{_scenario_rows(price)}</tbody></table>

<div class="section">第5节：下月加仓建议</div>
<div class="tip">📋 {next_advice}</div>

<div class="section">第6节：近30日评分历史</div>
<table><thead><tr>
  <th>日期</th><th>总分</th><th>技术分</th><th>基本面分</th><th>价格</th><th>策略</th>
</tr></thead><tbody>{table_rows}</tbody></table>

<div class="section">第7节：SEC 8-K 公告</div>
<table><thead><tr>
  <th>日期</th><th>公告</th>
</tr></thead><tbody>{filing_rows}</tbody></table>
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
        filings   = m.fetch_sec_8k()
        m.save_fundamental_cache(fund_data, filings)
        print("  基本面缓存已更新")
    except Exception as e:
        print(f"  基本面拉取失败：{e}，使用缓存")
        fund_data, filings = m.load_fundamental_cache()

    print("正在拉取价格数据...")
    df    = m.fetch(m.SYMBOL)
    price = float(df["Close"].squeeze().iloc[-1])
    today = str(df.index[-1].date())

    total_value    = m.SHARES * price
    unrealized_pnl = total_value - m.SHARES * m.AVG_COST

    SEP = "─" * 56
    print(f"\n{SEP}")
    print(f"  OKLO 月度报告  |  {today}")
    print(SEP)
    print(f"  现价 ${price:.2f}  |  持仓 {m.SHARES} 股")
    print(f"  市值 ${total_value:,.0f}  |  浮{'盈' if unrealized_pnl>=0 else '亏'} ${unrealized_pnl:,.0f}")
    print(f"  止损价 ${m.STOP_LOSS_PRICE}  |  剩余加仓预算 ${m.ADD_BUDGET:,}")
    print(SEP)

    generate_monthly_html(price, today, fund_data, filings)
    print(f"  基本面缓存 → {m.FUNDAMENTAL_FILE}\n")


if __name__ == "__main__":
    main()
