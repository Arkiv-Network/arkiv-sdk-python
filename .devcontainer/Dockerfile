FROM python:3.12-slim-bookworm

# Install system dependencies
# Note: build-essential is required for ARM64 architectures to compile
# Python packages that don't have pre-built wheels (like ruff, maturin, etc.)
# docker.io provides the Docker CLI for testcontainers
# openssh-client provides ssh for git operations over SSH
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    build-essential \
    docker.io \
    openssh-client \
    nano \
    curl \
    iputils-ping \
    ca-certificates

# Install uv and add it to PATH
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh

ENV PATH="/root/.local/bin/:$PATH"

# Suppress UV hardlink warnings in dev containers
ENV UV_LINK_MODE=copy

WORKDIR /workspace
