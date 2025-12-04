# Arkiv SDK Roadmap

Planned and proposed features for the Arkiv SDK.

## Creation Flags

Entities should support creation-time flags with meaningful defaults.
Flags can only be set at creation and define entity behavior:

- **Read-only**: Once created, entity data cannot be changed by anyone (immutable)
- **Unpermissioned extension**: Entity lifetime can be extended by anyone, not just the owner

```python
# Proposed API
client.arkiv.create_entity(
    payload=b"data",
    attributes={"type": "public"},
    expires_at_block=future_block,
    flags=EntityFlags.READ_ONLY | EntityFlags.PUBLIC_EXTENSION
)
```

## ETH Transfers

Arkiv chains should support ETH (or native token like GLM) transfers for gas fees and value transfer.

```python
# Already supported via Web3.py compatibility
tx_hash = client.eth.send_transaction({
    'to': recipient_address,
    'value': client.to_wei(1, 'ether'),
    'gas': 21000
})
```

## Offline Entity Verification

Provide cryptographic verification of entity data without querying the chain.

- Currently not supported
- Proposal: Store entity keys (and block number) in smart contracts and work with an optimistic oracle approach (challenger may take entity key and checks claimed data against the data of an Arkiv archival node)
