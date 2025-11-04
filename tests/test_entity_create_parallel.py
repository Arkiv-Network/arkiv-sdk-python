"""
Test parallel entity creation with multiple Arkiv clients and accounts.

- Threaded pseudo-parallelism: each thread runs a client and creates entities
- Local: auto-create/fund accounts; External: use .env accounts
- Random payload and attributes
- Pytest parameterization for number of clients/entities
- Entity verification (payload + attributes)
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
from requests import HTTPError
from web3 import Web3
from web3.exceptions import Web3RPCError

from arkiv import Arkiv
from arkiv.types import Attributes, CreateOp, EntityKey
from tests.conftest import arkiv_client_http

from .utils import create_account, create_entities

NUM_CLIENTS_ENV = "NUM_CLIENTS"
NUM_TX_ENV = "NUM_TX"
BATCH_SIZE_ENV = "BATCH_SIZE"
VERIFY_SAMPLE_SIZE_ENV = "VERIFY_SAMPLE_SIZE"

logger = logging.getLogger(__name__)

# Counters for successful entity creation transactions and verifications
tx_counter = 0
verified_counter = 0
tx_counter_lock = threading.Lock()
verified_counter_lock = threading.Lock()


def create_client(rpc_url: str, client_idx: int) -> Arkiv:
    account = create_account(client_idx, f"client_{client_idx}")
    client = Arkiv(Web3.HTTPProvider(rpc_url), account=account)

    # Verify connection
    assert client.is_connected(), (
        f"Failed to connect Arkiv client[{client_idx}] to {rpc_url}"
    )

    logger.info(f"Arkiv client[{client_idx}] connected to {rpc_url}")
    return client


def random_payload(size: int = 128) -> bytes:
    return os.urandom(size)


def random_attributes(client: int, entity_no: int) -> Attributes:
    return Attributes(
        {
            "client": client,
            "entity": entity_no,
            "type": random.choice(["test", "parallel", "demo"]),
            "version": random.randint(1, 100),
            "tag": "".join(random.choices(string.ascii_letters, k=8)),
        }
    )


def random_btl(btl_min: int = 100, btl_extension: int = 1000) -> int:
    return btl_min + random.randint(1, btl_extension)


def client_creation_task(
    client: Arkiv,
    client_idx: int,
    num_tx: int,
    batch_size: int,
) -> list[tuple[EntityKey, bytes, Attributes]]:
    """
    Create entities and return them with their expected data for later verification.

    Returns:
        List of tuples (entity_key, expected_payload, expected_attributes)
    """
    global tx_counter

    created_entities: list[tuple[EntityKey, bytes, Attributes]] = []

    for tx_no in range(num_tx):
        # Prepare entities for this transaction
        entities_in_batch = []
        for entity_no in range(batch_size):
            entity_index = tx_no * batch_size + entity_no
            payload = random_payload()
            attributes = random_attributes(client_idx, entity_index)
            btl = random_btl()
            entities_in_batch.append((payload, attributes, btl))

        # Create entity/entities based on batch_size
        try:
            if batch_size == 1:
                # Single entity creation
                payload, attributes, btl = entities_in_batch[0]
                try:
                    entity_key, tx_hash = client.arkiv.create_entity(
                        payload=payload, attributes=attributes, btl=btl
                    )
                    logger.info(
                        f"Entity creation TX[{client_idx}][{tx_no}]: {tx_hash} (1 entity)"
                    )
                    created_entities.append((entity_key, payload, attributes))
                except HTTPError as e:
                    logger.error(f"Error creating entity[{client_idx}][{tx_no}]: {e}")
                    continue
            else:
                # Bulk entity creation
                create_ops = [
                    CreateOp(payload=p, attributes=a, btl=b)
                    for p, a, b in entities_in_batch
                ]
                try:
                    entity_keys, tx_hash = create_entities(
                        arkiv_client_http, create_ops
                    )
                    logger.info(
                        f"Entity creation TX[{client_idx}][{tx_no}]: {tx_hash} ({len(entity_keys)} entities)"
                    )
                    # Store all created entities with their expected data
                    for i, entity_key in enumerate(entity_keys):
                        payload, attributes, btl = entities_in_batch[i]
                        created_entities.append((entity_key, payload, attributes))
                except HTTPError as e:
                    logger.error(f"Error creating entities[{client_idx}][{tx_no}]: {e}")
                    continue

            # entity tx successful, increase counter
            with tx_counter_lock:
                tx_counter += 1

        except Web3RPCError as e:
            logger.error(f"Error creating entities[{client_idx}][{tx_no}]: {e}")
            continue

    return created_entities


def verify_entities_task(
    client: Arkiv,
    client_idx: int,
    entities_to_verify: list[tuple[EntityKey, bytes, Attributes]],
    verify_sample_size: int,
) -> int:
    """
    Verify a sample of entities after all entities have been created.

    Args:
        client: Arkiv client to use for verification
        client_idx: Client index for logging
        entities_to_verify: List of (entity_key, expected_payload, expected_attributes)
        verify_sample_size: Number of entities to verify (0=none, -1=all, N=random sample)

    Returns:
        Number of successfully verified entities
    """
    global verified_counter

    if not entities_to_verify:
        return 0

    # Determine which entities to verify
    if verify_sample_size < 0:
        # Verify all entities
        sample_to_verify = entities_to_verify
    elif verify_sample_size == 0:
        # No verification
        return 0
    else:
        # Verify a random sample
        num_to_verify = min(verify_sample_size, len(entities_to_verify))
        sample_to_verify = random.sample(entities_to_verify, num_to_verify)

    logger.info(
        f"Client[{client_idx}]: Verifying {len(sample_to_verify)} of {len(entities_to_verify)} entities"
    )

    local_verified = 0
    for idx, (entity_key, expected_payload, expected_attributes) in enumerate(
        sample_to_verify
    ):
        try:
            entity = client.arkiv.get_entity(entity_key)

            # Verify payload
            if entity.payload != expected_payload:
                logger.warning(
                    f"Entity payload mismatch[{client_idx}][{idx}]: "
                    f"expected {len(expected_payload) if expected_payload else 0} bytes, "
                    f"got {len(entity.payload) if entity.payload else 0} bytes"
                )
                continue

            # Verify attributes
            if entity.attributes != expected_attributes:
                logger.warning(
                    f"Entity attributes mismatch[{client_idx}][{idx}]: "
                    f"{entity.attributes} != {expected_attributes}"
                )
                continue

            # Successfully verified
            local_verified += 1

        except Web3RPCError as e:
            logger.warning(f"Error fetching entity[{client_idx}][{idx}]: {e}")
        except Exception as e:
            logger.warning(
                f"Unexpected error verifying entity[{client_idx}][{idx}]: {e}"
            )

    # Update global counter
    with verified_counter_lock:
        verified_counter += local_verified

    return local_verified


def setup_clients(rpc_url: str, num_clients: int) -> list[Arkiv]:
    """
    Create and fund Arkiv clients for testing.

    Args:
        rpc_url: RPC URL to connect to
        num_clients: Number of clients to create

    Returns:
        List of connected and funded Arkiv clients
    """
    logger.info(f"Starting {num_clients} Arkiv clients...")
    clients = []
    for i in range(num_clients):
        client_idx = i + 1
        logger.info(f"Starting Arkiv client[{client_idx}] ....")
        client = create_client(rpc_url, client_idx)
        account: ChecksumAddress = cast(ChecksumAddress, client.eth.default_account)
        balance = client.eth.get_balance(account)

        # Only use clients with non-zero balance
        if balance > 0:
            logger.info(f"Arkiv client[{client_idx}] started.")
            clients.append(client)
        else:
            logger.warning(f"Arkiv client[{client_idx}] has zero balance.")

    return clients


def run_creation_phase(
    clients: list[Arkiv], num_tx: int, batch_size: int
) -> tuple[list[list[tuple[EntityKey, bytes, Attributes]]], float, int]:
    """
    Execute Phase 1: Create entities in parallel across all clients.

    Args:
        clients: List of Arkiv clients
        num_tx: Number of transactions per client
        batch_size: Number of entities per transaction

    Returns:
        Tuple of (creation_results, elapsed_time, tx_count)
        - creation_results: List of entity data per client
        - elapsed_time: Duration of creation phase
        - tx_count: Number of successful transactions
    """
    global tx_counter

    logger.info("=" * 80)
    logger.info("PHASE 1: Creating entities across all clients in parallel...")
    logger.info("-" * 80)
    creation_start_time = time.time()

    # Store results from each thread
    creation_results: list[list[tuple[EntityKey, bytes, Attributes]]] = [
        [] for _ in range(len(clients))
    ]

    def creation_wrapper(idx: int) -> None:
        creation_results[idx] = client_creation_task(
            clients[idx], idx, num_tx, batch_size
        )

    # Start all creation threads
    threads = []
    for client_idx in range(len(clients)):
        t = threading.Thread(target=creation_wrapper, args=(client_idx,))
        threads.append(t)
        t.start()

    logger.info("Started all creation threads, waiting for completion...")
    for t in threads:
        t.join()

    creation_elapsed = time.time() - creation_start_time

    # Read TX counter and reset for next test run
    with tx_counter_lock:
        final_tx_count = tx_counter
        tx_counter = 0

    total_entities_created = sum(len(entities) for entities in creation_results)

    logger.info("-" * 80)
    logger.info("PHASE 1 COMPLETE: Entity creation finished")
    logger.info(f"Total successful TX: {final_tx_count}")
    logger.info(f"Total entities created: {total_entities_created}")
    logger.info(f"Creation phase duration: {creation_elapsed:.2f} seconds")
    logger.info(f"Average TX/sec: {final_tx_count / creation_elapsed:.2f}")
    logger.info(
        f"Average entities/sec: {total_entities_created / creation_elapsed:.2f}"
    )
    logger.info("-" * 80)

    return creation_results, creation_elapsed, final_tx_count


def run_verification_phase(
    clients: list[Arkiv],
    creation_results: list[list[tuple[EntityKey, bytes, Attributes]]],
    verify_sample_size: int,
    sync_delay: float = 2.0,
) -> tuple[int, float]:
    """
    Execute Phase 2: Verify entities in parallel across all clients.

    Args:
        clients: List of Arkiv clients
        creation_results: Entity data from creation phase
        verify_sample_size: Number of entities to verify (0=none, -1=all, N=sample)
        sync_delay: Seconds to wait for node synchronization

    Returns:
        Tuple of (verified_count, elapsed_time)
    """
    global verified_counter

    total_entities = sum(len(entities) for entities in creation_results)

    if verify_sample_size == 0 or total_entities == 0:
        logger.info("Skipping verification phase (verify_sample_size=0)")
        return 0, 0.0

    logger.info(f"Waiting {sync_delay} seconds for node synchronization...")
    time.sleep(sync_delay)

    logger.info("=" * 80)
    logger.info("PHASE 2: Verifying entities across all clients in parallel...")
    logger.info("-" * 80)
    verification_start_time = time.time()

    # Start all verification threads
    threads = []
    for client_idx in range(len(clients)):
        client = clients[client_idx]
        entities_to_verify = creation_results[client_idx]
        t = threading.Thread(
            target=verify_entities_task,
            args=(client, client_idx, entities_to_verify, verify_sample_size),
        )
        threads.append(t)
        t.start()

    logger.info("Started all verification threads, waiting for completion...")
    for t in threads:
        t.join()

    verification_elapsed = time.time() - verification_start_time

    # Read verification counter and reset for next test run
    with verified_counter_lock:
        final_verified_count = verified_counter
        verified_counter = 0

    verification_percentage = (final_verified_count / total_entities) * 100
    logger.info("-" * 80)
    logger.info("PHASE 2 COMPLETE: Entity verification finished")
    logger.info(
        f"Total entities verified: {final_verified_count} ({verification_percentage:.1f}%)"
    )
    logger.info(f"Verification phase duration: {verification_elapsed:.2f} seconds")

    return final_verified_count, verification_elapsed


def log_test_summary(
    num_clients: int,
    num_tx: int,
    batch_size: int,
    tx_count: int,
    entities_created: int,
    entities_verified: int,
    seconds_elapsed: float,
) -> None:
    """
    Log comprehensive test summary statistics.
    """
    logger.info("-" * 80)
    logger.info("TEST SUMMARY")
    logger.info(f"Total active clients: {num_clients}")
    logger.info(f"TX per client: {num_tx}")
    logger.info(f"Entities per batch: {batch_size}")
    logger.info(f"Total successful TX: {tx_count}")
    logger.info(f"Total entities created: {entities_created}")
    logger.info(f"Total entities verified: {entities_verified}")
    logger.info(f"Total test duration: {seconds_elapsed:.2f} seconds")
    if seconds_elapsed > 0:
        logger.info(f"Average TX/sec: {tx_count / seconds_elapsed:.2f}")
        logger.info(f"Average entities/sec: {entities_created / seconds_elapsed:.2f}")
    logger.info("=" * 80)


def get_parallel_entity_creation_parameters(
    defaults: list[tuple[int, int, int, int]],
) -> list[tuple[int, int, int, int]]:
    (clients, txs, batch_size, verify_sample_size) = defaults

    clients_env = os.getenv(NUM_CLIENTS_ENV)
    txs_env = os.getenv(NUM_TX_ENV)
    batch_size_env = os.getenv(BATCH_SIZE_ENV)
    verify_sample_size_env = os.getenv(VERIFY_SAMPLE_SIZE_ENV)

    if clients_env:
        clients = int(clients_env)
    if txs_env:
        txs = int(txs_env)
    if batch_size_env:
        batch_size = int(batch_size_env)
    if verify_sample_size_env:
        verify_sample_size = int(verify_sample_size_env)

    parameters = (clients, txs, batch_size, verify_sample_size)
    logger.info(
        f"Using parallel entity creation parameters (clients, txs, batch_size, verify_sample_size): {parameters}"
    )
    return parameters


@pytest.mark.parametrize(
    "num_clients,num_tx,batch_size,verify_sample_size",
    [
        get_parallel_entity_creation_parameters(
            (2, 3, 2, -1)
        ),  # 2 clients, 3 tx/client, 2 entities/tx, verify all (-1 = all)
        # (1, 2, 4, 2),  # 1 client, 2 tx/client, 4 entities/tx, verify 2 random/tx
    ],
)
def test_parallel_entity_creation(
    arkiv_node,
    num_clients: int,
    num_tx: int,
    batch_size: int,
    verify_sample_size: int,
) -> None:
    """
    Test parallel entity creation and verification across multiple clients.

    This test is organized in two phases:
    1. Creation Phase: All clients create entities in parallel
    2. Verification Phase: After sync delay, verify entities in parallel

    The separation allows the distributed Arkiv node network to synchronize
    between creation and verification, avoiding stale read issues.
    """
    rpc_url = arkiv_node.http_url

    if not rpc_url:
        pytest.skip("No Arkiv node available for testing")

    test_start_time = time.time()

    # Setup: Create and fund clients
    clients = setup_clients(rpc_url, num_clients)

    # Phase 1: Create entities
    creation_results, _, tx_count = run_creation_phase(clients, num_tx, batch_size)
    total_entities_created = sum(len(entities) for entities in creation_results)

    # Measure total elapsed time for entity creation (without verification)
    seconds_elapsed = time.time() - test_start_time

    # Phase 2: Verify entities
    verified_count, _ = run_verification_phase(
        clients, creation_results, verify_sample_size
    )

    # Summary
    log_test_summary(
        num_clients=len(clients),
        num_tx=num_tx,
        batch_size=batch_size,
        tx_count=tx_count,
        entities_created=total_entities_created,
        entities_verified=verified_count,
        seconds_elapsed=seconds_elapsed,
    )
