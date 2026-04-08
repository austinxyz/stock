# OKLO 个股分析程序 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建 `oklo_score.py`，每日输出技术评分，`--full` 模式额外拉取基本面 + SEC 公告，生成持仓策略建议（止损/持有/加仓）和 HTML 报告，并入每日定时任务。

**Architecture:** 单文件脚本，两种运行模式（每日快跑 / `--full` 深度分析）。基本面数据缓存到 `oklo_fundamental.json`，技术面每日计算。HTML 报告包含 7 个区块，策略建议以三栏并列展示。

**Tech Stack:** Python 3, yfinance, pandas, numpy, requests (SEC EDGAR API), json, csv

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `oklo_score.py` | 新建 | 主脚本：数据拉取、评分、策略逻辑、HTML 生成 |
| `tests/test_oklo_scoring.py` | 新建 | 纯函数单元测试（评分 + 策略逻辑） |
| `oklo_fundamental.json` | 自动生成 | 基本面缓存 |
| `oklo_history.csv` | 自动生成 | 每日评分历史 |
| `oklo_report.html` | 自动生成 | 可视化报告 |
| `run_daily.bat` | 新建 | 替代 run_tqqq.bat，依次运行两个脚本 |

---

## Task 1: 项目骨架 + 配置 + CLI 参数解析

**Files:**
- Create: `oklo_score.py`
- Create: `tests/test_oklo_scoring.py`

- [ ] **Step 1: 新建 tests 目录和空测试文件**

```bash
mkdir tests
touch tests/__init__.py
touch tests/test_oklo_scoring.py
```

- [ ] **Step 2: 写第一个测试（验证配置常量存在）**

在 `tests/test_oklo_scoring.py` 写入：

```python
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
```

- [ ] **Step 3: 运行测试，确认失败**

```bash
python -m pytest tests/test_oklo_scoring.py::test_config_constants -v
```
预期：`ModuleNotFoundError` 或 `AttributeError`

- [ ] **Step 4: 新建 `oklo_score.py`，写入配置和 CLI 解析**

```python
# -*- coding: utf-8 -*-
"""
OKLO 个股买入信号评分脚本
用法:
  python oklo_score.py          # 每日快跑（技术面 + 缓存基本面）
  python oklo_score.py --full   # 深度分析（重新拉取基本面 + SEC 公告）
"""

import sys, io, os, csv, json, argparse
from datetime import datetime, timedelta
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
```

- [ ] **Step 5: 运行测试，确认通过**

```bash
python -m pytest tests/test_oklo_scoring.py::test_config_constants -v
```
预期：`PASSED`

- [ ] **Step 6: Commit**

```bash
git add oklo_score.py tests/
git commit -m "feat(oklo): scaffold config, CLI args, and test harness"
```

---

## Task 2: 技术指标计算函数

**Files:**
- Modify: `oklo_score.py`
- Modify: `tests/test_oklo_scoring.py`

- [ ] **Step 1: 写技术指标测试**

在 `tests/test_oklo_scoring.py` 追加：

```python
import pandas as pd
import numpy as np

def _make_closes(values):
    return pd.Series(values, dtype=float)

def test_calc_rsi_oversold():
    from oklo_score import calc_rsi
    # 连续下跌数据应产生低 RSI
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
    # 最后一个价格远低于前20日均值
    closes = _make_closes([100] * 20 + [70])
    z = calc_bb_z(closes)
    assert z < -1.5, f"expected negative z, got {z}"

def test_calc_drawdown_from_high():
    from oklo_score import calc_drawdown_52w
    closes = _make_closes([50, 100, 80, 60, 40])  # high=100, current=40
    dd = calc_drawdown_52w(closes)
    assert abs(dd - (-60.0)) < 0.1, f"expected -60%, got {dd}"
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
python -m pytest tests/test_oklo_scoring.py -k "rsi or bb_z or drawdown" -v
```
预期：`ImportError` 或 `AttributeError`

- [ ] **Step 3: 在 `oklo_score.py` 实现技术指标函数**

在配置常量后追加：

```python
# ── 数据拉取 ───────────────────────────────────────────────────────────────────
def fetch(symbol):
    df = yf.download(symbol, period=f"{LOOKBACK_DAYS}d", auto_adjust=True,
                     progress=False, multi_level_index=False)
    return df.dropna()

# ── 技术指标 ───────────────────────────────────────────────────────────────────
def calc_rsi(closes, period=14):
    delta = closes.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)
    ag = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    al = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = ag / al.replace(0, np.nan)
    return float((100 - 100 / (1 + rs)).iloc[-1])

def calc_macd(closes, fast=12, slow=26, signal=9):
    ml = closes.ewm(span=fast, adjust=False).mean() - closes.ewm(span=slow, adjust=False).mean()
    sl = ml.ewm(span=signal, adjust=False).mean()
    h  = ml - sl
    return float(h.iloc[-1]), float(h.iloc[-2])

def calc_bb_z(closes, period=20):
    w   = closes.iloc[-(period+1):-1]
    std = w.std()
    return float((closes.iloc[-1] - w.mean()) / std) if std else 0.0

def calc_drawdown_52w(closes):
    """当前价格相对过去252个交易日最高价的回撤百分比"""
    lookback = min(252, len(closes) - 1)
    high = closes.iloc[-lookback:-1].max()
    return float((closes.iloc[-1] - high) / high * 100)
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
python -m pytest tests/test_oklo_scoring.py -k "rsi or bb_z or drawdown" -v
```
预期：全部 `PASSED`

