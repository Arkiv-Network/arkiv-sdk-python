"""Arkiv Python SDK."""

import asyncio
import base64
import logging
import logging.config
import typing
from collections.abc import (
    AsyncGenerator,
    Callable,
    Coroutine,
    Sequence,
)
from typing import (
    Any,
    cast,
)

from eth_typing import ChecksumAddress, HexStr
from web3 import AsyncWeb3, WebSocketProvider
from web3.contract import AsyncContract
from web3.exceptions import ProviderConnectionError, Web3RPCError
from web3.method import Method, default_root_munger
from web3.middleware import SignAndSendRawMiddlewareBuilder
from web3.types import LogReceipt, RPCEndpoint, TxParams, TxReceipt, Wei
from web3.utils.subscriptions import (
    LogsSubscription,
    LogsSubscriptionContext,
)

from .constants import (
    ARKIV_ABI,
    STORAGE_ADDRESS,
)
from .types import (
    Address,
    Annotation,
    ArkivCreate,
    ArkivDelete,
    ArkivExtend,
    ArkivTransaction,
    ArkivTransactionReceipt,
    ArkivUpdate,
    CreateEntityReturnType,
    EntityKey,
    EntityMetadata,
    ExtendEntityReturnType,
    GenericBytes,
    QueryEntitiesResult,
    UpdateEntityReturnType,
    WatchLogsHandle,
)
from .utils import rlp_encode_transaction
from .wallet import (
    WalletError,
    decrypt_wallet,
)

__all__: Sequence[str] = [
    # Exports from .types
    "Address",
    "Annotation",
    "CreateEntityReturnType",
    "EntityKey",
    "EntityMetadata",
    "ExtendEntityReturnType",
    "GenericBytes",
    "ArkivCreate",
    "ArkivDelete",
    "ArkivExtend",
    "ArkivTransaction",
    "ArkivTransactionReceipt",
    "ArkivUpdate",
    "QueryEntitiesResult",
    "UpdateEntityReturnType",
    "WatchLogsHandle",
    # Exports from .constants
    "ARKIV_ABI",
    "STORAGE_ADDRESS",
    # Exports from .wallet
    "decrypt_wallet",
    "WalletError",
    # Exports from this file
    "ArkivClient",
    # Re-exports
    "Wei",
]


logger = logging.getLogger(__name__)
"""@private"""


