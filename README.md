# ⚔️ WAR DASHBOARD

Global macro war room for tracking energy shocks, recession signals, tanker freight, refinery thermal anomalies, and global flight activity.

## Features

- Asset dashboard for Brent, WTI, S&P 500, gold, and US 10Y yield
- Energy panel for crack spreads, crude and product inventories, and refinery utilization
- Macro panel for yield curve, industrial production, tanker freight, and capacity utilization
- Alt Intel tables for NASA FIRMS refinery fire detections and OpenSky airborne aircraft counts
- Local parquet-backed cache for faster reloads and lower API usage

## Requirements

- Python 3.11+
- Optional API keys for EIA, FRED, and NASA FIRMS
- Network access to Yahoo Finance, EIA, FRED, NASA FIRMS, and OpenSky

## Local Setup

### Using uv (recommended — shared venv)

```bash
git clone https://github.com/meever/war-dashboard.git
cd war-dashboard
uv sync --python D:\code\shared_venv\dashboards\Scripts\python.exe
copy .env.example .env
streamlit run app.py
```

### Using pip (standalone venv)

```bash
git clone https://github.com/meever/war-dashboard.git
cd war-dashboard
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
streamlit run app.py
```

The dashboard still runs without API keys, but only Yahoo Finance and OpenSky-backed views will populate.

## Environment Variables

| Variable | Required | Purpose |
| --- | --- | --- |
| `EIA_API_KEY` | No | Weekly petroleum inventories and refinery utilization |
| `FRED_API_KEY` | No | Macro series such as industrial production and yield curve |
| `FIRMS_MAP_KEY` | No | NASA FIRMS refinery fire detections |
| `LOG_LEVEL` | No | Python logging level, default `INFO` |

## Runtime Notes

- Local history is stored in `local_data/` as parquet files
- HTTP calls use a shared retrying session with exponential backoff for transient failures
- Failures are logged instead of being swallowed silently
- Sidebar keys are normalized and stripped before use

## Deployment

### Docker

```bash
docker build -t war-dashboard .
docker run --rm -p 8501:8501 --env-file .env war-dashboard
```

### Direct Process

```bash
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

## Deployment Checklist

- Confirm `.env` is present and not committed
- Confirm `local_data/` is writable by the runtime user
- Verify `pip install -r requirements.txt` installs `pyarrow` successfully
- Open all four tabs once after deploy and confirm data loads
- Check logs for API warnings or repeated retry failures

## Repository Layout

```text
app.py
components/
charts/
data/
local_data/
.streamlit/
settings.py
Dockerfile
```

## Security Notes

- `.env` is ignored by git; only `.env.example` should be committed
- API keys are never rendered back into the UI
- HTML rendering is limited to application-owned markup, not user-provided content

## License

[MIT](LICENSE)
