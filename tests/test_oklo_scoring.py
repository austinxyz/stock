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
