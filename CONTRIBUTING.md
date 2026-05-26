# Contributing

Thanks for considering a contribution.

## Getting started

```bash
git clone https://github.com/Inah516/aegis-mev-shield.git
cd aegis-mev-shield
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-asyncio ruff

cp .env.example .env
# Set MIMO_API_KEY + chain WSS endpoints

pytest tests/ -v
uvicorn src.main:app --reload --port 8000
```

## Adding a new detector

1. Define an agent descriptor in `src/agents.py`
2. Implement the prompt + classifier in the same module
3. Wire it into `src/engine.py` fan-out
4. Add tests in `tests/`
5. Open a PR

## Pull request workflow

1. Fork and branch from `main`
2. `ruff check src/ tests/`
3. `pytest tests/`
4. Open a PR

## Reporting issues

Use GitHub issues. Include the chain, block range, tx hash if relevant.
