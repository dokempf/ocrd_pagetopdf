PYTHON ?= python3
PIP ?= pip3
PYTEST_ARGS ?= -vv

DOCKER_BASE_IMAGE = docker.io/ocrd/core:v3.3.0
DOCKER_TAG = ocrd/pagetopdf

help:
	@echo ""
	@echo "  Targets"
	@echo ""
	@echo "    deps-ubuntu	Install system dependencies (on Debian/Ubuntu)"
	@echo "    deps       	Install Python dependencies via $(PIP)"
	@echo "    deps-test  	Install Python deps for test via $(PIP)"
	@echo "    install    	Install the Python package via $(PIP)"
	@echo "    install-dev 	Install in editable mode"
	@echo "    build 	Build source and binary distribution"
	@echo "    docker     	Build Docker image"
	@echo "    test         Run tests via Pytest"
	@echo "    repo/assets  Clone OCR-D/assets to ./repo/assets"
	@echo "    tests/assets Setup test assets"
	@echo ""
	@echo "  Variables"
	@echo ""
	@echo "    DOCKER_TAG  Docker container tag ($(DOCKER_TAG))"
	@echo "    PYTEST_ARGS Additional runtime options for pytest ($(PYTEST_ARGS))"
	@echo "                (See --help, esp. custom option --workspace)"

# Install system packages (on Debian/Ubuntu)
deps-ubuntu:
	apt-get update && apt-get install -y --no-install-recommends \
		python3 python3-venv default-jre-headless ghostscript git

# Install python packages
deps:
	$(PIP) install -r requirements.txt

deps-test:
	$(PIP) install -r requirements-test.txt

install:
	$(PIP) install .

install-dev:
	$(PIP) install -e .

build:
	$(PIP) install build wheel
	$(PYTHON) -m build .

# TODO: once core#1149 is fixed, remove this line (so the local copy can be used)
test: export OCRD_BASEURL=https://github.com/OCR-D/assets/raw/refs/heads/master/data/
# Run test
test: tests/assets
	$(PYTHON) -m pytest  tests --durations=0 $(PYTEST_ARGS)

#
# Assets
#

# Update OCR-D/assets submodule
.PHONY: repos always-update tests/assets
repo/assets: always-update
	git submodule sync --recursive $@
	if git submodule status --recursive $@ | grep -qv '^ '; then \
		git submodule update --init --recursive $@ && \
		touch $@; \
	fi

# Setup test assets
tests/assets: repo/assets
	mkdir -p tests/assets
	cp -a repo/assets/data/* tests/assets

# Build Docker image
docker:
	docker build \
	--build-arg DOCKER_BASE_IMAGE=$(DOCKER_BASE_IMAGE) \
	--build-arg VCS_REF=$$(git rev-parse --short HEAD) \
	--build-arg BUILD_DATE=$$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
	-t $(DOCKER_TAG) .

.PHONY: help deps-ubuntu deps deps-test install install-dev build docker
