# -*- coding: utf-8 -*-

def test_config_constants():
    """oklo_score 模块应暴露核心配置常量"""
    import oklo_score as m
    assert m.SYMBOL == "OKLO"
    assert m.SHARES == 80
    assert m.AVG_COST == 115.38
    assert m.STOP_LOSS_PRICE == round(m.AVG_COST * (1 - m.STOP_LOSS_PCT), 2)
    assert m.ADD_BUDGET == 5_000

import pandas as pd
import numpy as np

def _make_closes(values):
    return pd.Series(values, dtype=float)

def test_calc_rsi_oversold():
    from oklo_score import calc_rsi
    closes = _make_closes([100] + [100 - i * 2 for i in range(1, 30)])
    rsi = calc_rsi(closes)
    assert 0 <= rsi <= 35, f"expected oversold RSI, got {rsi}"

def test_calc_rsi_overbought():
    from oklo_score import calc_rsi
    closes = _make_closes([100] + [100 + i * 2 for i in range(1, 30)])
    rsi = calc_rsi(closes)
    assert rsi >= 65, f"expected overbought RSI, got {rsi}"

def test_calc_bb_z_negative_when_below_mean():
    from oklo_score import calc_bb_z
    closes = _make_closes([100] * 20 + [70])
    z = calc_bb_z(closes)
    assert z < -1.5, f"expected negative z, got {z}"

def test_calc_drawdown_from_high():
    from oklo_score import calc_drawdown_52w
    closes = _make_closes([50, 100, 80, 60, 40])  # high=100, current=40
    dd = calc_drawdown_52w(closes)
    assert abs(dd - (-60.0)) < 0.1, f"expected -60%, got {dd}"

def test_score_drawdown_52w():
    from oklo_score import score_drawdown_52w
    assert score_drawdown_52w(-55) == 15
    assert score_drawdown_52w(-35) == 10
    assert score_drawdown_52w(-20) == 5
    assert score_drawdown_52w(-10) == 0

def test_score_rsi():
    from oklo_score import score_rsi
    assert score_rsi(20) == 15
    assert score_rsi(30) == 15
    assert score_rsi(32) == 10
    assert score_rsi(44) == 5
    assert score_rsi(50) == 0

def test_score_macd():
    from oklo_score import score_macd
    assert score_macd(-0.5, 0.1) == 10   # 负转正 = 金叉
    assert score_macd(-0.5, -0.3) == 5   # 仍负但收窄
    assert score_macd(-0.5, -0.6) == 0   # 继续扩大
    assert score_macd(0.2, 0.3) == 0     # 都是正值，无买入信号

def test_score_bb():
    from oklo_score import score_bb
    assert score_bb(-2.5) == 10
    assert score_bb(-1.7) == 5
    assert score_bb(-1.0) == 0

def test_score_cash_runway():
    from oklo_score import score_cash_runway
    assert score_cash_runway(30)   == 20
    assert score_cash_runway(18)   == 13
    assert score_cash_runway(8)    == 6
    assert score_cash_runway(4)    == 0
    assert score_cash_runway(None) == 0

def test_score_analyst_target():
    from oklo_score import score_analyst_target
    assert score_analyst_target(100, 30)  == 15
    assert score_analyst_target(100, 55)  == 10
    assert score_analyst_target(100, 85)  == 5
    assert score_analyst_target(100, 95)  == 0
    assert score_analyst_target(None, 50) == 0

def test_score_pipeline():
    from oklo_score import score_pipeline
    assert score_pipeline(5)    == 10
    assert score_pipeline(60)   == 5
    assert score_pipeline(100)  == 0
    assert score_pipeline(None) == 0

def test_score_thesis():
    from oklo_score import score_thesis
    assert score_thesis(False) == 5
    assert score_thesis(True)  == 0
