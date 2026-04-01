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

# ── calc_tech_score ──
def test_calc_tech_score_max():
    assert m.calc_tech_score(15, 15, 10, 10) == 50

def test_calc_tech_score_zero():
    assert m.calc_tech_score(0, 0, 0, 0) == 0