- [ ] **Step 5: Commit**

```bash
git add oklo_score.py tests/test_oklo_scoring.py
git commit -m "feat(oklo): add technical indicator calculation functions"
```

---

## Task 3: 技术评分函数

**Files:**
- Modify: `oklo_score.py`
- Modify: `tests/test_oklo_scoring.py`

- [ ] **Step 1: 写评分函数测试**

在 `tests/test_oklo_scoring.py` 追加：

```python
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
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
python -m pytest tests/test_oklo_scoring.py -k "score_" -v
```
预期：`ImportError`

- [ ] **Step 3: 在 `oklo_score.py` 实现评分函数**

```python
# ── 技术评分规则 ────────────────────────────────────────────────────────────────
def score_drawdown_52w(pct):
    """满分 15"""
    if pct <= -50: return 15
    if pct <= -30: return 10
    if pct <= -15: return 5
    return 0

def score_rsi(r):
    """满分 15"""
    if r <= 30: return 15
    if r <= 35: return 10
    if r <= 45: return 5
    return 0

def score_macd(prev, now):
    """满分 10。prev=前日柱，now=今日柱"""
    if prev < 0 and now > 0: return 10   # 金叉
    if now < 0 and now > prev: return 5  # 底部收窄
    return 0

def score_bb(z):
    """满分 10"""
    if z < -2.0: return 10
    if z < -1.5: return 5
    return 0

def calc_tech_score(s_dd, s_rsi, s_macd, s_bb):
    return s_dd + s_rsi + s_macd + s_bb  # 满分 50
```

- [ ] **Step 4: 运行所有测试**

```bash
python -m pytest tests/test_oklo_scoring.py -v
```
预期：全部 `PASSED`

- [ ] **Step 5: Commit**

```bash
git add oklo_score.py tests/test_oklo_scoring.py
git commit -m "feat(oklo): add technical scoring functions with tests"
```

---

## Task 4: 基本面数据拉取与缓存

**Files:**
- Modify: `oklo_score.py`

- [ ] **Step 1: 在 `oklo_score.py` 实现基本面拉取函数**

```python
# ── 基本面数据（yfinance + SEC EDGAR）──────────────────────────────────────────
def fetch_fundamentals():
    """拉取基本面数据，返回 dict。失败时返回空 dict。"""
    info = {}
    try:
        ticker = yf.Ticker(SYMBOL)
        d = ticker.info
        total_cash = d.get("totalCash") or 0
        op_cf      = d.get("operatingCashflow") or 0
        # 现金跑道：现金 / 月均烧钱
        if op_cf < 0:
            runway_months = (total_cash / abs(op_cf)) * 12
        else:
            runway_months = 999  # 正现金流，无跑道压力
        info = {
            "market_cap":       d.get("marketCap"),
            "total_cash":       total_cash,
            "operating_cf":     op_cf,
            "cash_runway_months": round(runway_months, 1),
            "analyst_target":   d.get("targetMeanPrice"),
            "total_revenue":    d.get("totalRevenue"),
            "updated_at":       datetime.now().strftime("%Y-%m-%d"),
        }
    except Exception as e:
        print(f"  [警告] 基本面数据拉取失败: {e}")
    return info

def fetch_sec_8k(cik="0001824920", count=10):
    """
    从 SEC EDGAR 拉取最近 N 条 8-K 公告标题和日期。
    OKLO 的 CIK 为 0001824920。
    返回 list of {"date": str, "title": str, "url": str}
    """
    url = (f"https://data.sec.gov/submissions/CIK{cik}.json")
    headers = {"User-Agent": "personal-stock-tracker admin@example.com"}
    filings = []
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        recent = data.get("filings", {}).get("recent", {})
        forms  = recent.get("form", [])
        dates  = recent.get("filingDate", [])
        accessions = recent.get("accessionNumber", [])
        descriptions = recent.get("primaryDocument", [])
        for i, form in enumerate(forms):
            if form == "8-K" and len(filings) < count:
                acc = accessions[i].replace("-", "")
                filing_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{descriptions[i]}"
                filings.append({
                    "date":  dates[i],
                    "title": f"8-K ({dates[i]})",
                    "url":   filing_url,
                })
    except Exception as e:
        print(f"  [警告] SEC EDGAR 拉取失败: {e}")
    return filings

def load_fundamental_cache():
    """读取缓存文件，返回 (fund_data dict, filings list)"""
    if not os.path.exists(FUNDAMENTAL_FILE):
        return {}, []
    with open(FUNDAMENTAL_FILE, encoding="utf-8") as f:
        cached = json.load(f)
    return cached.get("data", {}), cached.get("filings", [])

def save_fundamental_cache(fund_data, filings):
    with open(FUNDAMENTAL_FILE, "w", encoding="utf-8") as f:
        json.dump({"data": fund_data, "filings": filings}, f, ensure_ascii=False, indent=2)
```

- [ ] **Step 2: 手动冒烟测试**

```bash
python -c "
import oklo_score as m
d = m.fetch_fundamentals()
print('现金跑道:', d.get('cash_runway_months'), '个月')
print('分析师目标价:', d.get('analyst_target'))
filings = m.fetch_sec_8k()
print('8-K条数:', len(filings))
if filings: print('最新:', filings[0])
"
```
预期：打印出现金跑道月数、目标价、至少1条8-K记录（无报错）

