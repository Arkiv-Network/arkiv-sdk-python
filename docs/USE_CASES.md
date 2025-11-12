# Arkiv Use Cases

**Build the web3 product you want, not the one gas prices allow.**

Arkiv provides 100-1000x cheaper storage than traditional L2 chains, making previously unaffordable use cases economically viable. This document outlines the most compelling applications for Arkiv's permissioned, queryable, blockchain-based storage.

---

## Top Use Cases

### 1. NFT Metadata & Small Images

**The Problem**: Storing NFT metadata and images on-chain is prohibitively expensive. Most projects use centralized servers or IPFS with mutable, centralized pinning.

**Arkiv Solution**:
```python
from pathlib import Path

# Read a small PNG image (e.g., icon, thumbnail, pixel art)
image_path = Path("punk_icon.png")
image_data = image_path.read_bytes()

# Store image directly on Arkiv with metadata as attributes
entity_key, tx_hash = client.arkiv.create_entity(
    payload=image_data,  # Raw PNG bytes
    attributes={
        "name": "CryptoPunk#1234",
        "collection": "cryptopunks",
        "token_id": 1234,
        "trait_type": "beanie",
        "trait_eyes": "blue"
    },
    expires_in=100_000_000  # a few years with 2s blocks
)

# NFT contract points to entity_key
nft.tokenURI(1234) -> f"arkiv://{entity_key}"

# Retrieve and display the image
entity = client.arkiv.get_entity(entity_key)
Path("retrieved_punk.png").write_bytes(entity.payload)

# Query by attributes
punks_with_beanie = client.arkiv.query_all_entities(
    "SELECT * WHERE collection='cryptopunks' AND trait_type='beanie'"
)
```

**Why It Wins**:
- 100-1000x cheaper than L2 storage
- Truly on-chain (not IPFS trust assumptions)
- Images under ~100KB fit directly in payload
- Queryable by traits and attributes
- Almost instant retrieval without IPFS gateway delays

**Use Cases**:
- Pixel art NFTs (like CryptoPunks at 24x24)
- Icons and thumbnails (small PNGs/SVGs)
- Gaming item sprites
- Badge and achievement images
- Profile avatars
- Small generative art

**Note**: For larger images (>100KB), see "File Vault" use case below or combine with IPFS and put the IPFS hash in attributes.

---

### 2. File Vault with Chunking

**The Problem**: Store files larger than the entity size limit on-chain without relying on IPFS or centralized storage.

**Arkiv Solution**:
```python
CHUNK_SIZE = 100_000  # Entity size limit

# Split file into chunks
file_data = Path("video.mp4").read_bytes()
file_hash = hashlib.sha256(file_data).hexdigest()

chunk_keys = []
for i in range(0, len(file_data), CHUNK_SIZE):
    chunk_key, _ = client.arkiv.create_entity(
        payload=file_data[i:i + CHUNK_SIZE],
        attributes={"file_hash": file_hash, "chunk_index": i // CHUNK_SIZE},
        expires_in=100_000_000
    )
    chunk_keys.append(chunk_key)

# Create manifest
manifest_key, _ = client.arkiv.create_entity(
    payload=file_hash.encode(),
    attributes={
        "type": "file_manifest",
        "file_name": "video.mp4",
        "chunk_keys": ",".join(chunk_keys),
    },
    expires_in=100_000_000
)

# Reconstruct file
manifest = client.arkiv.get_entity(manifest_key)
reconstructed = b"".join(
    client.arkiv.get_entity(k).payload
    for k in manifest.attributes["chunk_keys"].split(",")
)
```

**Why It Wins**:
- Store unlimited file sizes on-chain
- Queryable metadata
- Compose with other use cases
- Avoids IPFS trust assumptions or centralized storage

**Use Cases**:
- High-res NFT artwork
- Videos
- Documents
- Static web pages
- Software packages

---

### 3. Gaming State & Inventory

