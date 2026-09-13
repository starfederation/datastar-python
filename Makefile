.PHONY: test lint

test:
	@trap 'rm -f uv.lock' EXIT; uv run --with pytest pytest

lint:
	uv run --dev pre-commit run --all-files