- [ ] **Step 3: Commit**

```bash
git add oklo_score.py
git commit -m "feat(oklo): add fundamental data fetch and JSON cache"
```

---

## Task 5: 基本面评分函数

**Files:**
- Modify: `oklo_score.py`
- Modify: `tests/test_oklo_scoring.py`

- [ ] **Step 1: 写基本面评分测试**

在 `tests/test_oklo_scoring.py` 追加：

```python
def test_score_cash_runway():
    from oklo_score import score_cash_runway
    assert score_cash_runway(30)  == 20  # >24个月
    assert score_cash_runway(18)  == 13  # >12个月
    assert score_cash_runway(8)   == 6   # >6个月
    assert score_cash_runway(4)   == 0   # ≤6个月，硬止损

def test_score_analyst_target():
    from oklo_score import score_analyst_target
    assert score_analyst_target(100, 30)  == 15  # 333% > 200%
    assert score_analyst_target(100, 55)  == 10  # 182% > 150%
    assert score_analyst_target(100, 85)  == 5   # upside=118% > 110%
    assert score_analyst_target(100, 95)  == 0   # upside=105% ≤ 110%
    assert score_analyst_target(None, 50) == 0   # 无数据

def test_score_pipeline():
    from oklo_score import score_pipeline
    assert score_pipeline(5)  == 10   # 近30天
    assert score_pipeline(60) == 5    # 近90天
    assert score_pipeline(100) == 0   # 超过90天
    assert score_pipeline(None) == 0  # 无数据

def test_score_thesis():
    from oklo_score import score_thesis
    assert score_thesis(False) == 5  # 无负面事件
    assert score_thesis(True)  == 0  # 有负面事件
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
python -m pytest tests/test_oklo_scoring.py -k "cash_runway or analyst or pipeline or thesis" -v
```
预期：`ImportError`

- [ ] **Step 3: 实现基本面评分函数**

在 `oklo_score.py` 追加：

```python
# ── 基本面评分规则 ──────────────────────────────────────────────────────────────
def score_cash_runway(months):
    """满分 20。months 为现金跑道月数。"""
    if months is None: return 0
    if months > 24: return 20
    if months > 12: return 13
    if months > 6:  return 6
    return 0  # ≤6个月触发硬止损

def score_analyst_target(target, current_price):
    """满分 15。target 为分析师均价目标，current_price 为现价。"""
    if not target or not current_price: return 0
    upside = target / current_price
    if upside > 2.0: return 15
    if upside > 1.5: return 10
    if upside > 1.1: return 5
    return 0

def score_pipeline(days_since_last_filing):
    """满分 10。days_since_last_filing 为距最新合同/LOI类8-K的天数。"""
    if days_since_last_filing is None: return 0
    if days_since_last_filing <= 30: return 10
    if days_since_last_filing <= 90: return 5
    return 0

def score_thesis(has_negative_event):
    """满分 5。has_negative_event=True 表示有监管受阻/合同取消等重大负面。"""
    return 0 if has_negative_event else 5

def calc_fund_score(s_runway, s_target, s_pipeline, s_thesis):
    return s_runway + s_target + s_pipeline + s_thesis  # 满分 50

def days_since_latest_8k(filings):
    """返回最新8-K距今天数，无数据返回None"""
    if not filings:
        return None
    latest_date = datetime.strptime(filings[0]["date"], "%Y-%m-%d")
    return (datetime.now() - latest_date).days
```

- [ ] **Step 4: 运行所有测试**

```bash
python -m pytest tests/test_oklo_scoring.py -v
```
预期：全部 `PASSED`

- [ ] **Step 5: Commit**

```bash
git add oklo_score.py tests/test_oklo_scoring.py
git commit -m "feat(oklo): add fundamental scoring functions with tests"
```

---

## Task 6: 策略逻辑

**Files:**
- Modify: `oklo_score.py`
- Modify: `tests/test_oklo_scoring.py`

- [ ] **Step 1: 写策略逻辑测试**

在 `tests/test_oklo_scoring.py` 追加：

```python
def test_strategy_stop_loss_by_price():
    from oklo_score import determine_strategy
    # 现价低于止损线 $34.61
    result = determine_strategy(
        price=30.0, tech_score=40, cash_runway=18,
        has_negative_event=False, add_budget=5000
    )
    assert result["strategy"] == "STOP_LOSS"
    assert "现价低于止损线" in result["reasons"]["stop_loss"][0]

def test_strategy_stop_loss_by_cash():
    from oklo_score import determine_strategy
    result = determine_strategy(
        price=50.0, tech_score=40, cash_runway=4,
        has_negative_event=False, add_budget=5000
    )
    assert result["strategy"] == "STOP_LOSS"
    assert any("现金跑道" in r for r in result["reasons"]["stop_loss"])

def test_strategy_add():
    from oklo_score import determine_strategy
    result = determine_strategy(
        price=50.0, tech_score=40, cash_runway=18,
        has_negative_event=False, add_budget=5000
    )
    assert result["strategy"] == "ADD"
    assert result["add_amount"] > 0

def test_strategy_hold():
    from oklo_score import determine_strategy
    # 技术分不足，但无止损触发
    result = determine_strategy(
        price=50.0, tech_score=20, cash_runway=18,
        has_negative_event=False, add_budget=5000
    )
    assert result["strategy"] == "HOLD"
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
python -m pytest tests/test_oklo_scoring.py -k "strategy" -v
```
预期：`ImportError`

