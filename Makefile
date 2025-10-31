.PHONY: install install-dev test lint format check clean help

help:
	@echo "Fast Fixup Finder - Development Tasks"
	@echo "====================================="
	@echo ""
	@echo "Available targets:"
	@echo "  make install       - Install in development mode"
	@echo "  make install-dev   - Install with dev dependencies (recommended)"
	@echo "  make test          - Run tests with pytest"
	@echo "  make lint          - Run all linting checks (black, flake8, mypy)"
	@echo "  make format        - Format code with black"
	@echo "  make check         - Check formatting/linting without changes"
	@echo "  make clean         - Remove build artifacts and cache"
	@echo "  make help          - Show this help message"
	@echo ""

install:
	python3 -m venv venv
	. venv/bin/activate && pip install --upgrade pip setuptools wheel && pip install -e .

install-dev:
	python3 -m venv venv
	. venv/bin/activate && pip install --upgrade pip setuptools wheel && pip install -e ".[dev]"

test:
	pytest

lint:
	@echo "Running black..."
	black --check .
	@echo "✓ Black passed"
	@echo ""
	@echo "Running flake8..."
	flake8 .
	@echo "✓ Flake8 passed"
	@echo ""
	@echo "Running mypy..."
	mypy .
	@echo "✓ Mypy passed"

format:
	black .
	@echo "✓ Code formatted"

check: lint
	@echo "✓ All checks passed"

clean:
	rm -rf build dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	@echo "✓ Cleaned up build artifacts"
