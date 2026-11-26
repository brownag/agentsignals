SHELL := /bin/bash

PYTHON ?= python3
PIP    ?= pip
WATCH_INTERVAL ?= 3.0

SYSTEMD_USER_DIR := $(HOME)/.config/systemd/user
SYSTEMD_UNITS    := agentsignals-watch.service

.PHONY: help install install-user test test-cov lint check clean build scan distill watch systemd-dry-run systemd-install systemd-status systemd-uninstall

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
	$(PYTHON) -m pytest tests/ --cov=agentsignals --cov-report=term-missing

lint: ## Run linting checks using ruff
	@if command -v ruff >/dev/null 2>&1; then ruff check agentsignals tests; else echo "ruff not found, skipping."; fi

check: lint test ## Run linting and unit tests

build: ## Build wheel and sdist packages
	$(PYTHON) -m build

clean: ## Clean build artifacts, caches, and test artifacts
	@rm -rf build/ dist/ *.egg-info .pytest_cache/ .coverage htmlcov/ __pycache__ agentsignals/__pycache__ tests/__pycache__ || true

scan: ## Run agentsignals on-demand scan across /tmp/claude-1000
	agentsignals scan --no-debounce

distill: ## Distill unparsed dossiers into memory blocks
	agentsignals distill

watch: ## Run agentsignals continuous watch daemon (WATCH_INTERVAL, default 3.0 s)
	agentsignals watch --interval $(WATCH_INTERVAL) --auto-distill

systemd-dry-run: ## Preview systemd unit installation
	$(PYTHON) -m agentsignals.cli install-systemd --dry-run

systemd-install: ## Install units, then enable the watch service
	$(PYTHON) -m agentsignals.cli install-systemd
	systemctl --user daemon-reload
	systemctl --user enable --now agentsignals-watch.service

systemd-status: ## Show status of the agentsignals watch unit
	@systemctl --user status $(SYSTEMD_UNITS) --no-pager || true

systemd-uninstall: ## Disable and remove the agentsignals user units
	-systemctl --user disable --now $(SYSTEMD_UNITS)
	rm -f $(addprefix $(SYSTEMD_USER_DIR)/,$(SYSTEMD_UNITS))
	systemctl --user daemon-reload