**The Problem**: Game state on traditional L1/L2s is too expensive. Most games use centralized servers, breaking web3 promises.

**Arkiv Solution**:
```python
# Player inventory - create once, update frequently
player_state = client.arkiv.create_entity(
    payload=msgpack.packb({
        "health": 100,
        "inventory": ["sword", "shield", "potion"],
        "position": {"x": 123, "y": 456},
        "quests": {"main_story": 5, "side_quests": 12}
    }),
    attributes={
        "player_id": player_address,
        "level": 15,
        "guild": "dragons",
        "online": 1,
        "pvp_rating": 1850
    },
    expires_at_block=current_block + 1_000_000  # Auto-expire inactive players
)

# Update 1000x cheaper than L2
entity = arkiv.get_entity(entity_key)
client.arkiv.update_entity(payload=entity.payload, attributes=entity.attributes | {"level": 16})

# Query all online guild members
players = client.arkiv.query_entities(
    "SELECT * WHERE attributes.guild = 'dragons' AND attributes.online = 1"
)

# Find players for PVP matchmaking
opponents = client.arkiv.query_entities(
    "SELECT * WHERE attributes.pvp_rating BETWEEN 1800 AND 1900"
)
```

**Why It Wins**:
- Real-time updates without breaking the bank
- Auto-expiration cleans up abandoned accounts
- On-chain verifiability for tournaments/leaderboards
- Queryable game state (guild rosters, matchmaking, leaderboards)
- No centralized game server needed

**Use Cases**:
- MMO player state and inventory
- Turn-based strategy games
- Leaderboards and rankings
- Guild/clan management
- Achievement tracking
- Item trading marketplaces

---

### 4. Social Media & Content Platforms

**The Problem**: Decentralized social media needs cheap, permissioned storage for posts, profiles, and interactions.

**Arkiv Solution**:
```python
# User posts
post = client.arkiv.create_entity(
    payload=post_content.encode(),
    attributes={
        "author": user_address,
        "timestamp": block_number,
        "type": "post",
        "likes": 0,
        "reposts": 0,
        "hashtag": "web3"
    },
    expires_at_block=current_block + 10_000_000  # ~4 months
)

# Extend popular posts
if likes > 1000:
    client.arkiv.extend_entity(post_key, number_of_blocks=20_000_000)  # Keep for 8 more months

# Query feed
feed = client.arkiv.query_entities(
    "SELECT * WHERE attributes.author IN (following_list) ORDER BY timestamp DESC LIMIT 50"
)
```

**Why It Wins**:
- Cheap enough for high-volume content
- User owns their data (can delete/update)
- Auto-expiration = natural content lifecycle
- No centralized moderation needed for expired content
- Queryable feeds (following, hashtags, trending)
- Censorship-resistant (permissioned updates)

**Use Cases**:
- Decentralized Twitter/X alternative
- Blog platforms
- Community forums
- Content curation platforms
- Creator subscriptions
- Media sharing

---

### 5. DAO Proposals & Governance

**The Problem**: Storing full proposal text, discussions, and vote updates on-chain is prohibitively expensive.

**Arkiv Solution**:
```python
# Create proposal
proposal = client.arkiv.create_entity(
    payload=full_proposal_markdown.encode(),
    attributes={
        "dao": "uniswap",
        "type": "proposal",
        "proposal_id": some_unique_id,
        "proposal_closes": timestamp,
        "status": "active",
        "votes_for": 0,
        "votes_against": 0,
        "quorum": 40000000
    },
    expires_in=100_000_000  # Keep for historical record
)

# Update vote counts (cheap!)
arkiv.update_entity(
    proposal_key,
    payload=proposal.payload,  # Same text
    attributes={"votes_for": 1234, "votes_against": 567, "status": "passed"},
    expires_in=100_000_000  # Keep for historical record
)

# Query all active proposals
proposals = client.arkiv.query_entities(
    "SELECT * WHERE attributes.dao = 'uniswap' AND attributes.status = 'active'"
)

# Historical analysis
history = client.arkiv.query_entities(
    "SELECT * WHERE attributes.dao = 'uniswap' AND attributes.status = 'passed' ORDER BY timestamp DESC"
)
```

