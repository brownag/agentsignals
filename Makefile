SHELL := /bin/bash

PYTHON ?= python3
PIP    ?= pip

.PHONY: help install install-user test test-cov lint check clean build scan distill watch systemd-dry-run systemd-install

.DEFAULT_GOAL := help

help: ## Show this help message
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

install: ## Install package in editable mode with dev dependencies
	$(PIP) install -e ".[dev]" --break-system-packages

install-user: ## Install package in user mode without modifying system packages
	$(PIP) install -e . --no-deps --break-system-packages --user

test: ## Run unit tests with pytest
	$(PYTHON) -m pytest tests/ -v

test-cov: ## Run unit tests with code coverage report
	$(PYTHON) -m pytest tests/ --cov=claudalizer --cov-report=term-missing

lint: ## Run linting checks using ruff
	@command -v ruff >/dev/null 2>&1 && ruff check claudalizer tests || echo "ruff not found, skipping."

check: lint test ## Run linting and unit tests

build: ## Build wheel and sdist packages
	$(PYTHON) -m build

clean: ## Clean build artifacts, caches, and test artifacts
	@rm -rf build/ dist/ *.egg-info .pytest_cache/ .coverage htmlcov/ __pycache__ claudalizer/__pycache__ tests/__pycache__ || true

scan: ## Run claudalizer on-demand scan across /tmp/claude-1000
	claudalizer scan --no-debounce

distill: ## Distill unparsed dossiers into memory blocks
	claudalizer distill

watch: ## Run claudalizer continuous watch daemon
	claudalizer watch --interval 5.0 --notify --auto-distill

systemd-dry-run: ## Preview systemd unit installation
	claudalizer install-systemd --dry-run

systemd-install: ## Install user-level systemd service and path units
	claudalizer install-systemd
