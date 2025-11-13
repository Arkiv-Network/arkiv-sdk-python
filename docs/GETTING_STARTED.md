# Arkiv SDK Python Snippets

## Hello World

```python
from arkiv import Arkiv
from arkiv.account import NamedAccount
from arkiv.provider import ProviderBuilder

PRIVATE_KEY = "0x14f33c0d791b9d5e9b7311b4b7eded64ddc308b2ac13c4d9e12534e9b49ac716"
RPC_URL = "https://mendoza.hoodi.arkiv.network/rpc"

provider = ProviderBuilder().custom(RPC_URL).build()
account = NamedAccount.from_private_key("demo", PRIVATE_KEY)

client = Arkiv(provider=provider, account=account)
client.eth.get_balance(account.address) / 10**18

entity_key, tx_receipt = client.arkiv.create_entity(payload=b"Hello, Arkiv!", content_type="text/plain", attributes = {"type": "greeting", "version": 1}, expires_in = client.arkiv.to_seconds(hours=1))

entity = client.arkiv.get_entity(entity_key)
print(entity)
```

## Open Proposal

```python
proposal_key, _ = client.arkiv.create_entity(
    payload = b"Proposal: Switch stand-up to 9:30?",
    content_type = "text/plain",
    attributes = {
        "type": "proposal",
        "status": "open",
        "version": 1,
    },
    expires_in = client.arkiv.to_seconds(days=3),
)

print("Proposal key:", proposal_key)
```

## Cast Votes

```python
voter = client.eth.default_account  # type: ignore

yes_vote_key, _ = client.arkiv.create_entity(
    payload=b"vote: yes",
    content_type="text/plain",
    attributes={
        "type": "vote",
        "proposalKey": proposal_key,
        "voter": voter,
        "choice": "yes",
        "weight": 1,
    },
    expires_in = client.arkiv.to_seconds(days=3),
)

print("Vote cast:", yes_vote_key)
```

## Batch Votes

```python
vote_prefix = str(client.eth.default_account)
creates: list[CreateOp] = []

for i in range(5):
    creates.append(CreateOp(
        payload=f"vote: yes #{i+1}".encode("utf-8"),
        content_type="text/plain",
        attributes={
            "type": "vote",
            "proposalKey": proposal_key,
            "voter": f"{vote_prefix}-bot{i}",
            "choice": "yes" if i == 2 else "no",
            "weight": 1,
        },
        expires_in = client.arkiv.to_seconds(days=3),
    ))

batch_receipt = client.arkiv.execute(Operations(creates=creates))
print(f"Batch created: {len(batch_receipt.creates)} votes; tx={batch_receipt.tx_hash}")
```

## Tally Votes

```python
query_yes = f'type = "vote" and proposalKey = "{proposal_key}" and choice = "yes"'
query_no  = f'type = "vote" and proposalKey = "{proposal_key}" and choice = "no"'

yes_votes = list(client.arkiv.query_entities(query_yes))
no_votes  = list(client.arkiv.query_entities(query_no))

print(f"Tallies - YES: {len(yes_votes)}, NO: {len(no_votes)}")
```

## Watch Live

```python
def on_created(event, tx_hash):
    try:
        ent = client.arkiv.get_entity(event.key)
        if ent.attributes and ent.attributes.get("type") in ("vote", "proposal"):
            if ent.attributes.get("type") == "vote":
                print(f"[Created] key={event.key} vote={ent.attributes.get('choice')} tx={tx_hash}")
            else:
                print(f"[Created] key={event.key} proposal={ent.payload} tx={tx_hash}")
    except Exception as e:
        print("[Created] error:", e)

def on_extended(event, tx_hash):
    try:
        print(f"[Extended] key={event.key} new_expiration_block={event.new_expiration_block} tx={tx_hash}")
    except Exception as e:
        print("[Extended] error:", e)

filter_created = client.arkiv.watch_entity_created(on_created, from_block="latest", auto_start=True)
filter_extended = client.arkiv.watch_entity_extended(on_extended, from_block="latest", auto_start=True)

# When done watching:
# client.arkiv.cleanup_filters()
```

## Watch Live

```python
receipt = client.arkiv.extend_entity(proposal_key, number_of_blocks=2000)
print("Proposal extension receipt:", receipt.extensions)
```