- [ ] **Step 3: 实现策略逻辑**

在 `oklo_score.py` 追加：

```python
# ── 策略逻辑 ───────────────────────────────────────────────────────────────────
def determine_strategy(price, tech_score, cash_runway, has_negative_event, add_budget):
    """
    返回 dict:
      strategy: "STOP_LOSS" | "ADD" | "HOLD"
      add_amount: float（仅 ADD 时有值）
      reasons: {"stop_loss": [...], "add": [...], "hold": [...]}
    """
    stop_reasons = []
    add_reasons  = []
    hold_reasons = []

    # 止损条件
    if price <= STOP_LOSS_PRICE:
        stop_reasons.append(f"现价低于止损线 ${STOP_LOSS_PRICE}（成本×30%）")
    if cash_runway is not None and cash_runway <= 6:
        stop_reasons.append(f"现金跑道仅剩 {cash_runway:.1f} 个月（<6个月硬止损）")
    if has_negative_event:
        stop_reasons.append("检测到重大负面事件（监管受阻或合同取消）")

    # 加仓条件
    can_add = (
        price > STOP_LOSS_PRICE and
        tech_score >= 35 and
        (cash_runway is None or cash_runway > 12) and
        not has_negative_event
    )
    if can_add:
        add_reasons.append(f"技术评分 {tech_score}/50 ≥ 35（超卖信号）")
        add_reasons.append(f"现金跑道 {cash_runway:.0f} 个月 > 12个月")
        add_reasons.append("无止损触发条件")
    else:
        if tech_score < 35:
            hold_reasons.append(f"技术评分 {tech_score}/50 < 35，信号不足")
        if cash_runway is not None and cash_runway <= 12:
            hold_reasons.append(f"现金跑道 {cash_runway:.0f} 个月，偏紧，不宜追加")

    # 加仓金额
    add_amount = 0.0
    if can_add:
        if tech_score >= 45:
            add_amount = add_budget * 0.40
            add_reasons.append(f"技术分≥45，建议投入预算40%（${add_amount:,.0f}）")
        else:
            add_amount = add_budget * 0.20
            add_reasons.append(f"技术分35-44，建议投入预算20%（${add_amount:,.0f}）")

    if stop_reasons:
        strategy = "STOP_LOSS"
    elif can_add:
        strategy = "ADD"
    else:
        strategy = "HOLD"

    return {
        "strategy":   strategy,
        "add_amount": add_amount,
        "reasons": {
            "stop_loss": stop_reasons,
            "add":       add_reasons,
            "hold":      hold_reasons,
        }
    }
```

- [ ] **Step 4: 运行所有测试**

```bash
python -m pytest tests/test_oklo_scoring.py -v
```
预期：全部 `PASSED`

- [ ] **Step 5: Commit**

```bash
git add oklo_score.py tests/test_oklo_scoring.py
git commit -m "feat(oklo): add strategy decision logic with tests"
```

---

## Task 7: CSV 持久化 + 主程序骨架

**Files:**
- Modify: `oklo_score.py`

- [ ] **Step 1: 实现 CSV 读写和主程序流程**

在 `oklo_score.py` 追加：

