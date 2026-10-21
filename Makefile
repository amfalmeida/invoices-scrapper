COMPOSE ?= docker compose
PYTHON  ?= python3
VENV    ?= .venv
SERVICE := invoices

SHELL := /bin/bash

# Loads .env into the shell for local (non-docker) targets. Variables already set in the
# environment win, so `SINCE_DATE=2026-01-01 make local-dry-run` overrides .env.
LOAD_ENV := [ -f .env ] && while IFS='=' read -r k v; do \
	[[ "$$k" =~ ^[A-Za-z_][A-Za-z0-9_]*$$ ]] || continue; \
	[ -n "$${!k+x}" ] || export "$$k=$$v"; \
	done < .env

.DEFAULT_GOAL := help

.PHONY: help env build up down restart logs run-once dry-run shell venv auth lidl-auth lidl-token lidl-receipt local local-once local-dry-run clean

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

env: ## Create .env from .env.example (if missing)
	@[ -f .env ] && echo ".env already exists" || (cp .env.example .env && echo "Created .env, now edit it")

# --- Docker ---------------------------------------------------------------

build: ## Build the docker image
	$(COMPOSE) build

up: env ## Start the service in the background
	$(COMPOSE) up -d --build

down: ## Stop the service
	$(COMPOSE) down

restart: ## Restart the service
	$(COMPOSE) restart $(SERVICE)

logs: ## Follow the service logs
	$(COMPOSE) logs -f $(SERVICE)

run-once: env ## Run a single fetch+send pass in docker and exit
	$(COMPOSE) run --rm -e RUN_ONCE=true $(SERVICE)

dry-run: env ## Single pass in docker, log what would be sent without sending
	$(COMPOSE) run --rm -e RUN_ONCE=true -e DRY_RUN=true $(SERVICE)

shell: ## Open a shell inside the container
	$(COMPOSE) run --rm $(SERVICE) sh

# --- Local ----------------------------------------------------------------

$(VENV)/bin/activate: requirements.txt
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install -q --upgrade pip
	$(VENV)/bin/pip install -q -r requirements.txt "lidl-plus[auth]" "blinker<1.8" "pyopenssl<24.3"
	@touch $@

# selenium-wire (used for the Lidl login) is unmaintained: it needs blinker._saferef (removed in
# blinker 1.8) and X509.get_extension (removed in pyOpenSSL 24.3)
venv: $(VENV)/bin/activate ## Create local virtualenv with dependencies

lidl-auth: venv env ## Log in to Lidl Plus in a browser and save the refresh token
	$(LOAD_ENV); DATA_DIR=./data $(VENV)/bin/python -m tools.lidl_auth

auth: lidl-auth ## Alias for lidl-auth

lidl-token: venv ## Print a Lidl access token for curl (saves the rotated refresh token)
	@$(LOAD_ENV); DATA_DIR=./data $(VENV)/bin/python -W ignore -m tools.lidl_token

lidl-receipt: venv ## Save all receipts to ./data/receipts/data.json
	$(LOAD_ENV); DATA_DIR=./data $(VENV)/bin/python -W ignore -m tools.lidl_receipt

local: venv env ## Run the service locally (uses ./data for state)
	$(LOAD_ENV); DATA_DIR=./data $(VENV)/bin/python -m invoices

local-once: venv env ## Run a single pass locally
	$(LOAD_ENV); DATA_DIR=./data RUN_ONCE=true $(VENV)/bin/python -m invoices

local-dry-run: venv env ## Single pass locally without sending anything
	$(LOAD_ENV); DATA_DIR=./data RUN_ONCE=true DRY_RUN=true $(VENV)/bin/python -m invoices

clean: ## Remove virtualenv and caches (keeps ./data)
	rm -rf $(VENV)
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
