FROM python:3.12-slim-bookworm

# Install system dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
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