**Why It Wins**:
- Full proposal text on-chain (not IPFS hash)
- Update counts/status without expensive L2 txs
- Historical record with controlled expiration
- Queryable proposal history
- Transparent governance process

**Use Cases**:
- DAO voting systems
- Governance proposals
- Community polls
- Treasury allocation requests
- Protocol upgrade proposals
- Multi-sig decision tracking

---

### 6. DeFi Analytics & Oracle Data

**The Problem**: Storing historical price feeds, market data, and analytics on L2 is too expensive for high-frequency updates.

**Arkiv Solution**:
```python
# Price oracle writes every block
btc_price_data = client.arkiv.create_entity(
    payload=b'',
    attributes={
        "price": 3450230000, # price as int
        "block": block_number,
        "timestamp": timestamp,
        "pair": "eth_usd",
        "source": chainlink_feed_address,
        "network_id": network_id,
        "market": "crypto"
    },
    expires_in=100_000  # Keep 1 month
)

# Applications read latest or query history
historical = client.arkiv.query_entities(
    "SELECT * WHERE timestamp > your_date_time AND market = 'crypto' ORDER BY timestamp DESC LIMIT 1000"
)
```

**Why It Wins**:
- High-frequency updates affordable
- On-chain historical data without massive costs
- Auto-expiration keeps storage manageable
- Queryable time-series data
- Verifiable data provenance

**Use Cases**:
- Price oracles
- Trading volume tracking
- Liquidity pool analytics
- Market data aggregation
- Risk assessment data
- Historical backtesting data

---

### 7. Supply Chain & Document Tracking

**The Problem**: Enterprise needs immutable audit trails but can't afford L1/L2 costs for every event.

**Arkiv Solution**:
```python
# Product shipment tracking
shipment_key = client.arkiv.create_entity(
    payload=shipment_document_pdf,
    attributes={
        "type": "shipment",
        "tracking_id": "SHIP-12345",
        "company": "acme_corp",
        "product_sku": "PROD-789",
        "status": "in_transit",
    },
    expires_in=10_000_000  # Keep 6 months
)

status_key = client.arkiv.create_entity(
    payload=b''
    attributes={
        "type": "shipment_status",
        "shipment_key": shipment_key,
        "status": "in_transit",
        "location": "warehouse_b",
        "temperature": 5.0,
    }
    expires_in=10_000_000  # Keep 6 months
)

delivery_key = client.arkiv.create_entity(
    payload=b''
    attributes={
        "type": "shipment_status",
        "shipment_key": shipment_key,
        "status": "delivered",
        "location": "customer",
        "temperature": 11.0,
        "delivery_timestamp": delivery_timestamp,
        "signature": customer_signature_hash,
    }
    expires_in=10_000_000  # Keep 6 months
)

# Update status at each checkpoint
client.arkiv.update_entity(
    shipment_key,
    payload=updated_document_pdf,
    attributes=attributes | {
        "status": "delivered",
        "delivery": delivery_key,
    }
)

# Audit query for delivered items
audit = client.arkiv.query_entities(
    "SELECT * WHERE type = 'shipment'"
    "AND company = 'acme_corp'"
    "AND status = 'delivered'"
)

# Compliance reporting
report = client.arkiv.query_entities(
    "SELECT * WHERE type = 'shipment_status'"
    "AND product_sku = 'PROD-789'"
    "AND temperature > 10.0"
)
```

**Why It Wins**:
- Immutable audit trail
- Affordable for high-volume operations
- Compliance without centralized databases
- Controlled retention (auto-expiration)
- Multi-party verification
- Queryable for reporting

