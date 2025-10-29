# JobHub-API

Minimal FastAPI microservice scaffold.

## Quickstart

```bash
# Python 3.12+ recommended
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate

pip install --upgrade pip
pip install -e .
pip install -e .[dev]

make dev  # or: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --app-dir src
```

## Run tests

```bash
make test
```

## Lint/format/type-check

```bash
make fmt && make lint && make type
```
