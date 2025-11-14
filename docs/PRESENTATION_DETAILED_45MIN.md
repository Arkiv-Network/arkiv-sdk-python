# Arkiv SDK Deep Dive: Building Production-Ready Decentralized Applications
## 45-Minute Technical Workshop - Buenos Aires Hackathon

---

## Part 1: The Architecture (10 minutes)

### The Decentralized Data Trilemma

Traditional blockchain applications face a fundamental challenge:

```
            Web3
             /\
            /  \
           /    \
          /      \
         /        \
        /          \
       /   ARKIV    \
      /     ✓✓✓      \
     /________________\
Affordable          Queryable
```

**Without Arkiv**, you loose at least one:
- **Ethereum Storage**: Decentralized + Queryable, but $1000s per MB
- **Pure IPFS**: Decentralized + Affordable, but no queries
- **Web2 DB**: Affordable + Queryable, but centralized

**With Arkiv**: All three! 🎯

---

### How Arkiv Works: Under the Hood

#### 1. **Blockchain-Native Storage Layer**

Arkiv runs as a specialized blockchain network:
- EVM-compatible (works with existing Ethereum tools)
- Custom storage opcodes optimized for data operations
- Block time: ~2 seconds
- Native support for entity CRUD operations

#### 2. **Entity Model**

Each entity contains:

```python
Entity:
  - key: EntityKey           # Unique 256-bit identifier (auto-generated)
  - payload: bytes           # Binary data (up to MBs)
  - content_type: str        # MIME type (e.g., "application/json")
  - attributes: dict         # Queryable attrs, text and ints >= 0
  - owner: Address           # Ethereum address with control
  - expires_at: int          # Block number when entity expires
  - created_at: int          # Block number of creation
  - last_modified_at: int    # Block number of last update
```

#### 3. **Storage Economics**

- **Cost Model**: Pay for storage size and duration
- **Expiration**: Entities automatically expire after specified time
- **Extension**: Owners can extend lifetime before expiration
- **Deletion**: Manual deletion possible, may offer gas refunds

---

### Arkiv vs Alternatives: Technical Comparison


| Feature | **Arkiv** | Ethereum | IPFS | Web2 DB |
|---------|-----------|----------|------|---------|
| Web3 Data | ✅ | ✅ | ✅ | ❌ |
| Affordable | ✅ | ❌ | ✅ | ✅ |
| SQL-like Queries | ✅ | ❌ | ❌ | ✅ |
| Real-time Events | ✅ | ✅ | ❌ | ✅ |

---

## Part 2: SDK Architecture & Setup (10 minutes)

### Design Philosophy

**"Web3 Library + Entities"**

Python: Arkiv SDK is built on Web3.py with an "arkiv" extensino:

```python
from arkiv import Arkiv

client = Arkiv()

# Standard Web3.py functionality
account = client.eth.default_account
balance = client.eth.get_balance(address)
block = client.eth.get_block('latest')
tx = client.eth.send_transaction({...})

# + Arkiv entity functionality
entity_key, receipt = client.arkiv.create_entity(...)
entity = client.arkiv.get_entity(entity_key)
results = client.arkiv.query_entities(query)
```

---

### Installation & Environment Setup

#### Option 1: Quick Start (Local Development)
```bash
# Install SDK
pip install arkiv-sdk
pip install testcontainers, websockets

# Run with auto-managed local node (requires Docker)
from arkiv import Arkiv
client = Arkiv()  # Automatically starts containerized node + creates funded account
```

#### Option 2: Testnet Connection
```python
from arkiv import Arkiv
from arkiv.provider import ProviderBuilder
from arkiv.account import NamedAccount

MENDOZA_RPC = "https://mendoza.hoodi.arkiv.network/rpc"

# Load your account from wallet
with open('wallet.json', 'r') as f:
    wallet = f.read()
account = NamedAccount.from_wallet('alice', wallet, 'password')

# Load your account from private key
account = NamedAccount.from_private_key("alice", "0x...")

# Lock
# Connect to Kaolin testnet
provider = ProviderBuilder().custom(MENDOZA_RPC).build()
client = Arkiv(provider, account)
```