class ArkivHttpClient(AsyncWeb3):
    """Subclass of AsyncWeb3 with added Arkiv methods."""

    def __init__(self, rpc_url: str):
        super().__init__(
            AsyncWeb3.AsyncHTTPProvider(rpc_url, request_kwargs={"timeout": 60})
        )

        self.eth.attach_methods(
            {
                "get_storage_value": Method(
                    json_rpc_method=RPCEndpoint("golembase_getStorageValue"),
                    mungers=[default_root_munger],
                ),
                "get_entity_metadata": Method(
                    json_rpc_method=RPCEndpoint("golembase_getEntityMetaData"),
                    mungers=[default_root_munger],
                ),
                "get_entities_to_expire_at_block": Method(
                    json_rpc_method=RPCEndpoint("golembase_getEntitiesToExpireAtBlock"),
                    mungers=[default_root_munger],
                ),
                "get_entity_count": Method(
                    json_rpc_method=RPCEndpoint("golembase_getEntityCount"),
                    mungers=[default_root_munger],
                ),
                "get_all_entity_keys": Method(
                    json_rpc_method=RPCEndpoint("golembase_getAllEntityKeys"),
                    mungers=[default_root_munger],
                ),
                "get_entities_of_owner": Method(
                    json_rpc_method=RPCEndpoint("golembase_getEntitiesOfOwner"),
                    mungers=[default_root_munger],
                ),
                "query_entities": Method(
                    json_rpc_method=RPCEndpoint("golembase_queryEntities"),
                    mungers=[default_root_munger],
                ),
            }
        )

    async def get_storage_value(self, entity_key: EntityKey) -> bytes:
        """Get the storage value stored in the given entity."""
        return base64.b64decode(
            await self.eth.get_storage_value(  # type: ignore[attr-defined]
                entity_key.as_hex_string()
            )
        )

    async def get_entity_metadata(self, entity_key: EntityKey) -> EntityMetadata:
        """Get the metadata of the given entity."""
        metadata = await self.eth.get_entity_metadata(  # type: ignore[attr-defined]
            entity_key.as_hex_string()
        )

        return EntityMetadata(
            entity_key=entity_key,
            owner=Address(GenericBytes.from_hex_string(metadata.owner)),
            expires_at_block=metadata.expiresAtBlock,
            string_annotations=list(
                map(
                    lambda ann: Annotation(key=ann["key"], value=ann["value"]),
                    metadata.stringAnnotations,
                )
            ),
            numeric_annotations=list(
                map(
                    lambda ann: Annotation(key=ann["key"], value=ann["value"]),
                    metadata.numericAnnotations,
                )
            ),
        )

    async def get_entities_to_expire_at_block(
        self, block_number: int
    ) -> Sequence[EntityKey]:
        """Get all entities that will expire at the given block."""
        return list(
            map(
                lambda e: EntityKey(GenericBytes.from_hex_string(e)),
                await self.eth.get_entities_to_expire_at_block(  # type: ignore[attr-defined]
                    block_number
                ),
            )
        )

    async def get_entity_count(self) -> int:
        """Get the total entity count in Arkiv."""
        return cast(int, await self.eth.get_entity_count())  # type: ignore[attr-defined]

    async def get_all_entity_keys(self) -> Sequence[EntityKey]:
        """Get all entity keys in Arkiv."""
        return list(
            map(
                lambda e: EntityKey(GenericBytes.from_hex_string(e)),
                await self.eth.get_all_entity_keys(),  # type: ignore[attr-defined]
            )
        )

    async def get_entities_of_owner(
        self, owner: ChecksumAddress
    ) -> Sequence[EntityKey]:
        """Get all the entities owned by the given address."""
        return list(
            map(
                lambda e: EntityKey(GenericBytes.from_hex_string(e)),
                await self.eth.get_entities_of_owner(owner),  # type: ignore[attr-defined]
            )
        )

    async def query_entities(self, query: str) -> Sequence[QueryEntitiesResult]:
        """Get all entities that satisfy the given Arkiv query."""
        return list(
            map(
                lambda result: QueryEntitiesResult(
                    entity_key=result.key, storage_value=base64.b64decode(result.value)
                ),
                await self.eth.query_entities(query),  # type: ignore[attr-defined]
            )
        )


