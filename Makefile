.PHONY: run
run:
	uv run scrobble

.PHONY: install
install:
	uv sync

.PHONY: outdated
outdated:
	uv tree --outdated --depth 1

.PHONY: audit
audit:
	uv audit
