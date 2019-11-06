.PHONY: default deps base build stop shell test coverage run

export SERVICE_NAME := flask-calendar

BUILD_ENV ?= dev

HISTORY_FILE := ~/.bash_history.$(SERVICE_NAME)

# Required for the `deps` task
SHELL := $(shell which bash)

DOCKER := $(shell command -v docker)
COMPOSE := $(shell command -v docker-compose)

COMPOSE_ENV := $(COMPOSE) -f build/$(BUILD_ENV)/docker-compose.yml
COMPOSE_CMD := $(COMPOSE_ENV) run --rm $(SERVICE_NAME)

export GID := $(shell id -g)
export UID := $(shell id -u)

deps:
ifndef DOCKER
	@echo "Docker is not available. Please install docker"
	@exit 1
endif
ifndef COMPOSE
	@echo "docker-compose is not available. Please install docker-compose"
	@exit 1
endif
	@touch $(HISTORY_FILE)

base: deps
	sudo $(COMPOSE) -f build/base/docker-compose.yml build

build: base
	sudo $(COMPOSE_ENV) build

stop:
	sudo $(COMPOSE_ENV) stop
	sudo $(COMPOSE_ENV) rm -f -v

shell: build
	sudo $(COMPOSE_CMD) /bin/bash

test: build
	set -o pipefail; \
	sudo $(COMPOSE_CMD) pytest -s

# opening html file currently only works on Linux
coverage: build
	set -o pipefail; \
	sudo $(COMPOSE_CMD) pytest --cov-report html:cov_html --cov=. --cov-config .coveragerc; \
	xdg-open cov_html/index.html

run: build
	sudo $(COMPOSE_ENV) run --rm --service-ports $(SERVICE_NAME);$(COMPOSE_ENV) stop