class ArkivROClient:
    _http_client: ArkivHttpClient
    _ws_client: AsyncWeb3
    _arkiv_contract: AsyncContract
    _background_tasks: set[asyncio.Task[None]]

    @staticmethod
    async def create_ro_client(rpc_url: str, ws_url: str) -> "ArkivROClient":
        """
        Create an `ArkivClient` instance.

        This is the preferred method to create an instance.
        """
        return ArkivROClient(rpc_url, await ArkivROClient._create_ws_client(ws_url))

    @staticmethod
    async def _create_ws_client(ws_url: str) -> "AsyncWeb3":
        ws_client: AsyncWeb3 = await AsyncWeb3(WebSocketProvider(ws_url))
        return ws_client

    def __init__(self, rpc_url: str, ws_client: AsyncWeb3) -> None:
        """Initialise the ArkivClient instance."""
        self._http_client = ArkivHttpClient(rpc_url)
        self._ws_client = ws_client

        # Keep references to async tasks we created
        self._background_tasks = set()

        def is_connected(
            client: AsyncWeb3,
        ) -> Callable[[bool], Coroutine[Any, Any, bool]]:
            async def inner(show_traceback: bool) -> bool:
                try:
                    logger.debug("Calling eth_blockNumber to test connectivity...")
                    await client.eth.get_block_number()
                    return True
                except (OSError, ProviderConnectionError) as e:
                    logger.debug(
                        "Problem connecting to provider", exc_info=show_traceback
                    )
                    if show_traceback:
                        raise ProviderConnectionError(
                            "Problem connecting to provider"
                        ) from e
                    return False

            return inner

        # The default is_connected method calls web3_clientVersion, but the web3
        # API is not enabled on all our nodes, so let's monkey patch this to call
        # eth_getBlockNumber instead.
        # The method on the provider is usually not called directly, instead you
        # can call the eponymous method on the client, which will delegate to the
        # provider.
        object.__setattr__(
            self.http_client().provider,
            "is_connected",
            is_connected(self.http_client()),
        )

        # Allow caching of certain methods to improve performance
        self.http_client().provider.cache_allowed_requests = True

        # https://github.com/pylint-dev/pylint/issues/3162
        # pylint: disable=no-member
        self.arkiv_contract = self.http_client().eth.contract(
            address=STORAGE_ADDRESS.as_address(),
            abi=ARKIV_ABI,
        )
        for event in self.arkiv_contract.all_events():
            logger.debug(
                "Registered event %s with hash %s", event.signature, event.topic
            )

    def http_client(self) -> ArkivHttpClient:
        """Get the underlying web3 http client."""
        return self._http_client

    def ws_client(self) -> AsyncWeb3:
        """Get the underlying web3 websocket client."""
        return self._ws_client

    async def is_connected(self) -> bool:
        """Check whether the client's underlying http client is connected."""
        return cast(bool, await self.http_client().is_connected())  # type: ignore[redundant-cast]

    async def disconnect(self) -> None:
        """
        Disconnect this client.

        this method disconnects both the underlying http and ws clients and
        unsubscribes from all subscriptions.
        """
        await self.http_client().provider.disconnect()
        await self.ws_client().subscription_manager.unsubscribe_all()
        await self.ws_client().provider.disconnect()

    async def get_storage_value(self, entity_key: EntityKey) -> bytes:
        """Get the storage value stored in the given entity."""
        return await self.http_client().get_storage_value(entity_key)

    async def get_entity_metadata(self, entity_key: EntityKey) -> EntityMetadata:
        """Get the metadata of the given entity."""
        return await self.http_client().get_entity_metadata(entity_key)

    async def get_entities_to_expire_at_block(
        self, block_number: int
    ) -> Sequence[EntityKey]:
        """Get all entities that will expire at the given block."""
        return await self.http_client().get_entities_to_expire_at_block(block_number)

    async def get_entity_count(self) -> int:
        """Get the total entity count in Arkiv."""
        return await self.http_client().get_entity_count()

    async def get_all_entity_keys(self) -> Sequence[EntityKey]:
        """Get all entity keys in Arkiv."""
        return await self.http_client().get_all_entity_keys()

    async def get_entities_of_owner(
        self, owner: ChecksumAddress
    ) -> Sequence[EntityKey]:
        """Get all the entities owned by the given address."""
        return await self.http_client().get_entities_of_owner(owner)

    async def query_entities(self, query: str) -> Sequence[QueryEntitiesResult]:
        """Get all entities that satisfy the given Arkiv query."""
        return await self.http_client().query_entities(query)

    async def watch_logs(
        self,
        *,
        label: str,
        create_callback: Callable[[CreateEntityReturnType], None] | None = None,
        update_callback: Callable[[UpdateEntityReturnType], None] | None = None,
        delete_callback: Callable[[EntityKey], None] | None = None,
        extend_callback: Callable[[ExtendEntityReturnType], None] | None = None,
    ) -> WatchLogsHandle:
        """
        Subscribe to events on Arkiv.

        You can pass in four different callbacks, and the right one will
        be invoked for every create, update, delete, and extend operation.
        """

        async def log_handler(
            handler_context: LogsSubscriptionContext,
        ) -> None:
            # We only use this handler for log receipts
            # TypeDicts cannot be checked at runtime
            log_receipt = typing.cast(LogReceipt, handler_context.result)
            logger.debug("New log: %s", log_receipt)
            res = await self._process_arkiv_log_receipt(log_receipt)

            if create_callback:
                for create in res.creates:
                    create_callback(create)
            if update_callback:
                for update in res.updates:
                    update_callback(update)
            if delete_callback:
                for key in res.deletes:
                    delete_callback(key)
            if extend_callback:
                for extension in res.extensions:
                    extend_callback(extension)

        def create_subscription(topic: HexStr) -> LogsSubscription:
            return LogsSubscription(
                label=f"Arkiv subscription to topic {topic} with label {label}",
                address=self.arkiv_contract.address,
                topics=[topic],
                handler=log_handler,
                # optional `handler_context` args to help parse a response
                handler_context={},
            )

        event_names = []
        if create_callback:
            event_names.append("GolemBaseStorageEntityCreated")
        if update_callback:
            event_names.append("GolemBaseStorageEntityUpdated")
        if delete_callback:
            event_names.append("GolemBaseStorageEntityDeleted")
        if extend_callback:
            event_names.append("GolemBaseStorageEntityBTLExtended")

        events = list(
            map(
                lambda event_name: create_subscription(
                    self.arkiv_contract.get_event_by_name(event_name).topic
                ),
                event_names,
            )
        )
        subscription_ids = await self._ws_client.subscription_manager.subscribe(
            events,
        )
        logger.info("Sub ID: %s", subscription_ids)

        # Start a subscription loop in case there is none running
        await self._start_subscription_loop()

        async def unsubscribe() -> None:
            await self._ws_client.subscription_manager.unsubscribe(subscription_ids)

        return WatchLogsHandle(_unsubscribe=unsubscribe)

    async def _start_subscription_loop(self) -> None:
        """Create a long running task to handle subscriptions."""
        # The loop will finish when there are no subscriptions left, so this method
        # gets called every time a subscription is created, and we'll check
        # whether we need to make a new task or whether one is already running.
        if not self._background_tasks:
            # Start the asyncio event loop
            task = asyncio.create_task(
                self.ws_client().subscription_manager.handle_subscriptions()
            )
            self._background_tasks.add(task)

            def task_done(task: asyncio.Task[None]) -> None:
                logger.info("Subscription background task done, removing...")
                self._background_tasks.discard(task)

            task.add_done_callback(task_done)

    async def _process_arkiv_log_receipt(
        self,
        log_receipt: LogReceipt,
    ) -> ArkivTransactionReceipt:
        # Read the first entry of the topics array,
        # which is the hash of the event signature, identifying the event
        topic = AsyncWeb3.to_hex(log_receipt["topics"][0])
        # Look up the corresponding event
        # If there is no such event in the ABI, it probably needs to be added
        event = self.arkiv_contract.get_event_by_topic(topic)
        # Use the event to process the whole log
        event_data = event.process_log(log_receipt)

        creates: list[CreateEntityReturnType] = []
        updates: list[UpdateEntityReturnType] = []
        deletes: list[EntityKey] = []
        extensions: list[ExtendEntityReturnType] = []

        match event_data["event"]:
            case "GolemBaseStorageEntityCreated":
                creates.append(
                    CreateEntityReturnType(
                        expiration_block=event_data["args"]["expirationBlock"],
                        entity_key=EntityKey(
                            GenericBytes(
                                event_data["args"]["entityKey"].to_bytes(32, "big")
                            )
                        ),
                    )
                )
            case "GolemBaseStorageEntityUpdated":
                updates.append(
                    UpdateEntityReturnType(
                        expiration_block=event_data["args"]["expirationBlock"],
                        entity_key=EntityKey(
                            GenericBytes(
                                event_data["args"]["entityKey"].to_bytes(32, "big")
                            )
                        ),
                    )
                )
            case "GolemBaseStorageEntityDeleted":
                deletes.append(
                    EntityKey(
                        GenericBytes(
                            event_data["args"]["entityKey"].to_bytes(32, "big")
                        ),
                    )
                )
            case "GolemBaseStorageEntityBTLExtended":
                extensions.append(
                    ExtendEntityReturnType(
                        old_expiration_block=event_data["args"]["oldExpirationBlock"],
                        new_expiration_block=event_data["args"]["newExpirationBlock"],
                        entity_key=EntityKey(
                            GenericBytes(
                                event_data["args"]["entityKey"].to_bytes(32, "big")
                            )
                        ),
                    )
                )

        return ArkivTransactionReceipt(
            creates=creates,
            updates=updates,
            deletes=deletes,
            extensions=extensions,
        )

    async def _process_arkiv_receipt(
        self, receipt: TxReceipt
    ) -> ArkivTransactionReceipt:
        # There doesn't seem to be a method for this in the web3 lib.
        # The only option in the lib is to iterate over the events in the ABI
        # and call process_receipt on each of them to try and decode the logs.
        # This is inefficient though compared to reading the actual topic signature
        # and immediately selecting the right event from the ABI, which is what
        # we do here.
        async def process_receipt(
            receipt: TxReceipt,
        ) -> AsyncGenerator[ArkivTransactionReceipt, None]:
            for log in receipt["logs"]:
                yield await self._process_arkiv_log_receipt(log)

        creates: list[CreateEntityReturnType] = []
        updates: list[UpdateEntityReturnType] = []
        deletes: list[EntityKey] = []
        extensions: list[ExtendEntityReturnType] = []

        async for res in process_receipt(receipt):
            creates.extend(res.creates)
            updates.extend(res.updates)
            deletes.extend(res.deletes)
            extensions.extend(res.extensions)

        return ArkivTransactionReceipt(
            creates=creates,
            updates=updates,
            deletes=deletes,
            extensions=extensions,
        )