**Use Cases**:
- Logistics and shipping
- Food safety tracking
- Pharmaceutical chain of custody
- Manufacturing quality control
- Document verification
- Customs and trade compliance

---

### 8. AI Model Versioning & Training Data

**The Problem**: Tracking ML model versions, training datasets, and experiment results on-chain for reproducibility is too expensive.

**Arkiv Solution**:
```python
# Store model weights hash + metadata
model_entity_key = client.arkiv.create_entity(
    payload=model_metadata_json.encode(),
    attributes={
        "model_hash": ipfs_cid,
        "version": "v2.1.3",
        "training_data_hash": dataset_hash,
        "author": researcher_address,
        "framework": "pytorch"
    },
    expires_in=10_000_000
)

# Track experiments
experiment = client.arkiv.create_entity(
    payload=hyperparameters_json.encode(),
    attributes={
        "experiment_id": "exp-456",
        "model_key": model_entity_key,
        "validation_data_hash": ipfs_cid,
        "test_data_hash": ipfs_cid,
        "learning_rate": 0.001,
        "epochs": 100,
        "accuracy": 95,
        "f1_score": 93,
        },
    expires_in=5_000_000
)

# Provable model lineage
lineage = client.arkiv.query_entities(
    "SELECT * WHERE attributes.training_data_hash = ? ORDER BY version",
    params=[dataset_hash]
)

# Find best models
best = client.arkiv.query_entities(
    "SELECT * WHERE attributes.accuracy > 95 ORDER BY accuracy DESC LIMIT 10"
)
```

**Why It Wins**:
- Reproducible ML research
- Model provenance on-chain
- Cheap enough for versioning every experiment
- Queryable model registry
- Verifiable training data
- Collaborative research tracking

**Use Cases**:
- ML model registries
- Research reproducibility
- Collaborative AI development
- Training data provenance
- Model performance benchmarking
- AI safety and auditing

---

## The Value Proposition

### The Problem All These Use Cases Share:
- **Current L1/L2 storage**: Too costly to store real world data
- **Centralized DBs**: Break web3 promises (censorship, single point of failure)
- **IPFS**: Requires pinning services, trust assumptions

### Arkiv's Unique Position:

1. **100-1000x cheaper** than L2 → Makes many use cases economically viable
2. **Truly on-chain** → No IPFS trust, no centralized servers
3. **Permissioned ownership** → Only you can update your data
4. **Auto-expiration** → Natural data lifecycle, no bloat
5. **Queryable** → Not just key-value, actual SQL queries
6. **Web3 native** → Drop into any Web3.py project today

---

## Target Segments

### 1. Gaming Studios
**Pain**: State updates and inventory management kill L2 budgets
**Arkiv Solution**: Real-time game state for pennies

### 2. NFT Platforms
**Pain**: Metadata storage is their #1 operational cost
**Arkiv Solution**: Dynamic, queryable NFT metadata at 1/1000th the cost

### 3. Social Applications
**Pain**: Need high write throughput for posts, likes, comments
**Arkiv Solution**: Twitter-scale throughput at blockchain prices

### 4. DAOs & Governance
**Pain**: Proposals + discussions add up quickly
**Arkiv Solution**: Full governance history on-chain, affordably

### 5. Enterprise Blockchain
**Pain**: Audit trails and compliance require every event on-chain
**Arkiv Solution**: Complete audit logs without breaking budgets

---

## Getting Started

```python
from arkiv import Arkiv

# Create an Arkiv client for prototyping.
# The default setup creates a funded default account and starts a containerized Arkiv node.
client = Arkiv()

# Start building
entity_key, tx_hash = client.arkiv.create_entity(
    payload=b"Your data here",
    attributes={"type": "example", "version": 1},
)

# Query your data
entity = client.arkiv.get_entity(entity_key)
```

---

## Additional Resources

TODO

---

## Have a Use Case We Missed?

We'd love to hear about it! Open an issue or submit a PR to add your use case to this document.
