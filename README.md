# nldate

Parse natural-language date strings into `datetime.date` objects.

## Install

```bash
uv sync
```

## Usage

```python
from datetime import date
from nldate import parse

parse("5 days before December 1st, 2025")
parse("next Tuesday", today=date(2025, 11, 5))
```

Unrecognized inputs (including the empty string) raise `ValueError`.

## Development

```bash
uv run pytest
uv run mypy src/
uv run ruff check
uv run ruff format --check
```
