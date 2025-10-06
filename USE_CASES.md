# Arkiv Use Cases

**Build the web3 product you want, not the one gas prices allow.**

Arkiv provides 100-1000x cheaper storage than traditional L2 chains, making previously unaffordable use cases economically viable. This document outlines the most compelling applications for Arkiv's permissioned, queryable, blockchain-based storage.

---

## Top Use Cases

### 1. NFT Metadata & Dynamic NFTs

**The Problem**: Storing NFT metadata on-chain is prohibitively expensive. Most projects use centralized servers or IPFS with mutable, centralized pinning.

**Arkiv Solution**:
```python
# Mint NFT on mainnet/L2, store metadata on Arkiv DB chain
nft_metadata = {
    "name": "CryptoPunk #1234",
    "image": "ipfs://...",
    "attributes": {...},
    "level": 5,
    "experience": 1250
}

# Store on Arkiv - pennies instead of dollars
entity_key, _ = arkiv.create_entity(
    payload=json.dumps(nft_metadata).encode(),
    annotations={"collection": "cryptopunks", "token_id": "1234", "level": 5},
    expires_at_block=NEVER_EXPIRES
)

# NFT contract points to entity_key
nft.tokenURI(1234) -> f"arkiv://{entity_key}"

# Update NFT as character levels up
arkiv.update_entity(
    entity_key,
    payload=updated_metadata,
    annotations={"level": 6, "experience": 2000}
)
```

**Why It Wins**:
- 100-1000x cheaper than L2 storage
- Truly on-chain (not IPFS trust assumptions)
- Updatable (gaming NFTs, evolving art)
- Queryable (filter by level, rarity, attributes)
- Ownership enforced (only NFT owner can update)

**Use Cases**:
- Gaming NFTs with evolving stats
- Dynamic art that changes based on conditions
- Achievement/badge systems
- Collectibles with upgradeable traits
- Reputation-based NFTs

---

### 2. Gaming State & Inventory

**The Problem**: Game state on traditional L1/L2s is too expensive. Most games use centralized servers, breaking web3 promises.

