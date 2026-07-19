.PHONY: run
run:
	uv run scrobble

.PHONY: refresh-auth
refresh-auth:
	uv run refresh-auth

.PHONY: verify
verify:
	uv run python verify.py

.PHONY: install
install:
	uv sync

.PHONY: outdated
outdated:
	uv tree --outdated --depth 1

.PHONY: audit
audit:
	uv audit

.PHONY: lint
lint:
	uv run ruff check .
	uv run ruff format --check .

.PHONY: test
test:
	uv run python -m pytest
