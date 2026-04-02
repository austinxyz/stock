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