**Arkiv Solution**:
```python
# Player inventory - create once, update frequently
player_state = arkiv.create_entity(
    payload=msgpack.packb({
        "health": 100,
        "inventory": ["sword", "shield", "potion"],
        "position": {"x": 123, "y": 456},
        "quests": {"main_story": 5, "side_quests": 12}
    }),
    annotations={
        "player_id": player_address,
        "level": 15,
        "guild": "dragons",
        "online": 1,
        "pvp_rating": 1850
    },
    expires_at_block=current_block + 1_000_000  # Auto-expire inactive players
)

# Update 1000x cheaper than L2
arkiv.update_entity(entity_key, new_state, annotations={"level": 16})

# Query all online guild members
players = arkiv.query(
    "SELECT * WHERE annotations.guild = 'dragons' AND annotations.online = 1"
)

# Find players for PVP matchmaking
opponents = arkiv.query(
    "SELECT * WHERE annotations.pvp_rating BETWEEN 1800 AND 1900"
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

### 3. Social Media & Content Platforms

**The Problem**: Decentralized social media needs cheap, permissioned storage for posts, profiles, and interactions.

**Arkiv Solution**:
```python
# User posts
post = arkiv.create_entity(
    payload=post_content.encode(),
    annotations={
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
    arkiv.extend_entity(post_key, 20_000_000)  # Keep for 8 more months

# Query feed
feed = arkiv.query(
    "SELECT * WHERE annotations.author IN (following_list) ORDER BY timestamp DESC LIMIT 50"
)

# Trending hashtags
trending = arkiv.query(
    "SELECT hashtag, COUNT(*) as count WHERE timestamp > ? GROUP BY hashtag ORDER BY count DESC",
    params=[recent_block]
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

### 4. DAO Proposals & Governance

**The Problem**: Storing full proposal text, discussions, and vote updates on-chain is prohibitively expensive.

**Arkiv Solution**:
```python
# Create proposal
proposal = arkiv.create_entity(
    payload=full_proposal_markdown.encode(),
    annotations={
        "dao": "uniswap",
        "type": "proposal",
        "status": "active",
        "votes_for": 0,
        "votes_against": 0,
        "quorum": 40000000
    },
    expires_at_block=voting_end_block + 100_000  # Keep for historical record
)

# Update vote counts (cheap!)
arkiv.update_entity(
    proposal_key,
    payload=proposal.payload,  # Same text
    annotations={"votes_for": 1234, "votes_against": 567, "status": "passed"}
)

# Query all active proposals
proposals = arkiv.query(
    "SELECT * WHERE annotations.dao = 'uniswap' AND annotations.status = 'active'"
)

# Historical analysis
history = arkiv.query(
    "SELECT * WHERE annotations.dao = 'uniswap' AND annotations.status = 'passed' ORDER BY timestamp DESC"
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

### 5. DeFi Analytics & Oracle Data

**The Problem**: Storing historical price feeds, market data, and analytics on L2 is too expensive for high-frequency updates.

**Arkiv Solution**:
```python
# Price oracle writes every block
price_data = arkiv.create_entity(
    payload=msgpack.packb({
        "eth_usd": 3450.23,
        "btc_usd": 65432.11,
        "volume_24h": 1_234_567_890,
        "timestamp": block.timestamp
    }),
    annotations={
        "block": block_number,
        "source": "chainlink",
        "market": "crypto"
    },
    expires_at_block=block_number + 100_000  # Keep 1 week of data
)

# Applications read latest or query history
historical = arkiv.query(
    "SELECT * WHERE annotations.block > ? AND annotations.market = 'crypto' ORDER BY block DESC LIMIT 1000",
    params=[block_number - 1000]
)

# Analytics
avg_price = arkiv.query(
    "SELECT AVG(eth_usd) WHERE annotations.block BETWEEN ? AND ?",
    params=[start_block, end_block]
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

### 6. Supply Chain & Document Tracking

**The Problem**: Enterprise needs immutable audit trails but can't afford L1/L2 costs for every event.

**Arkiv Solution**:
```python
# Product shipment tracking
shipment = arkiv.create_entity(
    payload=shipment_document_pdf,
    annotations={
        "tracking_id": "SHIP-12345",
        "status": "in_transit",
        "location": "warehouse_b",
        "temperature": 22,
        "company": "acme_corp",
        "product_sku": "PROD-789"
    },
    expires_at_block=delivery_block + 2_000_000  # Keep 6 months post-delivery
)

# Update status at each checkpoint
arkiv.update_entity(
    shipment_key,
    payload=updated_document,
    annotations={"status": "delivered", "location": "customer", "signature": "0x..."}
)

# Audit query
audit = arkiv.query(
    "SELECT * WHERE annotations.company = 'acme_corp' AND annotations.status = 'delivered'"
)

# Compliance reporting
report = arkiv.query(
    "SELECT * WHERE annotations.temperature > 25 AND annotations.product_sku = 'PROD-789'"
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

### 7. AI Model Versioning & Training Data

**The Problem**: Tracking ML model versions, training datasets, and experiment results on-chain for reproducibility is too expensive.

**Arkiv Solution**:
```python
# Store model weights hash + metadata
model = arkiv.create_entity(
    payload=model_metadata_json.encode(),
    annotations={
        "model_hash": ipfs_cid,
        "version": "v2.1.3",
        "accuracy": 95,
        "f1_score": 93,
        "training_data_hash": dataset_hash,
        "author": researcher_address,
        "framework": "pytorch"
    },
    expires_at_block=NEVER_EXPIRES
)

# Track experiments
experiment = arkiv.create_entity(
    payload=hyperparameters_json.encode(),
    annotations={
        "experiment_id": "exp-456",
        "parent_model": model_hash,
        "learning_rate": 0.001,
        "epochs": 100,
        "best_accuracy": 96
    },
    expires_at_block=current_block + 5_000_000
)

# Provable model lineage
lineage = arkiv.query(
    "SELECT * WHERE annotations.training_data_hash = ? ORDER BY version",
    params=[dataset_hash]
)

# Find best models
best = arkiv.query(
    "SELECT * WHERE annotations.accuracy > 95 ORDER BY accuracy DESC LIMIT 10"
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
- **Current L1/L2 storage**: $10-$1000 per write
- **Centralized DBs**: Break web3 promises (censorship, single point of failure)
- **IPFS**: Mutable, requires pinning services, trust assumptions

### Arkiv's Unique Position:

1. **100-1000x cheaper** than L2 → Makes new use cases economically viable
2. **Truly on-chain** → No IPFS trust, no centralized servers
3. **Permissioned ownership** → Only you can update your data
4. **Auto-expiration** → Natural data lifecycle, no bloat
5. **Queryable** → Not just key-value, actual SQL queries
6. **Web3 native** → Drop into any Web3.py project today
7. **L2 integrated** → Bridge to mainnet when needed

### Migration Path:

```python
# Week 1: Keep using your L2 for core logic
l2_contract.mint_nft(token_id, owner)

# Week 2: Move expensive storage to Arkiv
arkiv.create_entity(metadata, annotations={"token_id": token_id})

# Week 3: Save 90%+ on gas costs
# Week 4: Launch features you couldn't afford before
```

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
    annotations={"type": "example", "version": 1},
    expires_at_block=future_block
)

# Query your data
entity = client.arkiv.get_entity(entity_key)
```

**The clincher**: *"Start building like storage is free. Because on Arkiv, it basically is."*

---

## Additional Resources

- [SDK Documentation](README.md)
- [API Reference](docs/api.md)
- [Architecture Overview](README.md#architecture)
- [Development Guide](README.md#development-guide)

---

## Have a Use Case We Missed?

We'd love to hear about it! Open an issue or submit a PR to add your use case to this document.
