"""
Arkiv SDK quickstart — demonstrates core entity operations.

Prerequisites:
    pip install 'arkiv-sdk[dev]'

    Or connect to an external node by setting these env vars:
        ARKIV_HTTP_URL=http://localhost:8545
        ARKIV_WS_URL=ws://localhost:8546
        ARKIV_PRIVATE_KEY=0x<hex>

Run:
    python examples/quickstart.py
"""

import json
import logging
import os
import time

from dotenv import load_dotenv

load_dotenv()  # loads .env from the project root (or any parent directory)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

from arkiv import Arkiv
from arkiv.account import NamedAccount
from arkiv.node import ArkivNode
from arkiv.provider import ProviderBuilder
from arkiv.types import (
    ALL,
    ATTRIBUTES,
    KEY,
    OWNER,
    PAYLOAD,
    Attributes,
    CreateEvent,
    QueryOptions,
    TxHash,
)


def build_client() -> tuple[Arkiv, ArkivNode | None]:
    http_url = os.getenv("ARKIV_HTTP_URL")
    ws_url = os.getenv("ARKIV_WS_URL")
    private_key = os.getenv("ARKIV_PRIVATE_KEY")

    if http_url and ws_url and private_key:
        logger.info("Connecting to external node at %s", http_url)
        node = ArkivNode(http_url=http_url, ws_url=ws_url)
        provider = ProviderBuilder().node(node).build()
        account = NamedAccount.from_private_key("default", private_key)
        return Arkiv(provider, account=account), node

    logger.info("Starting local Docker node (requires testcontainers)…")
    node = ArkivNode()
    node.start()
    provider = ProviderBuilder().node(node).build()
    account = NamedAccount.create("alice")
    node.fund_account(account)
    return Arkiv(provider, account=account), node


def main() -> None:
    client, node = build_client()

    try:
        # ── Basic chain info ────────────────────────────────────────────────
        block_number = client.eth.block_number
        chain_id = client.eth.chain_id
        account_address = client.eth.default_account
        logger.info("Connected — block=%d chain_id=%d account=%s", block_number, chain_id, account_address)

        # ── Subscribe to creation events ────────────────────────────────────
        received_events: list[tuple[CreateEvent, TxHash]] = []

        def on_entity_created(event: CreateEvent, tx_hash: TxHash) -> None:
            logger.info(
                "Event: EntityCreated key=%s owner=%s expiresAt=%d tx=%s",
                event.key,
                event.owner_address,
                event.expiration_block,
                tx_hash,
            )
            received_events.append((event, tx_hash))

        event_filter = client.arkiv.watch_entity_created(on_entity_created)
        logger.info("Subscribed to EntityCreated events")

        # ── Create an entity ────────────────────────────────────────────────
        data = {"message": "Hello from Python!", "value": 42}
        entity_key, receipt = client.arkiv.create_entity(
            payload=json.dumps(data).encode(),
            content_type="application/json",
            attributes=Attributes({"test": "hello", "test2": 23}),
            expires_in=3600,
        )
        logger.info("Created entity key=%s block=%d tx=%s", entity_key, receipt.block_number, receipt.tx_hash)

        # ── Get entity by key ───────────────────────────────────────────────
        entity = client.arkiv.get_entity(entity_key)
        payload_text = entity.payload.decode("utf-8") if entity.payload else ""
        payload_json = json.loads(payload_text) if payload_text else {}
        logger.info("Fetched entity: owner=%s expires_at=%s", entity.owner, entity.expires_at_block)
        logger.info("  payload  : %s", payload_json)
        logger.info("  attributes: %s", entity.attributes)

        # ── Query entities ──────────────────────────────────────────────────
        query = f'$attributes.test2 = 22 AND $owner = "{account_address}"'
        page = client.arkiv.query_entities_page(
            query,
            QueryOptions(attributes=KEY | PAYLOAD | ATTRIBUTES | OWNER),
        )
        logger.info("Query returned %d result(s) at block %d", len(page), page.block_number)
        for e in page:
            logger.info("  key=%s payload=%s", e.key, e.payload)

        # ── Count via select() fluent API ───────────────────────────────────
        results = list(
            client.arkiv.select(KEY, ATTRIBUTES)
            .where(f'test2 = 22 AND $owner = "{account_address}"')
            .fetch()
        )
        logger.info("Fluent query: %d matching entit(y/ies)", len(results))

        # ── Update the entity ───────────────────────────────────────────────
        updated_data = {**data, "updated": True}
        receipt_update = client.arkiv.update_entity(
            entity_key,
            payload=json.dumps(updated_data).encode(),
            content_type="application/json",
            attributes=Attributes({"test": "hello", "test2": 23, "version": 2}),
            expires_in=3600,
        )
        logger.info("Updated entity tx=%s", receipt_update.tx_hash)

        # ── Extend lifetime ─────────────────────────────────────────────────
        receipt_extend = client.arkiv.extend_entity(entity_key, extend_by=1800)
        logger.info("Extended entity tx=%s", receipt_extend.tx_hash)

        # ── Wait briefly for event callback ─────────────────────────────────
        time.sleep(3)
        logger.info("%d creation event(s) received via subscription", len(received_events))

        # ── Unsubscribe ──────────────────────────────────────────────────────
        event_filter.uninstall()
        logger.info("Unsubscribed from EntityCreated events")

        # ── Delete the entity ────────────────────────────────────────────────
        receipt_delete = client.arkiv.delete_entity(entity_key)
        logger.info("Deleted entity tx=%s", receipt_delete.tx_hash)

        exists = client.arkiv.entity_exists(entity_key)
        logger.info("Entity still exists after delete: %s", exists)

    finally:
        if node and not node.is_external:
            node.stop()
            logger.info("Node stopped")


if __name__ == "__main__":
    main()
