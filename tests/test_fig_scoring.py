# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'analysis'))
import fig_score as m

# ── RSI 持仓评分 ──
def test_score_rsi_hold_healthy():
    assert m.score_rsi_hold(60) == 15

def test_score_rsi_hold_neutral():
    assert m.score_rsi_hold(42) == 8

def test_score_rsi_hold_overbought():
    assert m.score_rsi_hold(75) == 8

def test_score_rsi_hold_boundary_70():
    assert m.score_rsi_hold(70) == 15   # upper edge of healthy range

def test_score_rsi_hold_weak():
    assert m.score_rsi_hold(28) == 3

# ── MACD ──
def test_score_macd_hold_golden_cross():
    assert m.score_macd_hold(h_prev=-0.2, h_now=0.1) == 10

def test_score_macd_hold_expanding_positive():
    assert m.score_macd_hold(h_prev=0.3, h_now=0.6) == 10

def test_score_macd_hold_shrinking_positive():
    assert m.score_macd_hold(h_prev=0.6, h_now=0.3) == 5

def test_score_macd_hold_negative():
    assert m.score_macd_hold(h_prev=-0.5, h_now=-0.8) == 0

# ── 价格 vs 200日均线 ──
def test_score_ma200_above():
    assert m.score_ma200(price=100, ma200=90) == 10

def test_score_ma200_below():
    assert m.score_ma200(price=80, ma200=90) == 0

# ── 52周回撤 ──
def test_score_drawdown_near_high():
    assert m.score_drawdown(-5) == 5

def test_score_drawdown_moderate():
    assert m.score_drawdown(-20) == 3

def test_score_drawdown_deep():
    assert m.score_drawdown(-35) == 1

def test_score_drawdown_severe():
    assert m.score_drawdown(-50) == 0

# ── calc_tech_score ──
def test_calc_tech_score_max():
    assert m.calc_tech_score(15, 10, 10, 5) == 40

def test_calc_tech_score_zero():
    assert m.calc_tech_score(0, 0, 0, 0) == 0

# ── 收入增速 ──
def test_score_revenue_growth_strong():
    assert m.score_revenue_growth(0.25) == 20

def test_score_revenue_growth_healthy():
    assert m.score_revenue_growth(0.12) == 13

def test_score_revenue_growth_slow():
    assert m.score_revenue_growth(0.06) == 6

def test_score_revenue_growth_flat():
    assert m.score_revenue_growth(0.02) == 0

# ── 分析师目标价上涨空间 ──
def test_score_upside_strong():
    assert m.score_upside(130.0, 100.0) == 20   # 30% upside

def test_score_upside_moderate():
    assert m.score_upside(118.0, 100.0) == 13   # 18% upside

def test_score_upside_small():
    assert m.score_upside(106.0, 100.0) == 6    # 6% upside

def test_score_upside_none():
    assert m.score_upside(102.0, 100.0) == 0    # 2% upside
    assert m.score_upside(0, 100.0) == 0        # no target

# ── 分析师评级 ──
def test_score_analyst_rating_strong_buy():
    assert m.score_analyst_rating(1.8) == 20

def test_score_analyst_rating_buy():
    assert m.score_analyst_rating(2.3) == 13

def test_score_analyst_rating_hold():
    assert m.score_analyst_rating(2.8) == 6

def test_score_analyst_rating_sell():
    assert m.score_analyst_rating(3.5) == 0

# ── calc_fund_score ──
def test_calc_fund_score_max():
    assert m.calc_fund_score(20, 20, 20) == 60

def test_calc_fund_score_zero():
    assert m.calc_fund_score(0, 0, 0) == 0

# ── determine_recommendation ──
def test_recommendation_hold_rank1():
    r = m.determine_recommendation(fig_rank=1, fig_score=70)
    assert r["action"] == "HOLD"

def test_recommendation_hold_rank2():
    r = m.determine_recommendation(fig_rank=2, fig_score=65)
    assert r["action"] == "HOLD"

def test_recommendation_watch_rank3():
    r = m.determine_recommendation(fig_rank=3, fig_score=60)
    assert r["action"] == "WATCH"

def test_recommendation_sell_rank4_low_score():
    r = m.determine_recommendation(fig_rank=4, fig_score=48)
    assert r["action"] == "SELL"

