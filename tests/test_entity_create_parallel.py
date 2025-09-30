"""
Test parallel entity creation with multiple Arkiv clients and accounts.

- Threaded pseudo-parallelism: each thread runs a client and creates entities
- Local: auto-create/fund accounts; External: use .env accounts
- Random payload and annotations
- Pytest parameterization for number of clients/entities
- Entity verification (payload + annotations)
- No cleanup
"""

import logging
import os
import random
import string
import threading
import time
from typing import cast

import pytest
from eth_typing import ChecksumAddress
from testcontainers.core.container import DockerContainer
from web3 import Web3
from web3.exceptions import Web3RPCError

from arkiv import Arkiv
from arkiv.types import AnnotationValue, EntityKey

from .utils import create_account

WALLET_FILE_ENV_PREFIX = "WALLET_FILE"
WALLET_PASSWORD_ENV_PREFIX = "WALLET_PASSWORD"

logger = logging.getLogger(__name__)

# Counter for successful entity creation transactions
tx_counter = 0
tx_counter_lock = threading.Lock()


def create_client(
    container: DockerContainer | None, rpc_url: str, client_idx: int
) -> Arkiv:
    account = create_account(client_idx, f"client_{client_idx}", container)
    client = Arkiv(Web3.HTTPProvider(rpc_url), account=account)

    # Verify connection
    assert client.is_connected(), (
        f"Failed to connect Arkiv client[{client_idx}] to {rpc_url}"
    )

    logger.info(f"Arkiv client[{client_idx}] connected to {rpc_url}")
    return client


def random_payload(size: int = 1024) -> bytes:
    return os.urandom(size)


def random_annotations(client: int, entity_no: int) -> dict[str, AnnotationValue]:
    return {
        "client": client,
        "entity": entity_no,
        "type": random.choice(["test", "parallel", "demo"]),
        "version": random.randint(1, 100),
        "tag": "".join(random.choices(string.ascii_letters, k=8)),
    }


def random_btl(btl_min: int = 100, btl_extension: int = 1000) -> int:
    return btl_min + random.randint(1, btl_extension)


def client_task(client: Arkiv, client_idx: int, num_entities: int) -> list[EntityKey]:
    global tx_counter

    created: list[EntityKey] = []
    for j in range(num_entities):
        # Create entity data
        payload = random_payload()
        annotations = random_annotations(client_idx, j)
        btl = random_btl()

        # Create entity
        try:
            entity_key, tx_hash = client.arkiv.create_entity(
                payload=payload, annotations=annotations, btl=btl
            )
            logger.info(f"Entity creation TX[{client_idx}][{j}]: {tx_hash.to_0x_hex()}")
            created.append(entity_key)

            # entity tx successful, increase counter
            with tx_counter_lock:
                tx_counter += 1

        except Web3RPCError as e:
            logger.error(f"Error creating entity[{client_idx}][{j}]: {e}")

        # Check entity data (based on unique/random entity data)
        try:
            entity = client.arkiv.get_entity(entity_key)
            assert entity.payload == payload, (
                f"Entity payload mismatch[{client_idx}][{j}]"
            )

            assert entity.annotations == annotations, (
                f"Entity annotations mismatch[{client_idx}][{j}]: {entity.annotations} != {annotations}"
            )
        except Web3RPCError as e:
            logger.error(f"Error fetching entity[{client_idx}][{j}]: {e}")

    return created


@pytest.mark.parametrize(
    "num_clients,num_entities",
    [
        (2, 10),
        # (2, 3),
        # (4, 2),
    ],
)
def test_parallel_entity_creation(
    arkiv_node: tuple[DockerContainer | None, str, str],
    num_clients: int,
    num_entities: int,
) -> None:
    container, rpc_url, _ = arkiv_node

    if not rpc_url:
        pytest.skip("No Arkiv node available for testing")

    logger.info(f"Starting {num_clients} Arkiv clients...")
    clients = []
    for i in range(num_clients):
        client_idx = i + 1
        logger.info(f"Starting Arkiv client[{client_idx}] ....")
        client = create_client(container, rpc_url, client_idx)
        account: ChecksumAddress = cast(ChecksumAddress, client.eth.default_account)
        balance = client.eth.get_balance(account)
        if balance > 0:
            logger.info(f"Arkiv client[{client_idx}] started.")
            clients.append(client)
        else:
            logger.warning(f"Arkiv client[{client_idx}] has zero balance.")

    # Remember start time
    start_time = time.time()

    threads = []
    for client_idx in range(len(clients)):
        client = clients[client_idx]
        t = threading.Thread(
            target=client_task, args=(client, client_idx, num_entities)
        )
        threads.append(t)
        t.start()

    logger.info("Started all Arkiv clients, waiting for task completion...")
    for t in threads:
        t.join()

    # Remember end time and calculate elapsed time
    end_time = time.time()
    elapsed_time = end_time - start_time

    logger.info(f"Total successful entity creation TX: {tx_counter}")
    logger.info(f"TX creation start time: {start_time:.2f}, end time: {end_time:.2f}")
    logger.info(f"All Arkiv clients have completed in {elapsed_time:.2f} seconds.")
