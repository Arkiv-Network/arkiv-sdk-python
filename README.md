# Golem Base

This is part of the [Golem Base](https://github.com/Golem-Base) project, which is designed as a Layer2 Network deployed on Ethereum, acting as a gateway to various Layer 3 Database Chains (DB-Chains).

> **For an overview of Golem Base, check out our [Litepaper](https://golem-base.io/wp-content/uploads/2025/03/GolemBase-Litepaper.pdf).**

# GolemBase SDK for Python

This SDK allows you to use [GolemBase](https://github.com/Golem-Base) from Python. It is available [on PyPI](https://pypi.org/project/golem-base-sdk/).

We also publish [generated documentation](https://golem-base.github.io/python-sdk/).

The repo also contains an example application to showcase how you can use this SDK.

**Tip:** For getting up and running quickly, we recommend the following two steps:

- Start golembase-op-geth through its [docker-compose](https://github.com/Golem-Base/golembase-op-geth/blob/main/RUN_LOCALLY.md).

- [Install the demo CLI](https://github.com/Golem-Base/golembase-demo-cli?tab=readme-ov-file#installation) and [create a user](https://github.com/Golem-Base/golembase-demo-cli?tab=readme-ov-file#quickstart).

(Note: As an alternative to installing the demo CLI, you can build the [actual CLI](https://github.com/Golem-Base/golembase-op-geth/blob/main/cmd/golembase/README.md) as it's included in the golembase-op-geth repo.)

When you create a user, it will generate a private key file called `wallet.json` and store it in:

* `~/.config/golembase/` on **Linux**
* `~/Library/Application Support/golembase/` on **macOS**
* `%LOCALAPPDATA%\golembase\` on **Windows**

(This is a standard folder as per the [XDG specification](https://specifications.freedesktop.org/basedir-spec/latest/).)

You will also need to fund the account. You can do so by typing:

```
golembase-demo-cli account fund 10
```

## Getting Started Example

Here's how you can get going with the SDK. First, create a new folder to hold your project:

```bash
mkdir golem-sdk-practice
cd golem-sdk-practice
```

Then create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

Next, install the GolemBase SDK from PyPI:

```bash
pip install golem-base-sdk
```

You can find some [base starter code here](https://github.com/Golem-Base/python-sdk/tree/main/example); copy the `__init__.py` into your project folder.

This is a basic Python application that:

- Imports several items from the SDK (`golem_base_sdk`), including:

   * `GolemBaseClient`: A class that creates a client to interact with GolemBase
   * `GolemBaseCreate`: A class representing a create transaction in GolemBase
   * `GolemBaseExtend`: A class for extending entity lifetime
   * `Annotation`: A class for key-value annotations

- Reads the private key, which it locates using the `xdg` module.

- Sets up logging with the standard Python `logging` module.

- The `main()` function follows, which is where the bulk of the example code runs.

The `main` function demonstrates how to create, extend, and query entities:

- Creates a client object that connects to the GolemBase network (e.g., Kaolin testnet) using `rpc` and `ws` URLs, and your private key.

- Subscribes to log events from the network (create, update, delete, extend).

- Creates an entity with data `"hello"`, BTL of `60`, and an annotation of `("foo", "bar")`.

- Prints various metadata and state:

   * The latest block
   * Entity count before and after creation
   * Entity metadata
   * Storage value
   * Entity expiration info
   * Query results by annotation

- Extends the created entity’s lifetime using `client.extend_entities`.

- Lists entities owned by your account, and all known entity keys.

## Building and Running from sources

You can also, from this cloned repo, build the SDK and run the example using [Nix](https://nixos.org):

```bash
nix build .#golem-base-sdk-example
./result/bin/main
```