---

### Account Management

#### Creating Wallets
```bash
# Generate encrypted wallet file
uv run python -m arkiv.account alice
# Enter password when prompted
# Creates wallet_alice.json
```

#### Using Accounts in Code
```python
from arkiv.account import NamedAccount

# From wallet file
alice = NamedAccount.from_wallet('Alice', wallet_json, 'password')

# From private key
bob = NamedAccount.from_key('Bob', private_key)

# Use in client
client = Arkiv(provider, account=alice)
```

---

## Part 3: Core Entity Operations (10 minutes)

### Creating Entities

#### Basic Creation
```python
entity_key, receipt = client.arkiv.create_entity(
    payload = b"Hello, Arkiv!",
    content_type = "text/plain",
    attributes = {
        "type": "greeting",
        "language": "en",
        "version": 1
    },
    expires_in = client.arkiv.to_seconds(hours=24)
)

print(f"Entity created: {entity_key}")
print(f"Transaction: {receipt.tx_hash}")
print(f"Block: {receipt.block_number}")
```

#### Working with JSON Data
```python
import json

data = {
    "user_id": "alice",
    "profile": {
        "name": "Alice Smith",
        "bio": "Web3 developer"
    },
    "settings": {"theme": "dark"}
}

entity_key, _ = client.arkiv.create_entity(
    payload = json.dumps(data).encode(),
    content_type = "application/json",
    attributes = {
        "type": "user_profile",
        "user_id": "alice",
        "verified": 1  # Use 1 for true, 0 for false
    },
    expires_in = client.arkiv.to_seconds(days=30)  # 30 days
)
```

#### Binary Data (Images, Files)
```python
# Store an image
with open('avatar.png', 'rb') as f:
    image_data = f.read()

entity_key, _ = client.arkiv.create_entity(
    payload = image_data,
    content_type = "image/png",
    attributes={
        "type": "avatar",
        "user": "alice",
        "size": len(image_data)
    },
    expires_in = client.arkiv.to_seconds(days=365)  # 1 year
)
```

---

### Reading Entities

#### Get by Key
```python
# Fetch entire entity
entity = client.arkiv.get_entity(entity_key)
print(entity.payload)
print(entity.attributes)
print(entity.owner)
print(entity.expires_at_block)
```

#### Selective Field Loading
```python
from arkiv.types import KEY, PAYLOAD, ATTRIBUTES, OWNER, EXPIRATION

# Load only what you need (improves performance)
entity = client.arkiv.get_entity(
    entity_key,
    fields=PAYLOAD | ATTRIBUTES  # Only fetch payload and attributes
)
```

#### Check Existence
```python
if client.arkiv.entity_exists(entity_key):
    entity = client.arkiv.get_entity(entity_key)
else:
    print("Entity not found or expired")
```

---

### Updating Entities

```python
# Update replaces all data (not a merge!)
receipt = client.arkiv.update_entity(
    entity_key,
    payload=b"Updated content",
    content_type = "text/plain",
    attributes={
        "type": "greeting",
        "language": "en",
        "version": 2,  # Incremented version
        "updated": 1
    },
    expires_in=client.arkiv.to_seconds(days=7)
)

print(f"Updated at block: {receipt.block_number}")
```

**Important**: Updates are full replacements, not merges. If you need to preserve existing attributes, fetch them first:

```python
# Pattern: Read-Modify-Write
entity = client.arkiv.get_entity(entity_key)
current_attrs = entity.attributes

# Modify
current_attrs["status"] = "updated"
current_attrs["version"] = current_attrs.get("version", 0) + 1

# Write back
client.arkiv.update_entity(
    entity_key,
    payload=entity.payload,
    attributes=current_attrs,
    expires_in=client.arkiv.to_seconds(days=7)
)
```

---

### Ownership & Lifecycle

#### Transfer Ownership
```python
# Transfer entity to another address
new_owner = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"

receipt = client.arkiv.change_owner(
    entity_key,
    new_owner
)

# Only the new owner can now modify/delete the entity
```

