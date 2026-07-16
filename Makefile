.PHONY: run
run:
	uv run python scrobble.py

.PHONY: install
install:
	uv sync

.PHONY: outdated
outdated:
	uv tree --outdated --depth 1

.PHONY: audit
audit:
	uv audit
