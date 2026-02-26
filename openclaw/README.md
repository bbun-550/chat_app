# OpenClaw

OpenClaw is a personal AI console Web MVP based on FastAPI + SQLite.

## Phase Status

- Phase 0: environment and project baseline complete
- Next: Phase 1 (DB layer implementation)

## Quick Start

```bash
cp .env.example .env
# set GEMINI_API_KEY in .env

make db
make run
```

Open in browser: `http://127.0.0.1:8000/`

## Development Commands

- `make db`: initialize SQLite schema
- `make run`: run FastAPI server
- `make fmt`: format with black
- `make lint`: lint with ruff
- `make test`: run tests
