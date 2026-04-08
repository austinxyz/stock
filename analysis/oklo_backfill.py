# -*- coding: utf-8 -*-
"""
OKLO 历史技术评分补录
用法: python oklo_backfill.py [天数]
默认补录最近 5 个交易日（不含今日）
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import oklo_score as m
import pandas as pd

days = int(sys.argv[1]) if len(sys.argv) > 1 else 5

print(f"\n正在拉取 OKLO 历史数据（补录最近 {days} 个交易日）...")
df     = m.fetch(m.SYMBOL)
closes = df['Close'].squeeze()

# 取最近 days 个交易日（不含最后一行，即不含今日）
trading_days = df.index[-(days+1):-1]

fund_data, filings = m.load_fundamental_cache()
cash_runway    = fund_data.get("cash_runway_months")
analyst_target = fund_data.get("analyst_target")
days_8k        = m.days_since_latest_8k(filings)

s_runway   = m.score_cash_runway(cash_runway or 0)
s_target   = m.score_analyst_target(analyst_target, float(closes.iloc[-1]))
s_pipeline = m.score_pipeline(days_8k)
s_thesis   = m.score_thesis(False)
fund_score = m.calc_fund_score(s_runway, s_target, s_pipeline, s_thesis)

SEP = "─" * 56
print(f"\n{'日期':<12} {'价格':>8} {'技术分':>6} {'综合分':>6} {'策略':>8}")
print("─" * 56)

for ts in trading_days:
    date_str = str(ts.date())
    # 截断到该日（含）的数据
    sub = closes[:ts]
    sub_df = df[:ts]

    if len(sub) < 30:
        print(f"{date_str:<12} 数据不足，跳过")
        continue

    price = float(sub.iloc[-1])
    pnl_pct = (price - m.AVG_COST) / m.AVG_COST * 100

    dd_pct        = m.calc_drawdown_52w(sub)
    rsi_val       = m.calc_rsi(sub)
    h_now, h_prev = m.calc_macd(sub)
    bb_z          = m.calc_bb_z(sub)

    s_dd   = m.score_drawdown_52w(dd_pct)
    s_rsi  = m.score_rsi(rsi_val)
    s_macd = m.score_macd(h_prev, h_now)
    s_bb   = m.score_bb(bb_z)
    tech_score = m.calc_tech_score(s_dd, s_rsi, s_macd, s_bb)

    total_score = tech_score + fund_score

    sr = m.determine_strategy(
        price=price,
        tech_score=tech_score,
        cash_runway=cash_runway,
        has_negative_event=(s_thesis == 0),
        add_budget=m.ADD_BUDGET
    )
    strategy   = sr["strategy"]
    add_amount = sr["add_amount"]

    # 保存到 CSV
    alert = "RED" if strategy == "STOP_LOSS" else "NONE"
    row = {
        "date": date_str, "price": f"{price:.2f}",
        "tech_score": tech_score, "fund_score": fund_score, "total_score": total_score,
        "dd_score": s_dd, "rsi_score": s_rsi, "macd_score": s_macd, "bb_score": s_bb,
        "dd_pct": f"{dd_pct:.2f}", "rsi_val": f"{rsi_val:.2f}", "bb_z": f"{bb_z:.3f}",
        "strategy": strategy,
        "cash_runway_months": f"{cash_runway:.1f}" if cash_runway is not None else "",
        "analyst_target": f"{analyst_target:.2f}" if analyst_target else "",
        "alert_level": alert,
    }
    m.save_csv(row)

    strat_icon = {"STOP_LOSS": "🔴止损", "ADD": "🟢加仓", "HOLD": "🟡持有"}.get(strategy, strategy)
    arrow = "▲" if pnl_pct >= 0 else "▼"
    print(f"{date_str:<12} ${price:>7.2f} {tech_score:>5}/50 {total_score:>5}/100  {strat_icon}")

print(SEP)

# 用最后一日数据重新生成 HTML（传入今日 oklo_score 的完整参数）
last_ts   = trading_days[-1]
last_sub  = closes[:last_ts]
last_df   = df[:last_ts]
last_price = float(last_sub.iloc[-1])
last_pnl   = (last_price - m.AVG_COST) / m.AVG_COST * 100
last_dd    = m.calc_drawdown_52w(last_sub)
last_rsi   = m.calc_rsi(last_sub)
last_hn, last_hp = m.calc_macd(last_sub)
last_bb    = m.calc_bb_z(last_sub)
ls_dd   = m.score_drawdown_52w(last_dd)
ls_rsi  = m.score_rsi(last_rsi)
ls_macd = m.score_macd(last_hp, last_hn)
ls_bb   = m.score_bb(last_bb)
l_tech  = m.calc_tech_score(ls_dd, ls_rsi, ls_macd, ls_bb)
l_total = l_tech + fund_score
l_sr    = m.determine_strategy(last_price, l_tech, cash_runway, s_thesis == 0, m.ADD_BUDGET)

m.generate_html(
    str(last_ts.date()), last_price, last_pnl, l_tech, fund_score, l_total,
    ls_dd, ls_rsi, ls_macd, ls_bb, last_dd, last_rsi, last_bb,
    fund_data, filings, cash_runway, analyst_target, days_8k,
    s_runway, s_target, s_pipeline, s_thesis,
    l_sr["strategy"], l_sr["add_amount"], l_sr["reasons"]
)

print(f"\n  已更新 CSV → {m.CSV_FILE}")
print(f"  已更新报告 → {m.HTML_FILE}\n")
