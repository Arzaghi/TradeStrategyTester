# Trader Bot / Strategy Tester

A compact Python library and example bot that implements candle-based trading strategies and a minimal execution/persistence stack. It is intended for learning, experimenting with simple technical rules, and running small strategy simulations. The codebase includes example strategies, a lightweight trader, persistence helpers and a tiny API entrypoint.

Key files
- `strategy.py` — strategy implementations (e.g. `StrategyAllCandles`, `StrategyHammerCandles`)
- `models.py` — domain models (e.g. `Position`)
- `trader.py` — trade execution / simulation logic
- `persistence.py` — simple save/load helpers
- `api.py` — optional minimal HTTP interface (if present)
- `main.py` — example entrypoint to run the bot
- `requirements.txt` — Python dependencies
- `Dockerfile` — container image build
- `tests/` — unit tests (e.g. `tests/test_strategy.py`, `tests/test_trader.py`)

What this project is for
- Learn how simple candle-based strategies can be implemented and tested in Python.
- Provide a minimal simulation/execution loop for developing and validating strategies.
- Demonstrate small, testable components (strategy, trader, persistence, models).

Requirements
- Python 3.8+ (project works on modern Python; CI uses 3.11 in this repo)
- pip (for installing dependencies)

Quickstart (Windows PowerShell)
1) Create and activate a virtual environment (recommended):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2) Install dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run the example bot

```powershell
python main.py
```

Run the tests

```powershell
python -m pytest tests/ --disable-warnings -q
```

Notes about tests
- The `tests/` directory contains unit tests that exercise strategies and trader behavior. Running `pytest` will run the full suite.

Docker
- Build image locally:

```powershell
docker build -t trader-bot:local .
```

- Run container (example):

```powershell
docker run --rm -d --name traderBot trader-bot:local
```

Development & project structure
- Strategies: check `strategy.py` for example implementations and to add new rules.
- Models: `models.py` contains data structures used across components (positions, orders, etc.).
- Trader: `trader.py` performs simulated execution; adapt it for realistic slippage/fees.
- Persistence: `persistence.py` currently provides minimal save helpers; replace with a DB or storage layer as needed.

License
- This repository does not currently include a license file.

Contact / help
- For quick experiments, inspect `tests/test_strategy.py` and `main.py` to see how strategies are invoked and validated.
