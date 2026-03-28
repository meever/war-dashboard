# ⚔️ WAR DASHBOARD

**Global Macro War Room — Energy Shock Monitor**

A real-time macroeconomic dashboard built with Streamlit, tracking crude oil markets, energy inventories, and recession signals in a dark terminal-style interface.

![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-1.30+-red.svg)
![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)

## Quick Start

```bash
git clone https://github.com/meever/war-dashboard.git
cd war-dashboard
pip install -r requirements.txt
cp .env.example .env          # Edit with EIA/FRED keys (optional)
streamlit run app.py           # Opens at http://localhost:8501
```

> The dashboard works without API keys — asset prices from Yahoo Finance still load. EIA and FRED keys unlock energy inventory and macro signal panels.

- **EIA key**: [eia.gov/opendata](https://www.eia.gov/opendata/register.php) (free)
- **FRED key**: [fred.stlouisfed.org](https://fred.stlouisfed.org/docs/api/api_key.html) (free)

---

## Visual Layout & Current State

This section describes every visible element of the dashboard so that agents and contributors who cannot see the running website can understand the full UI.

### Page Shell

- **Title**: `layout="wide"`, dark theme (#0A0A0A background), JetBrains Mono font, sidebar starts collapsed
- **Header bar**: Transparent background, Streamlit chrome hidden (`#MainMenu`, `footer`, status widget all removed via CSS). Only the sidebar expand arrow (`>>`) is visible in the top-left corner (enabled by `client.toolbarMode = "minimal"`)
- **Title banner**: Single row — red "⚔️ WAR DASHBOARD" (16px, letter-spacing 4px) + green "GLOBAL MACRO WAR ROOM — ENERGY SHOCK MONITOR" subtitle (10px), separated by a thin red border-bottom

### Sidebar (Collapsed by Default)

Click the `>>` arrow to open. Contains:
- "🗡️ COMMAND CENTER" header
- **EIA API KEY** text input (password type, reads from `EIA_API_KEY` env var)
- **FRED API KEY** text input (password type, reads from `FRED_API_KEY` env var)
- **🔄 REFRESH DATA** button — clears all `st.cache_data`
- Footer: "WAR DASHBOARD v1.0 | Data: Yahoo Finance · EIA · FRED"

### Status Bar (8 Cards)

Immediately below the title banner, a single-row CSS grid (8 columns) displays:

| Card | Source | Format | Color Logic |
|------|--------|--------|-------------|
| **WTI** | `price_data["wti"]` last Close | `{value:,.2f}` | White text |
| **S&P 500** | `price_data["spx"]` | `{:,.2f}` | White |
| **GOLD** | `price_data["gold"]` | `{:,.2f}` | White |
| **10Y YIELD** | `price_data["us10y"]` | `{:,.2f}` | White |
| **CRACK** | Heating Oil Spread | `${value:,.1f}` | 🟢 safe / 🔴 danger |
| **INVENTORY** | Weekly Crude Stocks latest | `{:,.0f}` | 🟢 / 🔴 |
| **YIELD CRV** | 10Y-2Y spread | `{:.2f}%` | 🟢 / 🔴 |
| **SHIPPING** | SBLK last Close | `${:,.0f}` | 🟢 / 🔴 |

**Signal thresholds**:
- Crack Spread: RED if percentile ≤5% or ≥95% of full history, or 5d avg declined >15% vs 30d avg
- Inventory: RED if latest weekly change z-score > 2.0 (vs 4-week avg/std)
- Yield Curve: RED if 10Y-2Y spread < 0 (inverted)
- Shipping: RED if SBLK declined >15% over 30 days

### Tabs (3 Tabs)

Below the status bar. Each tab has its own **period picker** (horizontal radio: 30d, **60d** [default], 90d, 6m, 1y, 2y, 5y, Max).

#### Tab 1: 💥 ASSET BLOWUP

A 2×2 Plotly subplot grid (580px height):

| Position | Panel | Traces | Colors | Legend |
|----------|-------|--------|--------|--------|
| [1,1] | Crude Oil (Brent vs WTI) | Brent Crude, WTI Crude | Red #FF4136, Amber #FF8C00 | Yes (horizontal, top) |
| [1,2] | S&P 500 | S&P 500 | Green #00FF41 | No |
| [2,1] | Gold ($/oz) | Gold | Gold #FFD700 | No |
| [2,2] | US 10Y Yield (%) | US 10Y Yield | Cyan #00FFFF | No |

- All panels have NBER recession shading (subtle red bands `rgba(255,65,54,0.08)`)
- Scroll-zoom enabled, permanent modebar (camera, zoom, pan, autoscale, reset, fullscreen)
- Hover mode: "x unified" (crosshair with all values)

#### Tab 2: 🛢️ ENERGY & DEMAND

A 2×2 Plotly subplot grid (580px height):

| Position | Panel | Traces | Colors | Legend |
|----------|-------|--------|--------|--------|
| [1,1] | Crack Spreads ($/bbl) | Heating Oil Spread, Gasoline Spread | Amber #FF8C00, Cyan #00FFFF | Yes (horizontal, top) |
| [1,2] | Crude Oil Stocks (k bbl) | Weekly Crude Stocks | Cyan #00FFFF | Only if >1 series |
| [2,1] | Product Stocks (k bbl) | Distillate Stocks, Gasoline Stocks | Cyan, Amber | Yes when multi-series |
| [2,2] | Refinery Utilization (%) | Weekly Refinery Util | Red #FF4136 | No |

- Panel [1,1] has a red dashed zero-reference line
- All panels have NBER recession shading
- Crack data computed from HO=F and RB=F futures (×42 gal→bbl conversion) minus WTI

#### Tab 3: 📉 MACRO SIGNALS

Above the chart: a dark HTML box with **SIGNAL GUIDE** — color-coded explanations for each indicator.

A 2×2 Plotly subplot grid (580px height):

| Position | Panel | Traces | Colors | Special |
|----------|-------|--------|--------|---------|
| [1,1] | Yield Curve (10Y-2Y) | 10Y-2Y Spread | Cyan #00FFFF | Red dashed zero-line |
| [1,2] | Industrial Production | INDPRO index | Green #00FF41 | — |
| [2,1] | Dry Bulk Shipping (SBLK) | SBLK price | Amber #FF8C00 | — |
| [2,2] | Capacity Utilization (%) | TCU percent | Gold #FFD700 | Green dot at 80%, red dot at 75% |

- All panels have NBER recession shading
- No legends on any panel (single-trace panels)

### Chart Visual Theme (All Charts)

- Template: `plotly_dark`
- Paper: `#0F0F1A`, Plot: `#0A0A0A`, Grid: `#1A1A2E`, Text: `#E0E0E0`
- Font: Courier New, size 11
- Subplot titles: size 16, Courier New
- Margins: left 50, right 20, top 40, bottom 30
- Scrollbar: custom dark (8px, #1A1A2E thumb, #FF4136 on hover)

### Recession Shading

6 NBER recession periods appear as subtle red vertical bands on every chart panel:
- 1980 Jan–Jul, 1981 Jul–1982 Nov, 1990 Jul–1991 Mar, 2001 Mar–Nov, 2007 Dec–2009 Jun, 2020 Feb–Apr

Visible when zoomed to longer timeframes (1y+, Max). At 60d default, they're outside the x-range and invisible.

---

## Architecture

### Project Structure

```
war-dashboard/
├── app.py                 # Main Streamlit entry point (CSS, layout, tabs, data flow)
├── requirements.txt       # streamlit, yfinance, fredapi, requests, pandas, numpy, plotly, python-dotenv
├── .env.example           # EIA_API_KEY, FRED_API_KEY template
├── .streamlit/
│   └── config.toml        # Dark theme, headless, toolbarMode=minimal
├── components/
│   ├── sidebar.py         # API key inputs + refresh button → returns {eia_key, fred_key, refresh}
│   └── status_bar.py      # 8-card HTML row with signal logic
├── charts/
│   ├── assets.py          # WAR_COLORS, RECESSIONS, add_recessions(), PLOTLY_CONFIG, _base_layout(), make_asset_grid()
│   ├── energy.py          # make_energy_grid(crack_df, eia_df)
│   ├── macro.py           # make_macro_grid(fred_df, asset_df), SIGNAL_GUIDE
│   └── history.py         # CRISIS_EVENTS, ASSET_LABELS, make_long_term_chart/grid (available, not rendered in app.py)
├── data/
│   ├── cache.py           # @st.cache_data wrappers with TTLs (5min/1hr/24hr)
│   ├── market.py          # yfinance fetcher, ASSET_TICKERS, CRACK_TICKERS, TIMEFRAME_DAYS
│   ├── energy.py          # EIA API v2 client (weekly + monthly series)
│   ├── macro.py           # FRED API client (INDPRO, TCU, T10Y2Y, etc.)
│   └── store.py           # Parquet persistence, incremental refresh from 1980
└── local_data/            # Auto-generated parquets (gitignored): brent, wti, spx, gold, us10y, sblk, ho, rb, eia_weekly, fred_macro
```

### Data Flow

```
External APIs                    Local Storage                  UI Layer
─────────────                    ─────────────                  ────────
yfinance (BZ=F, CL=F,    ──►  local_data/*.parquet   ──►    @st.cache_data (TTL)
 ^GSPC, GC=F, ^TNX,             (incremental refresh)         get_asset_data()
 SBLK, HO=F, RB=F)                                            get_full_market_history()

EIA API v2                ──►  eia_weekly.parquet     ──►    get_full_eia_history()
 (PET.WCESTUS1.W,                                            fetch_eia_inventories()
  PET.WDISTUS1.W,
  PET.WGTSTUS1.W,
  PET.WPULEUS3.W)

FRED API                  ──►  fred_macro.parquet     ──►    get_full_fred_history()
 (INDPRO, TCU, T10Y2Y,                                       fetch_fred_dataframe()
  MANEMP, DCOILWTICO,
  GASREGW, GASDESW)
```

### Data Tickers & Series IDs

**Yahoo Finance (yfinance):**
| Ticker | Asset | Store Key |
|--------|-------|-----------|
| `BZ=F` | Brent Crude futures | brent |
| `CL=F` | WTI Crude futures | wti |
| `^GSPC` | S&P 500 Index | spx |
| `GC=F` | Gold futures | gold |
| `^TNX` | US 10Y Treasury Yield | us10y |
| `SBLK` | Star Bulk Carriers (dry bulk proxy) | sblk |
| `HO=F` | Heating Oil futures ($/gal) | ho |
| `RB=F` | RBOB Gasoline futures ($/gal) | rb |

**EIA API v2 (weekly):**
| Series ID | Label |
|-----------|-------|
| `PET.WCESTUS1.W` | Weekly Crude Stocks (Mbbls) |
| `PET.WDISTUS1.W` | Weekly Distillate Stocks |
| `PET.WGTSTUS1.W` | Weekly Gasoline Stocks |
| `PET.WPULEUS3.W` | Weekly Refinery Utilization % |

**FRED:**
| Series ID | Label |
|-----------|-------|
| `INDPRO` | Industrial Production (index 2017=100) |
| `MANEMP` | Manufacturing Employment (thousands) |
| `TCU` | Capacity Utilization (%) |
| `T10Y2Y` | Yield Curve 10Y-2Y spread (%) |
| `DCOILWTICO` | WTI Crude (FRED, $/bbl daily) |
| `GASREGW` | Retail Gasoline ($/gal weekly) |
| `GASDESW` | Retail Diesel ($/gal weekly) |

### Cache & Refresh Strategy

| Data | TTL | Refresh Trigger | Source |
|------|-----|-----------------|--------|
| Asset prices (short-term) | 5 min | Auto | Local parquet → yfinance fallback |
| Full market history | 1 hour | `_is_stale()` check | Incremental yfinance fetch (last date → today) |
| EIA inventories | 24 hours | Manual or stale | Full refetch from 1990 |
| FRED macro | 24 hours | Manual or stale | Full refetch from 1960 |

Parquet files store complete history (back to 1980 for market data). Incremental refresh fetches only the gap between last stored date and today, with a 3-day overlap to prevent gaps.

### Color Palette

```
#FF4136  — red    (Brent, danger, recession shading, inverted yield curve)
#FF8C00  — amber  (WTI, heating oil spread, warning signals)
#00FF41  — green  (S&P 500, industrial production, bullish)
#00FFFF  — cyan   (10Y Yield, gasoline spread, yield curve)
#FFD700  — gold   (Gold, capacity utilization)
#FFFFFF  — white  (SBLK shipping)
#0A0A0A  — black  (plot background)
#0F0F1A  — navy   (paper/card background)
#1A1A2E  — indigo (grid lines, borders)
#E0E0E0  — gray   (default text)
```

### Unused but Available Code

`charts/history.py` defines full-history charts (`make_long_term_chart()`, `make_long_term_grid()`, `make_crack_spread_history_chart()`) with crisis event markers and "YOU ARE HERE" annotations. These are **not currently rendered** in `app.py` but are fully functional and importable. They include:
- Arrow annotations at crisis dates (9/11, Lehman, US Downgrade, OPEC Price War, COVID Crash, Russia Invades)
- Historical percentile box (green if ≤80th, red if >80th)
- Current price "YOU ARE HERE" dotted line

---

## Signal Logic

| Signal | Green (Safe) | Red (Danger) |
|--------|-------------|-------------|
| **Crack Spread** | Within 5th–95th percentile of full history | Outside 5th/95th percentile OR 5d avg declined >15% vs 30d avg |
| **Inventory** | Normal weekly change | Latest build >2σ above 4-week average |
| **Yield Curve** | 10Y-2Y spread > 0 | Inverted (spread < 0) — recession warning |
| **Shipping** | SBLK stable or rising | SBLK declined >15% over 30 days |

## License

[MIT](LICENSE)
