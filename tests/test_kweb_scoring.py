# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'analysis'))
import kweb_score as m

# ── 回撤评分 ──
def test_score_drawdown_deep():
    assert m.score_drawdown(-21) == 25

def test_score_drawdown_moderate():
    assert m.score_drawdown(-15) == 15

def test_score_drawdown_shallow():
    assert m.score_drawdown(-5) == 5

def test_score_drawdown_boundary_20():
    assert m.score_drawdown(-20) == 25

def test_score_drawdown_boundary_10():
    assert m.score_drawdown(-10) == 15

# ── RSI 评分 ──
def test_score_rsi_oversold():
    assert m.score_rsi(25) == 20

def test_score_rsi_low():
    assert m.score_rsi(35) == 12

def test_score_rsi_mid():
    assert m.score_rsi(45) == 4

def test_score_rsi_high():
    assert m.score_rsi(60) == 0

def test_score_rsi_boundary_30():
    assert m.score_rsi(30) == 20

def test_score_rsi_boundary_40():
    assert m.score_rsi(40) == 12

def test_score_rsi_boundary_50():
    assert m.score_rsi(50) == 4

# ── MACD 评分 ──
def test_score_macd_golden_cross():
    assert m.score_macd(-0.5, 0.1) == 15

def test_score_macd_negative_narrowing():
    assert m.score_macd(-0.8, -0.3) == 8

def test_score_macd_expanding_positive():
    assert m.score_macd(0.3, 0.8) == 0

def test_score_macd_negative_expanding():
    assert m.score_macd(-0.3, -0.8) == 0

# ── BB Z-score 评分 ──
def test_score_bb_very_low():
    assert m.score_bb(-2.5) == 15

def test_score_bb_low():
    assert m.score_bb(-1.7) == 8

def test_score_bb_neutral():
    assert m.score_bb(0.5) == 0

def test_score_bb_boundary_2():
    assert m.score_bb(-2.0) == 15

def test_score_bb_boundary_1_5():
    assert m.score_bb(-1.5) == 8

# ── FXI vs MA200 评分 ──
def test_score_fxi_ma200_above():
    assert m.score_fxi_ma200(3.0) == 15

def test_score_fxi_ma200_near():
    assert m.score_fxi_ma200(-3.0) == 8

def test_score_fxi_ma200_below():
    assert m.score_fxi_ma200(-6.0) == 0

def test_score_fxi_ma200_boundary_zero():
    assert m.score_fxi_ma200(0.0) == 15

def test_score_fxi_ma200_boundary_minus5():
    assert m.score_fxi_ma200(-5.0) == 8

# ── FXI 20日动量评分 ──
def test_score_fxi_momentum_strong():
    assert m.score_fxi_momentum(4.0) == 10

def test_score_fxi_momentum_positive():
    assert m.score_fxi_momentum(1.5) == 5

def test_score_fxi_momentum_negative():
    assert m.score_fxi_momentum(-2.0) == 0

def test_score_fxi_momentum_boundary_3():
    assert m.score_fxi_momentum(3.0) == 10

def test_score_fxi_momentum_boundary_zero():
    assert m.score_fxi_momentum(0.0) == 5
