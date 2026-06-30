SHELL := /usr/bin/env bash

ROOT_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
LOCAL_SCRIPT := $(ROOT_DIR)scripts/local.sh
DEV_SCRIPT := $(ROOT_DIR)scripts/dev.sh

STACK ?=
SUITE ?= infra
SKIP_FRONTEND ?= false

.PHONY: help local-up local-down local-test dev-deploy dev-destroy dev-test dev-bootstrap dev-sync-frontend

help:
	@echo "CV Match Makefile"
	@echo ""
	@echo "Local environment targets:"
	@echo "  make local-up STACK=<gateway|profile|gateway,profile|full> [SKIP_FRONTEND=true]"
	@echo "  make local-down STACK=<gateway|profile|gateway,profile|full>"
	@echo "  make local-test STACK=<gateway|profile|gateway,profile|full> SUITE=<unit|integration>"
	@echo ""
	@echo "Dev (AWS) targets:"
	@echo "  make dev-deploy STACK=<network|security|auth|data|gateway|profile|full>"
	@echo "  make dev-destroy STACK=<network|security|auth|data|gateway|profile|full>"
	@echo "  make dev-test [STACK=<...>] [SUITE=<infra|smoke>]"
	@echo "  make dev-bootstrap"
	@echo "  make dev-sync-frontend"
	@echo ""
	@echo "Examples:"
	@echo "  make local-up STACK=full"
	@echo "  make local-test STACK=gateway SUITE=unit"
	@echo "  make dev-deploy STACK=network,security,auth,data,profile,gateway"
	@echo "  make dev-test SUITE=infra"
	@echo "  make dev-test STACK=full SUITE=smoke"

local-up:
	@if [[ -z "$(STACK)" ]]; then echo "error: STACK is required" >&2; exit 1; fi
	@args=(--action up --stack "$(STACK)"); \
	if [[ "$(SKIP_FRONTEND)" == "true" ]]; then args+=(--skip-frontend); fi; \
	bash "$(LOCAL_SCRIPT)" "$${args[@]}"

local-down:
	@if [[ -z "$(STACK)" ]]; then echo "error: STACK is required" >&2; exit 1; fi
	@bash "$(LOCAL_SCRIPT)" --action down --stack "$(STACK)"

local-test:
	@if [[ -z "$(STACK)" ]]; then echo "error: STACK is required" >&2; exit 1; fi
	@if [[ -z "$(SUITE)" ]]; then echo "error: SUITE is required" >&2; exit 1; fi
	@bash "$(LOCAL_SCRIPT)" --action test --stack "$(STACK)" --suite "$(SUITE)"

dev-deploy:
	@if [[ -z "$(STACK)" ]]; then echo "error: STACK is required" >&2; exit 1; fi
	@bash "$(DEV_SCRIPT)" --action deploy --stack "$(STACK)"

dev-destroy:
	@if [[ -z "$(STACK)" ]]; then echo "error: STACK is required" >&2; exit 1; fi
	@bash "$(DEV_SCRIPT)" --action destroy --stack "$(STACK)"

dev-test:
	@if [[ "$(SUITE)" == "smoke" && -z "$(STACK)" ]]; then echo "error: STACK is required when SUITE=smoke" >&2; exit 1; fi
	@if [[ -n "$(STACK)" ]]; then \
		bash "$(DEV_SCRIPT)" --action test --stack "$(STACK)" --suite "$(SUITE)"; \
	else \
		bash "$(DEV_SCRIPT)" --action test --suite "$(SUITE)"; \
	fi

dev-bootstrap:
	@bash "$(DEV_SCRIPT)" --action bootstrap

dev-sync-frontend:
	@bash "$(DEV_SCRIPT)" --action sync-frontend
