.PHONY: setup test lint check clean

# ── Environment Setup ──────────────────────────────────────────────────────────
setup:
	@echo "==> Creating virtual environment..."
	python3 -m venv .venv
	@echo "==> Installing production dependencies..."
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install pydantic==2.7.1 pydantic-core==2.18.2
	@echo "==> Installing development dependencies..."
	.venv/bin/pip install pytest==8.2.0 pytest-cov==5.0.0 mypy==1.10.0 ruff==0.4.4
	@echo "==> Setup complete. Activate with: source .venv/bin/activate"

# ── Testing ───────────────────────────────────────────────────────────────────
test:
	.venv/bin/pytest --cov=src --cov-report=term-missing --cov-fail-under=95

# ── Linting & Type Checking ───────────────────────────────────────────────────
lint:
	.venv/bin/ruff check src/ tests/
	.venv/bin/ruff format --check src/ tests/
	.venv/bin/mypy src/

# ── Full CI Check (lint + test) ───────────────────────────────────────────────
check: lint test

# ── Cleanup ───────────────────────────────────────────────────────────────────
clean:
	rm -rf .venv __pycache__ .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
