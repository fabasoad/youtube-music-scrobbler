.PHONY: fetch
fetch:
	uv run fetch

.PHONY: run
run:
	uv run scrobble

.PHONY: update-likes
update-likes:
	uv run update-likes

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
