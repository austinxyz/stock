# FIG Stock Analysis Design Spec

**Date:** 2026-04-02
**Status:** Approved

---

## Goal

Build `analysis/fig_score.py` — a daily hold/sell conviction scorer that ranks FIG (Figma) against 4 peer stocks (PLTR, NOW, DDOG, ADBE) to help decide whether to hold FIG in Roth IRA or rotate into a higher-conviction alternative.

---

## Context

- **Holding:** 50 shares FIG @ $62.82 avg cost, held in **Roth IRA** (no capital gains tax on trades)
- **Concern:** Figma is an AI collaboration tool at risk of disruption by generative AI design tools
- **Decision framework:** If FIG ranks near the bottom of its peer group, rotate to the top-ranked peer

---

## Peers

| Ticker | Thesis |
|--------|--------|
| PLTR | AI data analytics platform; AI is core product, not a threat |
| NOW | Enterprise workflow automation; deep AI Agent integration |
| DDOG | Cloud observability; AI-era infrastructure, hard to displace |
| ADBE | Direct competitor and AI beneficiary via Firefly |

---

## Scoring (0–100 per stock)

### Technical (40 pts)

| Indicator | Max | Rules |
|-----------|-----|-------|
| RSI(14) | 15 | 50–70: 15 / 35–50: 8 / >70: 8 (overbought) / <35: 3 |
| MACD histogram | 10 | golden cross or expanding positive: 10 / positive shrinking: 5 / negative: 0 |
| Price vs 200d MA | 10 | above: 10 / below: 0 |
| 52w high drawdown | 5 | >-10%: 5 / >-25%: 3 / >-40%: 1 / ≤-40%: 0 |

### Fundamental (60 pts)

| Indicator | Max | Rules |
|-----------|-----|-------|
| Revenue growth (YoY) | 20 | ≥20%: 20 / ≥10%: 13 / ≥5%: 6 / <5%: 0 |
| Analyst target upside | 20 | ≥30%: 20 / ≥15%: 13 / ≥5%: 6 / <5%: 0 |
| Analyst rating mean | 20 | ≤2.0: 20 / ≤2.5: 13 / ≤3.0: 6 / >3.0: 0 |

Fundamental data cached in `analysis/report/fig_fundamental.json`. Auto-refreshed if cache is >7 days old.

---

## Recommendation Logic

Based on FIG's rank among the 5 stocks:

| FIG rank | Score | Output |
|----------|-------|--------|
| 1–2 | any | **HOLD** — FIG still competitive |
| 3 | any | **WATCH** — monitor, no action yet |
| 4–5 | <55 | **SELL** → rotate into rank-#1 peer |
| 4–5 | ≥55 | **WATCH** — weak position but not critical |

---

## HTML Report Sections

1. **FIG 持仓快照** — price, total value, unrealized P&L, Roth IRA tax note
2. **横向排名总表** — all 5 stocks ranked, FIG highlighted, recommendation
3. **各股评分卡片** — one card per stock (technical + fundamental breakdown)
4. **换仓建议面板** — shown when action is SELL; estimated rotation amount
5. **FIG 历史评分走势** — Chart.js line chart of FIG's daily scores

---

## Files

| File | Purpose |
|------|---------|
| `analysis/fig_score.py` | All logic: config, scoring, data fetch, CSV I/O, HTML, main() |
| `tests/test_fig_scoring.py` | Unit tests for pure scoring functions |
| `analysis/report/fig_history.csv` | FIG daily score history (not committed) |
| `analysis/report/fig_fundamental.json` | Fundamental cache for all 5 stocks (not committed) |
| `analysis/report/fig_daily_report.html` | Daily HTML report (not committed) |

---

## Key Differences from OKLO/EBAY

- No add budget, no stop loss, no sell log — purely a conviction ranking
- Fetches fundamentals for 5 stocks (not 1); stored in single JSON
- Fundamental cache auto-refreshes after 7 days (no `--full` flag needed)
- Not added to `run_daily.bat` — run manually: `py analysis/fig_score.py`
- Roth IRA context: rotation cost is zero, decision is purely about expected returns
