# -*- coding: utf-8 -*-
import importlib, sys, types

def test_config_constants():
    """oklo_score 模块应暴露核心配置常量"""
    import oklo_score as m
    assert m.SYMBOL == "OKLO"
    assert m.SHARES == 80
    assert m.AVG_COST == 115.38
    assert m.STOP_LOSS_PRICE == round(115.38 * 0.30, 2)
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
