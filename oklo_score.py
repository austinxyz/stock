# -*- coding: utf-8 -*-
"""
OKLO 个股买入信号评分脚本
用法:
  python oklo_score.py          # 每日快跑（技术面 + 缓存基本面）
  python oklo_score.py --full   # 深度分析（重新拉取基本面 + SEC 公告）
"""

import sys, io, os, csv, json, argparse
from datetime import datetime, timedelta
if sys.stdout and hasattr(sys.stdout, 'buffer') and __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import yfinance as yf
import pandas as pd
import numpy as np
import requests

# ── 用户参数 ────────────────────────────────────────────────────────────────────
SYMBOL         = "OKLO"
SHARES         = 80
AVG_COST       = 115.38
STOP_LOSS_PCT  = 0.70          # 最大亏损容忍（70%）
STOP_LOSS_PRICE = round(AVG_COST * (1 - STOP_LOSS_PCT), 2)  # $34.61
ADD_BUDGET     = 5_000
LOOKBACK_DAYS  = 400

SCRIPT_DIR       = os.path.dirname(os.path.abspath(__file__))
CSV_FILE         = os.path.join(SCRIPT_DIR, "oklo_history.csv")
HTML_FILE        = os.path.join(SCRIPT_DIR, "oklo_report.html")
FUNDAMENTAL_FILE = os.path.join(SCRIPT_DIR, "oklo_fundamental.json")

CSV_FIELDS = [
    "date", "price", "tech_score", "fund_score", "total_score",
    "dd_score", "rsi_score", "macd_score", "bb_score",
    "dd_pct", "rsi_val", "bb_z", "strategy",
    "cash_runway_months", "analyst_target", "alert_level"
]

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--full", action="store_true", help="重新拉取基本面和SEC公告")
    return p.parse_args()
