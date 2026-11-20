.PHONY: install test lint demo run export-example
install:
	python -m pip install -e ".[dev]"

test:
	python -m pytest -q

lint:
	ruff check src tests

demo:
	apex-f1 demo --trials 400

run:
	apex-f1 serve --host 127.0.0.1 --port 8000

export-example:
	apex-f1 export-fastf1 --year 2024 --round 1 --driver VER --output data/derived/bahrain-2024-ver.json