#### Extend Lifetime
```python
# Extend by number of blocks
receipt = client.arkiv.extend_entity(
    entity_key,
    number_of_blocks=43200  # ~1 day with 2-second blocks
)

# Or calculate blocks from time duration
blocks = client.arkiv.to_blocks(days=7)
receipt = client.arkiv.extend_entity(entity_key, blocks)
```

#### Delete Entity
```python
# Permanent deletion (only by owner)
receipt = client.arkiv.delete_entity(entity_key)

# Entity no longer exists
exists = client.arkiv.entity_exists(entity_key)  # False
```

---

### Batch Operations

Process multiple entities in a single transaction:

```python
from arkiv.types import Operations, CreateOp, UpdateOp, DeleteOp

operations = Operations(
    creates=[
        CreateOp(
            payload=b"Entity 1",
            attributes={"type": "test", "id": 1},
            expires_in=1000
        ),
        CreateOp(
            payload=b"Entity 2",
            attributes={"type": "test", "id": 2},
            expires_in=1000
        )
    ],
    updates=[
        UpdateOp(
            entity_key=existing_key,
            payload=b"Updated",
            attributes={"status": "modified"},
            expires_in=1000
        )
    ],
    deletes=[DeleteOp(entity_key=old_key)]
)

receipt = client.arkiv.execute(operations)

# Receipt contains all events
print(f"Created: {len(receipt.creates)}")
print(f"Updated: {len(receipt.updates)}")
print(f"Deleted: {len(receipt.deletes)}")

# Access created entity keys
for create_event in receipt.creates:
    print(f"New entity: {create_event.key}")
```

---

## Part 4: Querying & Filtering (8 minutes)

### Query Language Basics

Arkiv uses SQL-like syntax for filtering entities:

```python
# Basic equality
query = 'type = "user"'
entities = list(client.arkiv.query_entities(query))

# Multiple conditions
query = 'type = "user" AND status = "active"'

# Numeric comparisons
query = 'type = "user" AND age >= 18 AND age < 65'

# OR conditions
query = 'type = "user" AND (status = "active" OR status = "premium")'

# NOT conditions
query = 'type = "user" AND status != "deleted"'
query = 'type = "user" AND NOT (status = "deleted")'  # Alternative

# Pattern matching (GLOB)
query = 'name GLOB "John*"'  # Starts with "John"
query = 'email GLOB "*@example.com"'  # Ends with "@example.com"
```

---

### Query Options

```python
from arkiv.types import QueryOptions, KEY, PAYLOAD, ATTRIBUTES

options = QueryOptions(
    fields=PAYLOAD | ATTRIBUTES,  # Which fields to fetch
    max_results_per_page=100,     # Pagination size
    at_block=None                 # Query at specific block (None = latest)
)

# Query with options
entities = list(client.arkiv.query_entities(
    'type = "user" AND age >= 18',
    options=options
))
```

---

### Sorting Results

#### Single-Field Sorting
```python
from arkiv.types import OrderByAttribute, STR, INT, ASC, DESC

# Sort by string attribute (ascending)
order_by = [OrderByAttribute(attribute="name", type=STR, direction=ASC)]
options = QueryOptions(order_by=order_by)

entities = list(client.arkiv.query_entities('type = "user"', options=options))

# Sort by numeric attribute (descending)
order_by = [OrderByAttribute(attribute="age", type=INT, direction=DESC)]
options = QueryOptions(order_by=order_by)
```

#### Multi-Field Sorting
```python
# Sort by status (asc), then by age (desc), then by name (asc)
order_by = [
    OrderByAttribute(attribute="status", type=STR, direction=ASC),
    OrderByAttribute(attribute="age", type=INT, direction=DESC),
    OrderByAttribute(attribute="name", type=STR, direction=ASC)
]

options = QueryOptions(order_by=order_by)
entities = list(client.arkiv.query_entities('type = "user"', options=options))
```

---

### Pagination & Iteration

The SDK automatically handles pagination:

```python
# Iterate over all results (automatic pagination)
query = 'type = "post" AND status = "published"'

for entity in client.arkiv.query_entities(query):
    # Process each entity
    # SDK automatically fetches next pages as needed
    process_post(entity)

# Or collect all at once
all_entities = list(client.arkiv.query_entities(query))
```

With custom page size:
```python
options = QueryOptions(max_results_per_page=50)

for entity in client.arkiv.query_entities(query, options=options):
    # Processes in batches of 50
    pass
```

---

### Complex Query Examples

#### Social Network: Find Friends
```python
# Find all active users aged 25-35 in Buenos Aires
query = '''
    type = "user"
    AND status = "active"
    AND age >= 25
    AND age <= 35
    AND city = "Buenos Aires"
'''

options = QueryOptions(
    fields=KEY | ATTRIBUTES,
    order_by=[OrderByAttribute("name", STR, ASC)]
)

users = list(client.arkiv.query_entities(query, options=options))
```

#### NFT Marketplace: Filter Listings
```python
# Find affordable NFTs from specific collection
query = '''
    type = "nft_listing"
    AND collection = "CoolApes"
    AND price >= 100
    AND price <= 1000
    AND status = "active"
'''

options = QueryOptions(
    order_by=[OrderByAttribute("price", INT, ASC)]
)

listings = list(client.arkiv.query_entities(query, options=options))
```

#### Gaming: Leaderboard
```python
# Top 10 players by score
query = 'type = "player" AND status = "active"'

options = QueryOptions(
    max_results_per_page=10,
    order_by=[OrderByAttribute("score", INT, DESC)]
)

top_players = list(client.arkiv.query_entities(query, options=options))
```

---

## Part 5: Real-Time Events (5 minutes)

### Event Watching Basics

Monitor entity lifecycle changes in real-time:

```python
def on_entity_created(event, tx_hash):
    print(f"New entity created: {event.key}")
    print(f"Owner: {event.owner}")
    print(f"Expiration: {event.expiration}")
    print(f"Transaction: {tx_hash}")

# Start watching
filter = client.arkiv.watch_entity_created(on_entity_created)

# Events are triggered automatically as they occur
# ... your app runs ...

# Stop watching
filter.stop()
filter.uninstall()
```

---

### All Event Types

```python
# Creation events
created_filter = client.arkiv.watch_entity_created(on_created)

# Update events
updated_filter = client.arkiv.watch_entity_updated(on_updated)

# Deletion events
deleted_filter = client.arkiv.watch_entity_deleted(on_deleted)

# Lifetime extension events
extended_filter = client.arkiv.watch_entity_extended(on_extended)

# Ownership change events
owner_changed_filter = client.arkiv.watch_owner_changed(on_owner_changed)
```

---

### Historical Events

```python
# Watch from specific block
filter = client.arkiv.watch_entity_created(
    on_entity_created,
    from_block=1000  # Start from block 1000
)

# Watch from beginning of chain
filter = client.arkiv.watch_entity_created(
    on_entity_created,
    from_block=0
)
```

---

### Automatic Cleanup

```python
# Context manager handles cleanup automatically
with Arkiv() as client:
    filter1 = client.arkiv.watch_entity_created(callback1)
    filter2 = client.arkiv.watch_entity_updated(callback2)

    # Do work...
    # Filters automatically stopped and uninstalled on exit

# Manual cleanup of all filters
client.arkiv.cleanup_filters()
```

---

### Real-World Event Example: Live Feed

```python
import json

def on_new_post(event, tx_hash):
    # Fetch the full entity
    entity = client.arkiv.get_entity(event.key)

    # Parse payload
    post_data = json.loads(entity.payload)

    # Display in feed
    print(f"@{post_data['author']}: {post_data['content']}")
    print(f"  Posted at block {event.expiration - 43200}")  # 1 day TTL

    # Store locally, update UI, send notifications, etc.
    update_ui_feed(entity)

# Start live feed
feed_filter = client.arkiv.watch_entity_created(on_new_post)

# App continues running, displaying new posts in real-time
```