def test_recommendation_watch_rank4_high_score():
    r = m.determine_recommendation(fig_rank=4, fig_score=58)
    assert r["action"] == "WATCH"

def test_recommendation_sell_rank5():
    r = m.determine_recommendation(fig_rank=5, fig_score=40)
    assert r["action"] == "SELL"

# ── data layer ──────────────────────────────────────────────────────────────────
import pytest, tempfile, os, json, csv as _csv
from datetime import datetime, timedelta

# ── load_fundamental_cache ──
def test_load_fundamental_cache_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(m, 'FUND_FILE', str(tmp_path / 'fund.json'))
    assert m.load_fundamental_cache() == {}

def test_load_fundamental_cache_corrupt(tmp_path, monkeypatch):
    f = tmp_path / 'fund.json'
    f.write_text("not json", encoding="utf-8")
    monkeypatch.setattr(m, 'FUND_FILE', str(f))
    assert m.load_fundamental_cache() == {}

def test_load_fundamental_cache_valid(tmp_path, monkeypatch):
    f = tmp_path / 'fund.json'
    data = {"FIG": {"revenue_growth": 0.25}}
    f.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(m, 'FUND_FILE', str(f))
    assert m.load_fundamental_cache() == data

# ── save_fundamental_cache ──
def test_save_fundamental_cache_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(m, 'FUND_FILE', str(tmp_path / 'fund.json'))
    data = {"FIG": {"revenue_growth": 0.15}}
    m.save_fundamental_cache(data)
    assert m.load_fundamental_cache() == data

# ── is_cache_stale ──
def test_is_cache_stale_missing_symbol():
    assert m.is_cache_stale({}) is True

def test_is_cache_stale_fresh():
    now = datetime.now().isoformat()
    cache = {sym: {"updated_at": now} for sym in m.ALL_SYMBOLS}
    assert m.is_cache_stale(cache) is False

def test_is_cache_stale_old():
    old = (datetime.now() - timedelta(days=8)).isoformat()
    cache = {sym: {"updated_at": old} for sym in m.ALL_SYMBOLS}
    assert m.is_cache_stale(cache) is True

def test_is_cache_stale_malformed_date():
    cache = {sym: {"updated_at": "not-a-date"} for sym in m.ALL_SYMBOLS}
    assert m.is_cache_stale(cache) is True

# ── read_csv_rows / save_csv ──
def test_read_csv_rows_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(m, 'CSV_FILE', str(tmp_path / 'history.csv'))
    assert m.read_csv_rows() == []

def test_save_csv_creates_and_reads(tmp_path, monkeypatch):
    monkeypatch.setattr(m, 'CSV_FILE', str(tmp_path / 'history.csv'))
    row = {f: "0" for f in m.CSV_FIELDS}
    row["date"] = "2026-04-01"
    m.save_csv(row)
    rows = m.read_csv_rows()
    assert len(rows) == 1
    assert rows[0]["date"] == "2026-04-01"

def test_save_csv_dedup_by_date(tmp_path, monkeypatch):
    monkeypatch.setattr(m, 'CSV_FILE', str(tmp_path / 'history.csv'))
    row = {f: "0" for f in m.CSV_FIELDS}
    row["date"] = "2026-04-01"
    m.save_csv(row)
    row2 = dict(row)
    row2["total_score"] = "99"
    m.save_csv(row2)
    rows = m.read_csv_rows()
    assert len(rows) == 1
    assert rows[0]["total_score"] == "99"

def test_save_csv_sorted_ascending(tmp_path, monkeypatch):
    monkeypatch.setattr(m, 'CSV_FILE', str(tmp_path / 'history.csv'))
    base = {f: "0" for f in m.CSV_FIELDS}
    for d in ["2026-04-03", "2026-04-01", "2026-04-02"]:
        row = dict(base)
        row["date"] = d
        m.save_csv(row)
    rows = m.read_csv_rows()
    dates = [r["date"] for r in rows]
    assert dates == sorted(dates)

# ── NaN RSI guard ──
def test_score_rsi_hold_nan():
    import math
    assert m.score_rsi_hold(float('nan')) == 0

# ── rank 5 high score still SELL ──
def test_recommendation_sell_rank5_high_score():
    r = m.determine_recommendation(fig_rank=5, fig_score=60)
    assert r["action"] == "SELL"