```python
# ── CSV 持久化 ──────────────────────────────────────────────────────────────────
def read_csv_rows():
    if not os.path.exists(CSV_FILE):
        return []
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def save_csv(row: dict):
    rows = read_csv_rows()
    rows = [r for r in rows if r["date"] != row["date"]]
    rows.append(row)
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        w.writerows(rows)

# ── 主程序 ─────────────────────────────────────────────────────────────────────
def main():
    args = parse_args()
    print("\n正在拉取价格数据...")
    df     = fetch(SYMBOL)
    closes = df['Close'].squeeze()
    price  = float(closes.iloc[-1])
    today  = str(df.index[-1].date())
    pnl_pct = (price - AVG_COST) / AVG_COST * 100

    # 技术指标
    dd_pct   = calc_drawdown_52w(closes)
    rsi_val  = calc_rsi(closes)
    h_now, h_prev = calc_macd(closes)
    bb_z     = calc_bb_z(closes)

    # 技术评分
    s_dd   = score_drawdown_52w(dd_pct)
    s_rsi  = score_rsi(rsi_val)
    s_macd = score_macd(h_prev, h_now)
    s_bb   = score_bb(bb_z)
    tech_score = calc_tech_score(s_dd, s_rsi, s_macd, s_bb)

    # 基本面（--full 时重新拉取，否则读缓存）
    if args.full:
        print("正在拉取基本面数据（--full 模式）...")
        fund_data = fetch_fundamentals()
        filings   = fetch_sec_8k()
        save_fundamental_cache(fund_data, filings)
    else:
        fund_data, filings = load_fundamental_cache()
        if not fund_data:
            print("  [提示] 无基本面缓存，建议运行 --full 获取完整数据")

    cash_runway    = fund_data.get("cash_runway_months")
    analyst_target = fund_data.get("analyst_target")
    days_8k        = days_since_latest_8k(filings)

    # 基本面评分
    s_runway   = score_cash_runway(cash_runway or 0)
    s_target   = score_analyst_target(analyst_target, price)
    s_pipeline = score_pipeline(days_8k)
    s_thesis   = score_thesis(False)   # 默认无负面；--full 模式后续可扩展
    fund_score = calc_fund_score(s_runway, s_target, s_pipeline, s_thesis)

    total_score = tech_score + fund_score

    # 策略
    sr = determine_strategy(
        price=price,
        tech_score=tech_score,
        cash_runway=cash_runway,
        has_negative_event=(s_thesis == 0),
        add_budget=ADD_BUDGET
    )
    strategy   = sr["strategy"]
    add_amount = sr["add_amount"]
    reasons    = sr["reasons"]

    # 控制台输出
    SEP = "─" * 56
    arrow = "▲" if pnl_pct >= 0 else "▼"
    print(f"\n{SEP}")
    print(f"  OKLO 持仓分析  |  {today}")
    print(SEP)
    print(f"  现价 ${price:.2f}  |  成本 ${AVG_COST:.2f}  |  {arrow} {abs(pnl_pct):.1f}%")
    print(f"  止损线 ${STOP_LOSS_PRICE}  |  距止损 {((price-STOP_LOSS_PRICE)/STOP_LOSS_PRICE*100):+.1f}%")
    print(SEP)
    print(f"  技术评分  {tech_score:>3}/50   基本面  {fund_score:>3}/50   综合  {total_score:>3}/100")
    print(SEP)
    icons = {"STOP_LOSS": "🔴 止损", "ADD": "🟢 加仓", "HOLD": "🟡 持有"}
    print(f"  策略建议: {icons.get(strategy, strategy)}")
    if strategy == "ADD":
        print(f"  建议加仓金额: ${add_amount:,.0f}")
    print(SEP)

    # 保存
    alert = "RED" if strategy == "STOP_LOSS" else "NONE"
    row = {
        "date": today, "price": f"{price:.2f}",
        "tech_score": tech_score, "fund_score": fund_score, "total_score": total_score,
        "dd_score": s_dd, "rsi_score": s_rsi, "macd_score": s_macd, "bb_score": s_bb,
        "dd_pct": f"{dd_pct:.2f}", "rsi_val": f"{rsi_val:.2f}", "bb_z": f"{bb_z:.3f}",
        "strategy": strategy,
        "cash_runway_months": f"{cash_runway:.1f}" if cash_runway else "",
        "analyst_target": f"{analyst_target:.2f}" if analyst_target else "",
        "alert_level": alert,
    }
    save_csv(row)
    generate_html(today, price, pnl_pct, tech_score, fund_score, total_score,
                  s_dd, s_rsi, s_macd, s_bb, dd_pct, rsi_val, bb_z,
                  fund_data, filings, cash_runway, analyst_target, days_8k,
                  s_runway, s_target, s_pipeline, s_thesis,
                  strategy, add_amount, reasons)

    print(f"\n  已保存 → {CSV_FILE}")
    print(f"  报告   → {HTML_FILE}\n")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 冒烟测试（每日模式）**

```bash
python oklo_score.py
```
预期：打印持仓摘要和策略建议，生成 `oklo_history.csv`（提示无基本面缓存）

- [ ] **Step 3: Commit**

```bash
git add oklo_score.py
git commit -m "feat(oklo): add CSV persistence and main program flow"
```

---

## Task 8: HTML 报告生成

**Files:**
- Modify: `oklo_score.py`

- [ ] **Step 1: 实现 `generate_html` 函数**

在 `oklo_score.py` 的 `main()` 函数之前插入（注意 `generate_html` 需在 `main` 调用之前定义）：

```python
# ── HTML 报告 ──────────────────────────────────────────────────────────────────
def generate_html(today, price, pnl_pct, tech_score, fund_score, total_score,
                  s_dd, s_rsi, s_macd, s_bb, dd_pct, rsi_val, bb_z,
                  fund_data, filings, cash_runway, analyst_target, days_8k,
                  s_runway, s_target, s_pipeline, s_thesis,
                  strategy, add_amount, reasons):

    rows = read_csv_rows()
    rows_desc = sorted(rows, key=lambda r: r["date"], reverse=True)
    chart_rows   = sorted(rows, key=lambda r: r["date"])[-60:]
    chart_labels = json.dumps([r["date"] for r in chart_rows])
    chart_tech   = json.dumps([int(r["tech_score"]) for r in chart_rows])
    chart_total  = json.dumps([int(r["total_score"]) for r in chart_rows])

    # 持仓摘요
    market_value   = price * SHARES
    cost_value     = AVG_COST * SHARES
    pnl_dollars    = market_value - cost_value
    dist_stop_pct  = (price - STOP_LOSS_PRICE) / STOP_LOSS_PRICE * 100
    pnl_color      = "#16a34a" if pnl_pct >= 0 else "#dc2626"
    stop_color     = "#16a34a" if price > STOP_LOSS_PRICE * 1.2 else "#ca8a04" if price > STOP_LOSS_PRICE else "#dc2626"

    # 策略配色
    strategy_colors = {"STOP_LOSS": "#dc2626", "ADD": "#16a34a", "HOLD": "#ca8a04"}
    strategy_labels = {"STOP_LOSS": "止损", "ADD": "加仓", "HOLD": "持有"}

    def score_color(s, max_s):
        pct = s / max_s if max_s else 0
        if pct >= 0.8: return "#16a34a"
        if pct >= 0.6: return "#ca8a04"
        if pct >= 0.4: return "#2563eb"
        return "#9ca3af"

    def bar(score, max_score, color):
        pct = int(score / max_score * 100) if max_score else 0
        return (f'<div style="display:flex;align-items:center;gap:8px">'
                f'<div style="flex:1;background:#e5e7eb;border-radius:99px;height:6px">'
                f'<div style="width:{pct}%;height:6px;border-radius:99px;background:{color}"></div></div>'
                f'<span style="font-size:12px;color:#374151;min-width:40px">{score}/{max_score}</span></div>')

    def reasons_list(items, color):
        if not items:
            return '<span style="color:#9ca3af;font-size:12px">无触发条件</span>'
        return "".join(
            f'<div style="font-size:12px;color:{color};margin:2px 0">• {r}</div>'
            for r in items
        )

    # 技术指标卡片
    tech_cards = [
        {"name": "52周回撤", "score": s_dd, "max": 15,
         "current": f"{dd_pct:+.1f}%", "color": "#4f46e5",
         "why": "股价距52周高点回撤越深，相对价值越高，超跌反弹概率越大。",
         "rules": [
             {"cond": "≤ -50%", "pts": 15, "active": dd_pct <= -50},
             {"cond": "≤ -30%", "pts": 10, "active": -50 < dd_pct <= -30},
             {"cond": "≤ -15%", "pts": 5,  "active": -30 < dd_pct <= -15},
             {"cond": "> -15%", "pts": 0,  "active": dd_pct > -15},
         ]},
        {"name": "RSI(14)", "score": s_rsi, "max": 15,
         "current": f"{rsi_val:.1f}", "color": "#0891b2",
         "why": "RSI < 30 为严重超卖，短期反弹概率高；个股超卖比ETF更极端。",
         "rules": [
             {"cond": "≤ 25（极度超卖）", "pts": 15, "active": rsi_val <= 25},
             {"cond": "≤ 35",             "pts": 10, "active": 25 < rsi_val <= 35},
             {"cond": "≤ 45",             "pts": 5,  "active": 35 < rsi_val <= 45},
             {"cond": "> 45",             "pts": 0,  "active": rsi_val > 45},
         ]},
        {"name": "MACD 柱", "score": s_macd, "max": 10,
         "current": ("金叉" if s_macd == 10 else "底部收窄" if s_macd == 5 else "无信号"),
         "color": "#16a34a",
         "why": "MACD柱由负转正是趋势反转信号；柱在负区收窄说明下跌动能减弱。",
         "rules": [
             {"cond": "负转正（金叉）", "pts": 10, "active": s_macd == 10},
             {"cond": "负区收窄",       "pts": 5,  "active": s_macd == 5},
             {"cond": "无信号",         "pts": 0,  "active": s_macd == 0},
         ]},
        {"name": "布林带 z-score", "score": s_bb, "max": 10,
         "current": f"z = {bb_z:.2f}", "color": "#ca8a04",
         "why": "z < -2 说明价格已偏离20日均线2个标准差，统计上均值回归概率高。",
         "rules": [
             {"cond": "z < -2.0", "pts": 10, "active": bb_z < -2.0},
             {"cond": "z < -1.5", "pts": 5,  "active": -2.0 <= bb_z < -1.5},
             {"cond": "z ≥ -1.5", "pts": 0,  "active": bb_z >= -1.5},
         ]},
    ]

    def tech_card_html(c):
        rules_html = "".join(
            f'<tr style="{"background:#f0fdf4;font-weight:600;" if r["active"] else ""}">'
            f'<td style="padding:3px 6px;color:#6b7280">{"✓ " if r["active"] else ""}{r["cond"]}</td>'
            f'<td style="padding:3px 6px;text-align:right">{r["pts"]}分</td></tr>'
            for r in c["rules"]
        )
        return f"""
        <div style="background:#fff;border-radius:10px;padding:18px 20px;box-shadow:0 1px 4px rgba(0,0,0,.08)">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px">
            <div>
              <div style="font-size:14px;font-weight:600">{c['name']}</div>
              <div style="font-size:12px;color:#6b7280">当前：<span style="font-weight:600;color:#374151">{c['current']}</span></div>
            </div>
            <div style="font-size:20px;font-weight:700;color:{c['color']}">{c['score']}<span style="font-size:11px;color:#9ca3af">/{c['max']}</span></div>
          </div>
          {bar(c['score'], c['max'], c['color'])}
          <div style="margin-top:10px;font-size:12px;color:#6b7280;background:#f9fafb;border-radius:6px;padding:6px 8px">
            <b style="color:#374151">为什么：</b>{c['why']}
          </div>
          <table style="width:100%;border-collapse:collapse;margin-top:6px;font-size:12px">{rules_html}</table>
        </div>"""

    tech_cards_html = "".join(tech_card_html(c) for c in tech_cards)

    # 基本面区块
    fund_updated = fund_data.get("updated_at", "未知")
    runway_color = "#16a34a" if (cash_runway or 0) > 12 else "#ca8a04" if (cash_runway or 0) > 6 else "#dc2626"
    filings_html = "".join(
        f'<div style="padding:6px 0;border-bottom:1px solid #f3f4f6;font-size:12px">'
        f'<span style="color:#6b7280">{fl["date"]}</span>&nbsp;'
        f'<a href="{fl["url"]}" target="_blank" style="color:#4f46e5">{fl["title"]}</a></div>'
        for fl in filings[:8]
    ) or '<div style="font-size:12px;color:#9ca3af">无数据（运行 --full 获取）</div>'

    # 策略三栏
    def strategy_col(key, label, icon, color, rs):
        is_active = (strategy == key)
        bg = f"background:{color}10;border:2px solid {color};" if is_active else "background:#f9fafb;border:2px solid #e5e7eb;"
        return f"""
        <div style="{bg}border-radius:10px;padding:18px;flex:1">
          <div style="font-size:16px;font-weight:700;color:{color if is_active else '#9ca3af'};margin-bottom:8px">{icon} {label}</div>
          {'<div style="font-size:11px;font-weight:600;background:'+color+';color:#fff;padding:2px 8px;border-radius:99px;display:inline-block;margin-bottom:8px">当前建议</div>' if is_active else ''}
          {reasons_list(rs, color if is_active else '#6b7280')}
        </div>"""

    strategy_html = f"""
    <div style="display:flex;gap:16px;flex-wrap:wrap">
      {strategy_col("STOP_LOSS", "止损", "🔴", "#dc2626", reasons["stop_loss"])}
      {strategy_col("HOLD",      "持有", "🟡", "#ca8a04", reasons["hold"])}
      {strategy_col("ADD",       "加仓", "🟢", "#16a34a", reasons["add"])}
    </div>"""

    # 历史表格
    def strat_badge(s):
        c = {"STOP_LOSS":"#dc2626","ADD":"#16a34a","HOLD":"#ca8a04"}.get(s,"#9ca3af")
        l = {"STOP_LOSS":"止损","ADD":"加仓","HOLD":"持有"}.get(s, s)
        return f'<span style="background:{c};color:#fff;padding:1px 7px;border-radius:4px;font-size:11px">{l}</span>'

    table_rows_html = "".join(
        f"<tr><td>{r['date']}</td>"
        f"<td style='font-weight:600;color:{score_color(int(r['total_score']),100)}'>{r['total_score']}</td>"
        f"<td>{r['tech_score']}</td><td>{r['fund_score']}</td>"
        f"<td>${float(r['price']):.2f}</td>"
        f"<td>{strat_badge(r['strategy'])}</td></tr>"
        for r in rows_desc
    )

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>OKLO 持仓分析</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
  body{{font-family:-apple-system,sans-serif;background:#f9fafb;margin:0;padding:24px;color:#111}}
  h1{{font-size:22px;font-weight:700;margin-bottom:4px}}
  .sub{{color:#6b7280;font-size:13px;margin-bottom:20px}}
  .cards{{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:20px}}
  .card{{background:#fff;border-radius:10px;padding:18px 22px;box-shadow:0 1px 4px rgba(0,0,0,.08);min-width:140px}}
  .card .label{{font-size:11px;color:#6b7280;margin-bottom:4px}}
  .card .val{{font-size:26px;font-weight:700}}
  .section{{font-size:15px;font-weight:600;margin:20px 0 10px}}
  .ind-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px;margin-bottom:20px}}
  .chart-box{{background:#fff;border-radius:10px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,.08);margin-bottom:20px}}
  table{{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,.08);overflow:hidden}}
  th{{background:#f3f4f6;padding:9px 12px;text-align:left;font-size:12px;color:#374151}}
  td{{padding:8px 12px;font-size:13px;border-top:1px solid #f3f4f6}}
  tr:hover td{{background:#fafafa}}
</style>
</head>
<body>
<h1>OKLO 持仓分析</h1>
<div class="sub">更新时间：{today} &nbsp;·&nbsp; 80股 @ 成本 ${AVG_COST}</div>

<div class="cards">
  <div class="card">
    <div class="label">综合评分</div>
    <div class="val" style="color:{score_color(total_score,100)}">{total_score}<span style="font-size:14px;color:#9ca3af">/100</span></div>
    <div style="font-size:11px;color:#6b7280;margin-top:4px">技术 {tech_score}/50 · 基本面 {fund_score}/50</div>
  </div>
  <div class="card">
    <div class="label">现价</div>
    <div class="val">${price:.2f}</div>
  </div>
  <div class="card">
    <div class="label">持仓浮亏/盈</div>
    <div class="val" style="color:{pnl_color}">{"▲" if pnl_pct>=0 else "▼"}{abs(pnl_pct):.1f}%</div>
    <div style="font-size:11px;color:{pnl_color}">${pnl_dollars:+,.0f}</div>
  </div>
  <div class="card">
    <div class="label">止损线</div>
    <div class="val" style="color:{stop_color}">${STOP_LOSS_PRICE}</div>
    <div style="font-size:11px;color:{stop_color}">距离 {dist_stop_pct:+.1f}%</div>
  </div>
  <div class="card">
    <div class="label">策略建议</div>
    <div style="margin-top:10px;font-size:18px;font-weight:700;color:{strategy_colors.get(strategy,'#9ca3af')}">{strategy_labels.get(strategy,strategy)}</div>
    {'<div style="font-size:12px;color:#16a34a;margin-top:4px">建议加仓 $'+f'{add_amount:,.0f}</div>' if strategy=="ADD" else ''}
  </div>
  <div class="card">
    <div class="label">现金跑道</div>
    <div class="val" style="color:{runway_color}">{f'{cash_runway:.0f}月' if cash_runway else 'N/A'}</div>
  </div>
</div>

<div class="section">策略建议详情</div>
{strategy_html}

<div class="section">技术指标详情</div>
<div class="ind-grid">{tech_cards_html}</div>

<div class="section">基本面详情 <span style="font-size:12px;font-weight:400;color:#9ca3af">（上次更新：{fund_updated}）</span></div>
<div style="background:#fff;border-radius:10px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,.08);margin-bottom:20px;display:grid;grid-template-columns:1fr 1fr;gap:20px">
  <div>
    <div style="font-size:13px;font-weight:600;margin-bottom:10px">财务指标</div>
    <table style="box-shadow:none">
      <tr><td style="color:#6b7280;border:none">现金跑道</td><td style="font-weight:600;color:{runway_color};border:none">{f'{cash_runway:.1f} 个月' if cash_runway else 'N/A'}</td></tr>
      <tr><td style="color:#6b7280">分析师目标价</td><td style="font-weight:600">{f'${analyst_target:.2f}' if analyst_target else 'N/A'}</td></tr>
      <tr><td style="color:#6b7280">总现金</td><td style="font-weight:600">{f'${fund_data.get("total_cash",0)/1e6:.0f}M' if fund_data.get("total_cash") else 'N/A'}</td></tr>
      <tr><td style="color:#6b7280">经营现金流</td><td style="font-weight:600">{f'${fund_data.get("operating_cf",0)/1e6:.0f}M' if fund_data.get("operating_cf") else 'N/A'}</td></tr>
    </table>
  </div>
  <div>
    <div style="font-size:13px;font-weight:600;margin-bottom:10px">近期 SEC 8-K 公告</div>
    {filings_html}
  </div>
</div>

<div class="chart-box">
  <div style="font-size:14px;font-weight:600;margin-bottom:12px">历史评分走势</div>
  <canvas id="scoreChart" height="80"></canvas>
</div>

<div class="section">历史记录</div>
<table>
<thead><tr><th>日期</th><th>总分</th><th>技术分</th><th>基本面分</th><th>价格</th><th>策略</th></tr></thead>
<tbody>{table_rows_html}</tbody>
</table>

<script>
new Chart(document.getElementById('scoreChart'), {{
  type: 'line',
  data: {{
    labels: {chart_labels},
    datasets: [
      {{label:'综合评分',data:{chart_total},borderColor:'#4f46e5',backgroundColor:'rgba(79,70,229,0.08)',fill:true,tension:0.3,pointRadius:3,borderWidth:2}},
      {{label:'技术评分',data:{chart_tech},borderColor:'#0891b2',backgroundColor:'transparent',tension:0.3,pointRadius:2,borderWidth:1.5,borderDash:[4,3]}},
      {{label:'买入门槛(总分60)',data:Array({len(chart_rows)}).fill(60),borderColor:'#9ca3af',pointRadius:0,borderWidth:1,borderDash:[6,4]}}
    ]
  }},
  options:{{responsive:true,plugins:{{legend:{{position:'top'}}}},scales:{{y:{{min:0,max:100}},x:{{ticks:{{maxTicksLimit:10}}}}}}}}
}})
</script>
</body></html>"""

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
```

- [ ] **Step 2: 运行完整测试验证 HTML 生成**

```bash
python oklo_score.py --full
```
预期：控制台打印持仓摘要、策略建议，生成 `oklo_report.html`，在浏览器打开确认 7 个区块均正常显示

- [ ] **Step 3: Commit**

```bash
git add oklo_score.py
git commit -m "feat(oklo): add HTML report generation with 7 sections"
```

---

## Task 9: 整合每日定时任务

**Files:**
- Create: `run_daily.bat`

- [ ] **Step 1: 新建 `run_daily.bat`**

```bat
@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo [%date% %time%] 开始每日分析... >> daily_run.log
python tqqq_score.py >> daily_run.log 2>&1
python oklo_score.py >> daily_run.log 2>&1
echo [%date% %time%] 完成 >> daily_run.log
```

- [ ] **Step 2: 测试批处理文件**

```bash
cmd /c run_daily.bat
```
预期：两个脚本依次运行，无报错，`daily_run.log` 有输出记录

- [ ] **Step 3: 更新 Windows 任务计划程序**

将原来指向 `run_tqqq.bat` 的计划任务改为指向 `run_daily.bat`（手动操作，无需代码）。

- [ ] **Step 4: Commit**

```bash
git add run_daily.bat
git commit -m "feat: add run_daily.bat integrating TQQQ and OKLO daily analysis"
```

---

## Task 10: 运行深度分析

- [ ] **Step 1: 运行 `--full` 获取当前基本面和SEC公告**

```bash
python oklo_score.py --full
```
预期：拉取 yfinance 基本面数据、SEC 8-K 公告，保存 `oklo_fundamental.json`，生成完整 HTML 报告

- [ ] **Step 2: 在浏览器打开报告，确认所有区块数据正确**

检查：
- 持仓摘要卡片：现价、浮亏%、止损线距离
- 策略建议三栏：当前命中的选项高亮
- 基本面：现金跑道月数、分析师目标价、8-K 列表
- 历史图表：至少1条数据点

- [ ] **Step 3: 运行所有测试确认无回归**

```bash
python -m pytest tests/test_oklo_scoring.py -v
```
预期：全部 `PASSED`

- [ ] **Step 4: 最终 Commit**

```bash
git add oklo_history.csv oklo_fundamental.json oklo_report.html
git commit -m "feat(oklo): initial full analysis run with fundamental data"
```