---

## Part 6: Advanced Patterns & Best Practices (7 minutes)

### Time & Block Conversions

Arkiv provides utility methods for time calculations:

```python
# Convert time to seconds
expires_in = client.arkiv.to_seconds(
    days=7,
    hours=12,
    minutes=30,
    seconds=0
)

# Convert time to blocks (for extend_entity)
blocks = client.arkiv.to_blocks(
    days=1,
    hours=6
)

# Create entity with 30-day lifetime
entity_key, _ = client.arkiv.create_entity(
    payload=data,
    attributes=attrs,
    expires_in=client.arkiv.to_seconds(days=30)
)

# Extend by 1 week
client.arkiv.extend_entity(
    entity_key,
    client.arkiv.to_blocks(days=7)
)
```

---

### Entity Versioning Pattern

Implement versioning for update tracking:

```python
def create_versioned_entity(client, payload, attrs):
    """Create entity with version tracking."""
    attrs["version"] = 1
    attrs["created_timestamp"] = int(time.time())

    return client.arkiv.create_entity(
        payload=payload,
        attributes=attrs,
        expires_in=client.arkiv.to_seconds(days=30)
    )

def update_versioned_entity(client, entity_key, new_payload, new_attrs):
    """Update entity and increment version."""
    # Fetch current
    entity = client.arkiv.get_entity(entity_key)

    # Increment version
    new_attrs["version"] = entity.attributes.get("version", 0) + 1
    new_attrs["updated_timestamp"] = int(time.time())

    # Preserve creation timestamp
    new_attrs["created_timestamp"] = entity.attributes.get("created_timestamp")

    return client.arkiv.update_entity(
        entity_key,
        payload=new_payload,
        attributes=new_attrs,
        expires_in=client.arkiv.to_seconds(days=30)
    )
```

---

### Soft Delete Pattern

Implement soft deletes instead of hard deletion:

```python
def soft_delete_entity(client, entity_key):
    """Mark entity as deleted without actually deleting."""
    entity = client.arkiv.get_entity(entity_key)

    # Update with deleted flag
    entity.attributes["deleted"] = 1
    entity.attributes["deleted_at"] = int(time.time())

    return client.arkiv.update_entity(
        entity_key,
        payload=entity.payload,
        attributes=entity.attributes,
        expires_in=client.arkiv.to_seconds(days=7)  # Expire sooner
    )

# Query active entities only
active_entities = list(client.arkiv.query_entities(
    'type = "post" AND deleted != 1'
))
```

---

### Caching Strategy

Cache frequently accessed entities:

```python
from functools import lru_cache
import time

class EntityCache:
    def __init__(self, client, ttl=60):
        self.client = client
        self.ttl = ttl
        self.cache = {}

    def get(self, entity_key):
        """Get entity with caching."""
        now = time.time()

        # Check cache
        if entity_key in self.cache:
            entity, timestamp = self.cache[entity_key]
            if now - timestamp < self.ttl:
                return entity

        # Fetch and cache
        entity = self.client.arkiv.get_entity(entity_key)
        self.cache[entity_key] = (entity, now)
        return entity

    def invalidate(self, entity_key):
        """Invalidate cache entry."""
        if entity_key in self.cache:
            del self.cache[entity_key]

# Usage
cache = EntityCache(client, ttl=60)

entity = cache.get(entity_key)  # Fetches from Arkiv
entity = cache.get(entity_key)  # Returns cached (within 60s)

# After update
client.arkiv.update_entity(entity_key, ...)
cache.invalidate(entity_key)  # Clear cache
```

---

### Error Handling

```python
from arkiv.exceptions import EntityKeyException, AttributeException

try:
    entity = client.arkiv.get_entity(entity_key)
except ValueError as e:
    if "not found" in str(e):
        print("Entity doesn't exist or has expired")
    else:
        raise

try:
    entity_key, _ = client.arkiv.create_entity(
        payload=data,
        attributes={"invalid-key": "value"}  # Invalid attribute name
    )
except AttributeException as e:
    print(f"Attribute error: {e}")

try:
    receipt = client.arkiv.execute(operations)
except RuntimeError as e:
    if "Transaction failed" in str(e):
        print("Transaction reverted")
        # Check logs, retry, etc.
```

