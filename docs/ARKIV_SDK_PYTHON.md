# Arkiv SDK for Python

## Requirements

- Python: >= 3.10
- UV or pip

## Commands

### Setup Project (PIP)

```shell
python3 -m venv .venv
source .venv/bin/activate
```

### Install Arkiv SDK and Packages

```shell
pip install arkiv-sdk==1.0.0a8
pip install testcontainers websockets
```

### Setup Project (UV)

```shell
uv init voting-board
```

### Install SDK and Packages

```shell
uv add arkiv-sdk --prerelease=allow
uv add testcontainers websockets
```

### Run Application

```
uv run main.py
```

### Update SDK

```shell
npm update arkiv-sdk
```

## Files

### .python-version

```
3.14
```

Versions 3.10, 3.11, 3.12, 3.13 are supported too

### pyproject.toml

```
[project]
name = "app"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.14"
dependencies = [
    "arkiv-sdk>=1.0.0a8",
    "testcontainers>=4.13.3",
    "websockets>=15.0.1",
]
```
