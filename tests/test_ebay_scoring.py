# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'analysis'))
import ebay_score as m

# ── RSI 卖出评分 ──
def test_score_rsi_sell_overbought():
    assert m.score_rsi_sell(72) == 15

def test_score_rsi_sell_high():
    assert m.score_rsi_sell(65) == 8

def test_score_rsi_sell_mid():
    assert m.score_rsi_sell(55) == 3

def test_score_rsi_sell_low():
    assert m.score_rsi_sell(40) == 0

# ── 距52周高点 ──
def test_score_dist_52w_near():
    assert m.score_distance_52w_high(-3.0) == 15

def test_score_dist_52w_moderate():
    assert m.score_distance_52w_high(-10.0) == 8

def test_score_dist_52w_far():
    assert m.score_distance_52w_high(-20.0) == 3

def test_score_dist_52w_very_far():
    assert m.score_distance_52w_high(-40.0) == 0

# ── 布林带 ──
def test_score_bb_sell_high():
    assert m.score_bb_sell(2.5) == 10

def test_score_bb_sell_moderate():
    assert m.score_bb_sell(1.7) == 5

def test_score_bb_sell_low():
    assert m.score_bb_sell(0.5) == 0

# ── MACD ──
def test_score_macd_sell_zero_cross():
    assert m.score_macd_sell(h_prev=0.5, h_now=-0.1) == 10

def test_score_macd_sell_shrinking_top():
    assert m.score_macd_sell(h_prev=0.8, h_now=0.3) == 10

def test_score_macd_sell_expanding_positive():
    assert m.score_macd_sell(h_prev=0.3, h_now=0.5) == 5

def test_score_macd_sell_negative_expanding():
    assert m.score_macd_sell(h_prev=-0.5, h_now=-0.8) == 0

def test_score_macd_sell_bullish_cross():
    # h_prev < 0, h_now > 0 = bullish zero-cross = NOT a sell signal
    assert m.score_macd_sell(h_prev=-0.2, h_now=0.1) == 0

# ── calc_tech_score ──
def test_calc_tech_score_max():
    assert m.calc_tech_score(15, 15, 10, 10) == 50

def test_calc_tech_score_zero():
    assert m.calc_tech_score(0, 0, 0, 0) == 0

# ── 分析师目标价上涨空间 ──
def test_score_analyst_upside_near():
    assert m.score_analyst_upside(91.0, 90.0) == 15   # 1.1% upside

def test_score_analyst_upside_moderate():
    assert m.score_analyst_upside(100.0, 90.0) == 8   # 11.1% upside

def test_score_analyst_upside_large():
    assert m.score_analyst_upside(112.0, 90.0) == 3   # 24.4% upside

def test_score_analyst_upside_very_large():
    assert m.score_analyst_upside(130.0, 90.0) == 0   # 44% upside

def test_score_analyst_upside_no_data():
    assert m.score_analyst_upside(0, 90.0) == 0

# ── 市盈率 ──
def test_score_pe_very_high():
    assert m.score_pe(25.0) == 15

def test_score_pe_high():
    assert m.score_pe(18.0) == 8

def test_score_pe_moderate():
    assert m.score_pe(14.0) == 3

def test_score_pe_low():
    assert m.score_pe(10.0) == 0

def test_score_pe_negative():
    assert m.score_pe(-5.0) == 0

# ── 收入增速 ──
def test_score_revenue_growth_declining():
    assert m.score_revenue_growth(-0.02) == 10

def test_score_revenue_growth_slow():
    assert m.score_revenue_growth(0.03) == 5

def test_score_revenue_growth_normal():
    assert m.score_revenue_growth(0.08) == 0

# ── 分析师评级 ──
def test_score_analyst_rating_bearish():
    assert m.score_analyst_rating(3.8) == 10

def test_score_analyst_rating_neutral():
    assert m.score_analyst_rating(2.8) == 5

def test_score_analyst_rating_bullish():
    assert m.score_analyst_rating(2.0) == 0

# ── calc_fund_score ──
def test_calc_fund_score_max():
    assert m.calc_fund_score(15, 15, 10, 10) == 50

def test_calc_fund_score_zero():
    assert m.calc_fund_score(0, 0, 0, 0) == 0

# ── determine_sell_strategy ──
def test_strategy_sell_rsu_first():
    r = m.determine_sell_strategy(
        total_score=75, rsu_shares=1016, espp_shares=1957,
        price=90.0, rsu_avg_cost=70.0, espp_avg_cost=30.0,
        tax_rate=0.321, annual_remaining=40_000,
    )
    assert r["action"] == "SELL"
    assert r["pool"] == "RSU"
    assert r["shares"] > 0
    assert abs(r["capital_gain"] - r["shares"] * (90.0 - 70.0)) < 0.01
    assert abs(r["tax_estimate"] - r["capital_gain"] * 0.321) < 0.01
    assert abs(r["net_proceeds"] - (r["proceeds"] - r["tax_estimate"])) < 0.01

def test_strategy_wait():
    r = m.determine_sell_strategy(
        total_score=55, rsu_shares=1016, espp_shares=1957,
        price=90.0, rsu_avg_cost=70.0, espp_avg_cost=30.0,
        tax_rate=0.321, annual_remaining=40_000,
    )
    assert r["action"] == "WAIT"
    assert r["shares"] > 0

def test_strategy_hold():
    r = m.determine_sell_strategy(
        total_score=40, rsu_shares=1016, espp_shares=1957,
        price=90.0, rsu_avg_cost=70.0, espp_avg_cost=30.0,
        tax_rate=0.321, annual_remaining=40_000,
    )
    assert r["action"] == "HOLD"
    assert r["shares"] == 0

def test_strategy_espp_when_rsu_empty():
    r = m.determine_sell_strategy(
        total_score=75, rsu_shares=0, espp_shares=1957,
        price=90.0, rsu_avg_cost=70.0, espp_avg_cost=30.0,
        tax_rate=0.321, annual_remaining=40_000,
    )
    assert r["pool"] == "ESPP"
    assert abs(r["capital_gain"] - r["shares"] * (90.0 - 30.0)) < 0.01

def test_strategy_no_annual_budget():
    r = m.determine_sell_strategy(
        total_score=75, rsu_shares=1016, espp_shares=1957,
        price=90.0, rsu_avg_cost=70.0, espp_avg_cost=30.0,
        tax_rate=0.321, annual_remaining=0,
    )
    assert r["action"] == "HOLD"
    assert r["shares"] == 0