---

### Async/Await Support

For high-performance applications:

```python
import asyncio
from arkiv import AsyncArkiv

async def process_entities():
    async with AsyncArkiv() as client:
        # All operations are async
        entity_key, receipt = await client.arkiv.create_entity(
            payload=b"Async data",
            attributes={"type": "async"}
        )

        # Async iteration
        query = 'type = "user"'
        async for entity in client.arkiv.query_entities(query):
            await process_user(entity)

        # Async batch operations
        tasks = [
            client.arkiv.create_entity(payload=f"Entity {i}".encode())
            for i in range(100)
        ]
        results = await asyncio.gather(*tasks)

asyncio.run(process_entities())
```

---

## Part 7: Production Deployment & Hackathon Tips (5 minutes)

### Deployment Checklist

#### 1. Network Configuration
```python
# Production setup
from arkiv import Arkiv
from arkiv.provider import ProviderBuilder

# Use environment variables
import os

rpc_url = os.getenv('ARKIV_RPC_URL')
provider = ProviderBuilder().custom(rpc_url).build()

# Load account from secure storage
account = load_account_from_secure_storage()

client = Arkiv(provider, account=account)
```

#### 2. Error Handling & Retry Logic
```python
import time
from web3.exceptions import Web3RPCError

def create_entity_with_retry(client, payload, attributes, max_retries=3):
    """Create entity with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            return client.arkiv.create_entity(
                payload=payload,
                attributes=attributes,
                expires_in=client.arkiv.to_seconds(days=30)
            )
        except Web3RPCError as e:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt
            print(f"Retry {attempt + 1} after {wait_time}s...")
            time.sleep(wait_time)
```

#### 3. Monitoring & Logging
```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_entity_logged(client, payload, attributes):
    """Create entity with logging."""
    logger.info(f"Creating entity with attrs: {attributes}")

    try:
        entity_key, receipt = client.arkiv.create_entity(
            payload=payload,
            attributes=attributes,
            expires_in=client.arkiv.to_seconds(days=30)
        )

        logger.info(f"Created entity {entity_key} in tx {receipt.tx_hash}")
        return entity_key, receipt

    except Exception as e:
        logger.error(f"Failed to create entity: {e}")
        raise
```

---

### Hackathon Best Practices

#### 1. Start Simple, Iterate Fast
```python
# Phase 1: Basic CRUD (30 minutes)
client = Arkiv()
entity_key, _ = client.arkiv.create_entity(payload=b"test")
entity = client.arkiv.get_entity(entity_key)

# Phase 2: Add attributes (30 minutes)
entity_key, _ = client.arkiv.create_entity(
    payload=data,
    attributes={"type": "user", "name": "Alice"}
)

# Phase 3: Add queries (1 hour)
users = list(client.arkiv.query_entities('type = "user"'))

# Phase 4: Add real-time (1 hour)
client.arkiv.watch_entity_created(on_new_user)
```

#### 2. Use Type Hints for Faster Development
```python
from arkiv import Arkiv
from arkiv.types import Entity, EntityKey, TransactionReceipt

def create_user_profile(
    client: Arkiv,
    user_data: dict
) -> tuple[EntityKey, TransactionReceipt]:
    """IDE autocomplete and type checking work perfectly."""
    return client.arkiv.create_entity(
        payload=json.dumps(user_data).encode(),
        content_type="application/json",
        attributes={"type": "user"},
        expires_in=client.arkiv.to_seconds(days=30)
    )
```

#### 3. Leverage Tests from SDK
```python
# Copy test patterns from SDK repo
# File: tests/test_entity_create.py

def test_your_feature():
    client = Arkiv()

    # Create test data
    entity_key, _ = client.arkiv.create_entity(...)

    # Verify
    entity = client.arkiv.get_entity(entity_key)
    assert entity.payload == expected

    # Cleanup
    client.arkiv.delete_entity(entity_key)
```

