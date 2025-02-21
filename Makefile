PYTHON ?= python3
PIP ?= pip3

DOCKER_BASE_IMAGE = docker.io/ocrd/core:v3.0.4
DOCKER_TAG = ocrd/pagetopdf

help:
	@echo ""
	@echo "  Targets"
	@echo ""
	@echo "    deps-ubuntu	Install system dependencies (on Debian/Ubuntu)"
	@echo "    deps       	Install Python dependencies via $(PIP)"
	@echo "    install    	Install the Python package via $(PIP)"
	@echo "    install-dev 	Install in editable mode"
	@echo "    build 	Build source and binary distribution"
	@echo "    docker     	Build Docker image"

# Install system packages (on Debian/Ubuntu)
deps-ubuntu:
	apt-get install -y python3 python3-venv default-jre-headless ghostscript git

# Install python packages
deps:
	$(PIP) install -r requirements.txt

install:
	$(PIP) install .

install-dev:
	$(PIP) install -e .

build:
	$(PIP) install build wheel
	$(PYTHON) -m build .

# Build Docker image
docker:
	docker build \
	--build-arg DOCKER_BASE_IMAGE=$(DOCKER_BASE_IMAGE) \
	--build-arg VCS_REF=$$(git rev-parse --short HEAD) \
	--build-arg BUILD_DATE=$$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
	-t $(DOCKER_TAG) .

.PHONY: help deps-ubuntu deps install install-dev docker
