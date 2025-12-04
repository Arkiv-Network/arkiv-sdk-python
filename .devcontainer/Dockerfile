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
    ca-certificates \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Create vscode user and grant sudo privileges
RUN useradd -m -s /bin/bash -u 1000 vscode && \
    echo "vscode ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Switch to vscode user
USER vscode

# Install uv and add it to PATH (install for vscode user)
ADD --chown=vscode:vscode https://astral.sh/uv/install.sh /tmp/uv-installer.sh
RUN sh /tmp/uv-installer.sh && rm /tmp/uv-installer.sh
ENV PATH="/home/vscode/.local/bin:$PATH"

# Suppress UV hardlink warnings in dev containers
ENV UV_LINK_MODE=copy

WORKDIR /workspace
