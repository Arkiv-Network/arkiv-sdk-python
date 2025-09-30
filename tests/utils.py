import logging
import os
import time
from pathlib import Path

from testcontainers.core.container import DockerContainer

from arkiv.account import NamedAccount

WALLET_FILE_ENV_PREFIX = "WALLET_FILE"
WALLET_PASSWORD_ENV_PREFIX = "WALLET_PASSWORD"

WAIT_FOR_FUNDING = 2

logger = logging.getLogger(__name__)


def create_account(
    index: int, name: str, container: DockerContainer | None
) -> NamedAccount:
    """Create a named account from env vars or generate a new one."""
    wallet_file = os.getenv(f"{WALLET_FILE_ENV_PREFIX}_{index}")
    wallet_password = os.getenv(f"{WALLET_PASSWORD_ENV_PREFIX}_{index}")

    if not wallet_file or not wallet_password:
        account = NamedAccount.create(name)
        if type(container) is DockerContainer:
            fund_account(container, account)
        return account

    logger.info(f"Using existing wallet: {wallet_file}")
    wallet_json = load_wallet_json(wallet_file)
    return NamedAccount.from_wallet(name, wallet_json, wallet_password)


def load_wallet_json(wallet_file: str) -> str:
    """Load account from encrypted wallet file."""
    wallet_path = Path(wallet_file)
    with wallet_path.open() as f:
        return f.read()


def fund_account(arkivContainer: DockerContainer, account: NamedAccount) -> None:
    """Fixture to create and fund a test account in the Arkiv node."""

    # Import account inside the container
    exit_code, output = arkivContainer.exec(
        ["golembase", "account", "import", "--key", account.key.hex()]
    )
    assert exit_code == 0, f"Account import failed: {output.decode()}"

    # Fund account inside the container
    logger.info(f"Funding account: '{account.name}' ({account.address})")
    exit_code, output = arkivContainer.exec(["golembase", "account", "fund"])
    assert exit_code == 0, f"Account funding failed: {output.decode()}"
    logger.info(f"Imported and funded account: {account.address}")

    # Wait for the funding transaction to be mined
    time.sleep(WAIT_FOR_FUNDING)

    # Printing account balance
    exit_code, output = arkivContainer.exec(["golembase", "account", "balance"])
    assert exit_code == 0, f"Account balance check failed: {output.decode()}"
    logger.info(f"Account balance: {output.decode().strip()}, exit_code: {exit_code}")
