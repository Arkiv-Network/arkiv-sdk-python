# Arkiv: Web3 Data made Queryable and Affordable

## Problem Statement: Decentralized Data is Painful...

When building data centric decentralized applications today, you are left with painful choices:

**Option 1**: Onchain Ethereum
- ✅ Allows Web3 Data
- ❌ Not Really Queryable (nowhere near SQL)
- ❌ Expensive ($$$ for MB of data)

**Option 2**: Decentralized Data (IPFS/Arweave)
- ✅ Built for Web3 Data
- ✅ Affordable
- ❌ **Not Queryable** (nowhere near SQL)

**Option 3**: Web2 (Centralized AWS, Azure, Google Clouds)
- ✅ Affordable
- ✅ Queryable (full SQL, powerful APIs)
- ❌ **Centralized** (single point of failure, censorship, no ownership)

---

## Enter Arkiv

**Arkiv = Decentralized + Affordable + Queryable**

### What is Arkiv?

A Web3 data protocol that runs on the Optimism L2 technology stack, designed specifically for dApp data needs:

- **Decentralized**: Runs on blockchain infrastructure
- **Queryable**: SQL-like queries, attributes, real-time filters
- **Affordable**: Storage costs << than current L1/L2 solutions

---

## How Arkiv Works

### Entities: The Core Concept

Arkiv stores data as **entities**.
Think of entities as **Data + Searchable Attributes + Expiration Timer**

1. **Payload**: Your actual data (any binary content - JSON, images, documents, etc.)
2. **Queryable Attributes**: Key-value metadata (strings and numbers) that you can filter and sort by
3. **Lifetime**: Time-based expiration (pay only for how long you need the data)

This combination gives you the power of a database with the decentralization of blockchain.

---

## Real-World Use Cases

- **Gaming**:
  - Store game states
  - Player inventories
  - Match results
  - Query by level, status, achievements

- **Social Networks**:
  - Store posts, comments, profiles
  - User connections and feeds
  - Media attachments
  - Query by hashtags, mentions, timestamps

- **NFT Marketplaces**:
  - Store metadata affordably
  - Listing details
  - Trading history
  - Query by collection, rarity, price, traits

- **DeFi Applications**:
  - Store transaction history
  - User positions
  - Trading data
  - Query by address, amount, time period

---

## Why Arkiv for Your Project?

| Feature | **Arkiv** | Ethereum | IPFS | Web2 DB |
|---------|-----------|----------|------|---------|
| Web3 Data | ✅ | ✅ | ✅ | ❌ |
| Affordable | ✅ | ❌ | ✅ | ✅ |
| SQL-like Queries | ✅ | ❌ | ❌ | ✅ |
| Real-time Events | ✅ | ✅ | ❌ | ✅ |

---

## Quick Start for Hackathon

### Installation (30 seconds)
```bash
pip install arkiv-sdk
```

### Hello World (2 minutes)
```python
from arkiv import Arkiv

# Auto-setup: local node + funded account
client = Arkiv()

# Create entity
entity_key, _ = client.arkiv.create_entity(
    payload=b"My hackathon project data",
    attributes={"team": "awesome", "category": "defi"}
)

# Query it back
entity = client.arkiv.get_entity(entity_key)
print(entity.payload)
print(entity.attributes)
```

### Deploy to Testnet (2 minutes)
```python
from arkiv import Arkiv
from arkiv.provider import ProviderBuilder

# Connect to Mendoza
MENDOZA_RPC = "https://mendoza.hoodi.arkiv.network/rpc"
provider = ProviderBuilder().custom(MENDOZA).build()
client = Arkiv(provider, account=your_account)

# Same API, now on Mendoza!
```

### SQL Like Query Language
```python
query = 'type = "user" AND age >= 18 AND (status = "active" OR status = "premium")'
users = list(client.arkiv.query_entities(query))
```

### Real-Time Events
```python
# Watch for new data in real-time
def on_new_entity(event, tx_hash):
    print(f"New entity: {event}")

client.arkiv.watch_entity_created(on_new_entity)
```

### Familiar Developer Experience
```python
# Built on Web3.py - use all standard Ethereum tools
balance = client.eth.get_balance(address)
tx = client.eth.send_transaction({...})
```

---

## Resources for Hackathon

### Documentation
- **Getting Started**: [arkiv.network](https://arkiv.network/getting-started/typescript)

### Live Network
- **Mendoza**: Public Arkiv testnet available now
- **Homepage**: [mendoza.hoodi.arkiv.network](https://mendoza.hoodi.arkiv.network/)

### Support
- **Typescript**: [github.com/Arkiv-Network/arkiv-sdk-js](https://github.com/Arkiv-Network/arkiv-sdk-js)
- **Python**: [github.com/Arkiv-Network/arkiv-sdk-python](https://github.com/Arkiv-Network/arkiv-sdk-python)
- **Issues**: Open issues for bugs or questions

---

## Key Takeaways

1. **Arkiv solves the trilemma**: Decentralized + Affordable + Queryable
2. **5-minute setup**: Perfect for hackathons
3. **Familiar tools**: SDKs built on Web3 standard tooling
4. **Production-ready**: Testnet available, SDK stable
5. **Rich features**: Queries, events, sorting, pagination

---

## Let's Build!

1. **Getting Started**: [arkiv.network/getting-started](https://arkiv.network/getting-started)
3. **Read the Docs**: Check SDK readme documents
4. **Attend the 45min session**: Deep dive into advanced features
5. **Start Building**: Make the impossible possible!

---

## Questions?

**Ready to build decentralized apps that don't compromise?**

Let's solve real problems with Arkiv! 🚀
