.PHONY: test lint

test:
	uv run --dev pytest

lint:
	uv run --dev pre-commit run --all-files