---

### Common Pitfalls & Solutions

#### Pitfall 1: Forgetting Expiration
```python
# ❌ Bad: Entity expires too soon
entity_key, _ = client.arkiv.create_entity(
    payload=data,
    expires_in=100  # Only 100 seconds!
)

# ✅ Good: Use time helpers
entity_key, _ = client.arkiv.create_entity(
    payload=data,
    expires_in=client.arkiv.to_seconds(days=30)
)
```

#### Pitfall 2: Update Not Merge
```python
# ❌ Bad: Loses existing attributes
client.arkiv.update_entity(
    entity_key,
    payload=new_data,
    attributes={"new_field": "value"}  # Old attributes lost!
)

# ✅ Good: Read-modify-write pattern
entity = client.arkiv.get_entity(entity_key)
attrs = entity.attributes
attrs["new_field"] = "value"

client.arkiv.update_entity(
    entity_key,
    payload=new_data,
    attributes=attrs
)
```

#### Pitfall 3: Not Using Batch Operations
```python
# ❌ Slow: Individual transactions
for item in items:
    client.arkiv.create_entity(...)  # N transactions

# ✅ Fast: Single batch transaction
from arkiv.types import Operations, CreateOp

operations = Operations(
    creates=[
        CreateOp(payload=item.encode(), attributes={"id": i})
        for i, item in enumerate(items)
    ]
)
receipt = client.arkiv.execute(operations)  # 1 transaction
```

---

### Demo Ideas for Hackathon

#### 1. Decentralized Social Network
- User profiles, posts, comments
- Query by hashtags, trending topics
- Real-time feed updates
- Affordable (1000s of posts for pennies)

#### 2. NFT Marketplace with Advanced Filtering
- Store metadata affordably
- Complex queries (collection, traits, price range)
- Real-time listing notifications
- Sorting by price, rarity, etc.

#### 3. Multiplayer Game Leaderboard
- Store match results
- Query top players, recent games
- Real-time score updates
- Historical game data

#### 4. DAO with Rich Proposals
- Store full proposal details (not just IPFS hash)
- Query by status, category, deadline
- Real-time voting events
- Discussion threads attached

#### 5. Supply Chain Tracker
- Product journey entities
- Query by location, status, time
- Real-time tracking updates
- Compliance audit trail

---

## Resources & Next Steps

### Documentation
- **GitHub**: [github.com/Arkiv-Network/arkiv-sdk-python](https://github.com/Arkiv-Network/arkiv-sdk-python)
- **Full API Docs**: See README.md
- **Getting Started Guide**: `docs/GETTING_STARTED.md`
- **Code Examples**: `tests/` directory

### Networks
- **Kaolin Testnet**: `https://kaolin.hoodi.arkiv.network/rpc`
- **Local Node**: Automatic via `Arkiv()` (requires Docker)

### Support During Hackathon
- Open GitHub issues for bugs
- Check existing tests for examples
- Use type hints + IDE for autocomplete
- Start with simple examples, build up

### Quick Reference Commands

```bash
# Installation
pip install arkiv-sdk

# Create wallet
uv run python -m arkiv.account alice

# Run tests (learn from examples)
uv run pytest tests/ -v

# Type checking
uv run mypy your_code.py
```

---

## Challenge: Build the Impossible

**Your mission**: Build something that requires all three:
1. ✅ Decentralized (no single point of failure)
2. ✅ Affordable (pennies, not dollars)
3. ✅ Queryable (complex filters, sorting, real-time)

**Ideas to get started**:
- Social network where users own their data
- NFT marketplace with advanced search
- Gaming platform with rich state
- DAO with comprehensive governance
- DeFi with detailed transaction history

**Remember**: Before Arkiv, you had to compromise. Now you don't! 🚀

---

## Questions & Live Coding

Let's build something together!

What would you like to see?
- Live entity creation and queries?
- Real-time event watching?
- Complex query examples?
- Batch operations?
- Your idea?

**Let's make decentralization accessible!** 🎉