class ArkivClient(ArkivROClient):
    """
    The Arkiv client used to interact with Arkiv.

    Many useful methods are implemented directly on this type, while more
    generic ethereum methods can be accessed through the underlying
    web3 client that you can access with the
    `ArkivClient.http_client()`
    method.
    """

    @staticmethod
    async def create_rw_client(
        rpc_url: str, ws_url: str, private_key: bytes
    ) -> "ArkivClient":
        """
        Create a read-write Arkiv client.

        This is the preferred method to create an instance.
        """
        return ArkivClient(
            rpc_url, await ArkivROClient._create_ws_client(ws_url), private_key
        )

    @staticmethod
    async def create(rpc_url: str, ws_url: str, private_key: bytes) -> "ArkivClient":
        """
        Create a read-write Arkiv client.

        This method is deprecated in favour of `ArkivClient.create_rw_client()`.
        """
        return await ArkivClient.create_rw_client(rpc_url, ws_url, private_key)

    def __init__(self, rpc_url: str, ws_client: AsyncWeb3, private_key: bytes) -> None:
        """Initialise the ArkivClient instance."""
        super().__init__(rpc_url, ws_client)

        # Set up the ethereum account
        self.account = self.http_client().eth.account.from_key(private_key)
        # Inject a middleware that will sign transactions with the account that
        # we created
        self.http_client().middleware_onion.inject(
            # pylint doesn't detect nested @curry annotations properly...
            # pylint: disable=no-value-for-parameter
            SignAndSendRawMiddlewareBuilder.build(self.account),
            layer=0,
        )
        # Set the account as the default, so we don't need to specify the from field
        # every time
        self.http_client().eth.default_account = self.account.address
        logger.debug("Using account: %s", self.account.address)

    def get_account_address(self) -> ChecksumAddress:
        """Get the address associated with the private key of this client."""
        return cast(ChecksumAddress, self.account.address)

    async def create_entities(
        self,
        creates: Sequence[ArkivCreate],
        *,
        gas: int | None = None,
        maxFeePerGas: Wei | None = None,
        maxPriorityFeePerGas: Wei | None = None,
    ) -> Sequence[CreateEntityReturnType]:
        """Create entities in Arkiv."""
        return (
            await self.send_transaction(
                creates=creates,
                gas=gas,
                maxFeePerGas=maxFeePerGas,
                maxPriorityFeePerGas=maxPriorityFeePerGas,
            )
        ).creates

    async def update_entities(
        self,
        updates: Sequence[ArkivUpdate],
        *,
        gas: int | None = None,
        maxFeePerGas: Wei | None = None,
        maxPriorityFeePerGas: Wei | None = None,
    ) -> Sequence[UpdateEntityReturnType]:
        """Update entities in Arkiv."""
        return (
            await self.send_transaction(
                updates=updates,
                gas=gas,
                maxFeePerGas=maxFeePerGas,
                maxPriorityFeePerGas=maxPriorityFeePerGas,
            )
        ).updates

    async def delete_entities(
        self,
        deletes: Sequence[ArkivDelete],
        *,
        gas: int | None = None,
        maxFeePerGas: Wei | None = None,
        maxPriorityFeePerGas: Wei | None = None,
    ) -> Sequence[EntityKey]:
        """Delete entities from Arkiv."""
        return (
            await self.send_transaction(
                deletes=deletes,
                gas=gas,
                maxFeePerGas=maxFeePerGas,
                maxPriorityFeePerGas=maxPriorityFeePerGas,
            )
        ).deletes

    async def extend_entities(
        self,
        extensions: Sequence[ArkivExtend],
        *,
        gas: int | None = None,
        maxFeePerGas: Wei | None = None,
        maxPriorityFeePerGas: Wei | None = None,
    ) -> Sequence[ExtendEntityReturnType]:
        """Extend the BTL of entities in Arkiv."""
        return (
            await self.send_transaction(
                extensions=extensions,
                gas=gas,
                maxFeePerGas=maxFeePerGas,
                maxPriorityFeePerGas=maxPriorityFeePerGas,
            )
        ).extensions

    async def send_transaction(
        self,
        *,
        creates: Sequence[ArkivCreate] | None = None,
        updates: Sequence[ArkivUpdate] | None = None,
        deletes: Sequence[ArkivDelete] | None = None,
        extensions: Sequence[ArkivExtend] | None = None,
        gas: int | None = None,
        maxFeePerGas: Wei | None = None,
        maxPriorityFeePerGas: Wei | None = None,
    ) -> ArkivTransactionReceipt:
        """
        Send a generic transaction to Arkiv.

        This transaction can contain multiple create, update, delete and
        extend operations.
        """
        tx = ArkivTransaction(
            creates=creates,
            updates=updates,
            deletes=deletes,
            extensions=extensions,
            gas=gas,
            maxFeePerGas=maxFeePerGas,
            maxPriorityFeePerGas=maxPriorityFeePerGas,
        )
        return await self._send_arkiv_transaction(tx)

    async def _send_arkiv_transaction(
        self, tx: ArkivTransaction
    ) -> ArkivTransactionReceipt:
        txData: TxParams = {
            # https://github.com/pylint-dev/pylint/issues/3162
            # pylint: disable=no-member
            "to": STORAGE_ADDRESS.as_address(),
            "value": AsyncWeb3.to_wei(0, "ether"),
            "data": rlp_encode_transaction(tx),
        }

        if tx.gas:
            txData |= {"gas": tx.gas}
        if tx.maxFeePerGas:
            txData |= {"maxFeePerGas": tx.maxFeePerGas}
        if tx.maxPriorityFeePerGas:
            txData |= {"maxPriorityFeePerGas": tx.maxPriorityFeePerGas}

        txhash = await self.http_client().eth.send_transaction(txData)
        receipt = await self.http_client().eth.wait_for_transaction_receipt(txhash)

        # If we get a receipt and the transaction was failed, we run the same
        # transaction with eth_call, which will simulate it and get us back the
        # error that was reported by geth.
        # Otherwise the error is not actually present in the receipt and so we
        # don't have something useful to present to the user.
        # This only happens when the gas price was explicitly provided, since
        # otherwise there will be a call to eth_estimateGas, which will fail with
        # the same error message that we would get here (and so we'll never actually
        # get to submitting the transaction).
        # The status in the receipt is either 0x0 for failed or 0x1 for success.
        if not int(receipt["status"]):
            # This call will lead to an exception, but that's OK, what we want
            # is to raise a useful exception to the user with an error message.
            try:
                await self.http_client().eth.call(txData)
            except Web3RPCError as e:
                if e.rpc_response:
                    error = e.rpc_response["error"]["message"]
                    raise Exception(
                        f"Error while processing transaction: {error}"
                    ) from e
                else:
                    raise e

        return await self._process_arkiv_receipt(receipt)
