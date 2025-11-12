# Arkiv Marketing Guide

**Enabling Data Autonomy for Everyone**

This document explains Arkiv's vision, technology, and market positioning for marketing and business development teams. It provides approved messaging, inspirational framing, and technical guardrails to ensure accurate, compelling communication about our mission to make Web3 applications economically viable.

> **Related Documents:**
> - **USE_CASES.md**: Detailed technical use cases with working code examples (reference this for campaign ideas)
> - **README.md**: Technical documentation for developers (source of truth for features)
> - **MARKETING.md** (this doc): Marketing guidelines and approved messaging

---

## Our Mission

**Enable Data Autonomy for Everyone**

Arkiv is building the future where individuals and organizations truly own and control their data. We're creating the infrastructure that makes Web3 applications not just possible, but *practical*—by solving the cost and complexity barriers that have held the ecosystem back.

### **The Vision**

Imagine a world where:
- **You control your data**, not platforms or corporations
- **Applications are affordable to build**, not limited by prohibitive storage costs
- **Innovation happens freely**, unburdened by the economic constraints of traditional blockchain infrastructure
- **The Web3 equivalent of databases** is as easy to use and accessible as Web2 tools

This is the world Arkiv is building.

---

## What is Arkiv?

**The Web3 Database Protocol**

Arkiv is a **data storage protocol built on Ethereum** — the Web3 equivalent of traditional Web2 databases. It enables **DB-Chains**—specialized Layer 3 networks that combine blockchain security with database-like query capabilities. Think of it as the Web3 equivalent of what databases are to Web2—the fundamental infrastructure that makes applications possible.

### **Simple Explanation:**

Arkiv lets applications store and query structured data on-chain significantly more cost-efficiently than typical L2s. Your data lives on **DB-Chains** (Layer 3 networks with built-in database nodes), coordinated through Arkiv's Layer 2, all secured by Ethereum. Data is organized as flexible "entities" (like database records) with automatic lifecycle management, making Web3 applications finally economically viable.

### **Key Concepts:**

- **Three-Layer Architecture**: Ethereum (L1) → Arkiv L2 (coordination) → DB-Chains (L3, where your data lives)
- **DB-Chains**: Layer 3 networks with modified nodes that include databases for SQL-like queries
- **Database-like Structure**: Data organized as searchable entities with attributes and metadata
- **Automatic Expiration**: Built-in lifecycle management keeps costs predictable and chains lean
- **Significant Cost Reduction**: Makes previously impossible use cases affordable
- **True Data Ownership**: Users control access to their entities through blockchain-based permissions

---

## The Ethereum Ecosystem Integration

### **Architecture: The Three-Layer Model**

Arkiv uses a sophisticated three-layer architecture where **your data actually lives on DB-Chains** (Layer 3), not on the L2 itself:

**Layer 1 - Ethereum (Mainnet):**
- Security foundation and settlement layer
- Final arbiter of state and disputes

**Layer 2 - Arkiv Protocol:**
- Vanilla Optimism (OP) network for coordination
- Settlement and state management layer
- Does NOT store entity data itself
- Coordinates DB-Chain operations

**Layer 3 - DB-Chains (Where Your Data Lives):**
- **Modified OP nodes** with integrated databases
- Each DB-Chain node runs both blockchain + database
- **SQL-like queries** powered by the database layer
- **Entity storage** happens here, not on L2
- Specialized networks for different use cases or communities

**Why This Matters:**
The DB-Chain architecture (L3) is what makes Arkiv unique. Traditional L2s store everything on-chain at high cost. Arkiv's DB-Chains combine blockchain security with database efficiency—the blockchain layer handles ownership and state, while the database layer enables fast queries and affordable storage.

### **Powered by $GLM and Multi-Token Economy**

Arkiv uses **$GLM (Golem Network Token)** as the preferred gas token, creating a multi-token economy that gives users flexibility:

- **$GLM as Primary**: Preferred token for gas fees, integrated with Golem Network ecosystem
- **Multi-Token Support**: Pay gas in ETH, USDC, or other supported tokens
- **Flexible Payments**: Choose the token that works best for your application

**Gas Fee Model:**
Storage costs are calculated based on:
- Data size (bytes stored)
- Retention time (blocks to live)
- Number of attributes (queryable metadata)

### **Ethereum Alignment:**

Arkiv is deeply integrated with the Ethereum ecosystem:
- **Ethereum security** protects the entire stack (L2 coordination + L3 DB-Chains)
- **Ethereum-compatible wallets and tools** work seamlessly with Arkiv

**The Data Flow:**
1. Applications interact with DB-Chain nodes (L3) to store/query data
2. State changes settle through Arkiv L2 (OP network)
3. Final security anchored to Ethereum L1

### **Built by Golem Network**

Arkiv is developed by the team behind **Golem Network**, pioneers in decentralized computing since 2016. This collaboration brings:
- Proven expertise in distributed systems
- Commitment to decentralization and open infrastructure
- Vision of accessible, permissionless Web3 tools

---

## The Decentralization Journey

### **Protocol: Permissionless Today**

Arkiv's **protocol is permissionless** from day one:
- **Anyone can store data** - no approval needed to create entities
- **Anyone can query data** - read access is open to all
- **No gatekeepers** - the protocol itself has no access restrictions

### **Entities: Owner-Controlled by Design**

Individual entities follow an **owner-controlled model**:
- The account that creates an entity **owns** that entity
- Only the owner can **update, extend, or delete** their entity
- Ownership can be **transferred** to another account
- After transfer, the previous owner loses control

This isn't a limitation - it's a feature that enables **true data autonomy**. You control your data, not a platform or third party.

### **Network: Gradual Decentralization**

While the protocol is permissionless, the **network infrastructure** (sequencers, nodes, governance) is on a gradual decentralization journey:

- **Progressive Decentralization**: Building solid foundations before fully distributing control
- **Thoughtful Governance**: Ensuring the network is robust before opening to broader participation
- **Transparent Roadmap**: Clear communication about where we are and where we're going
- **Community-Driven Evolution**: Growing decentralization as the ecosystem matures

**Current State:** Arkiv follows the proven approach of leading L2 protocols like Base and Optimism—operating sequencers for network efficiency while maintaining open-source code for transparency and community verification.

**Future Vision:** Decentralized node operators, community governance through Arkiv Improvement Proposals (AIPs), and broader network participation.

---

## What Arkiv is NOT

### **NOT a General-Purpose Database**
- ❌ **Avoid:** "Replace your database with Arkiv"
- ✅ **Instead:** "Add blockchain-backed storage to your application"
- **Why:** Arkiv is optimized for blockchain use cases, not general operational databases

### **NOT Permanent Storage by Default**
- ❌ **Avoid:** "Store data forever on Arkiv"
- ✅ **Instead:** "Store time-limited data with configurable expiration"
- **Why:** All data requires TTL (time-to-live) and will expire unless extended

### **NOT Fully Decentralized Network (Yet)**
- ❌ **Avoid:** "Completely decentralized network infrastructure today"
- ✅ **Instead:** "Permissionless protocol with network on gradual decentralization journey"
- **Why:** The protocol is permissionless (anyone can store/query), but network infrastructure (sequencers, nodes) is progressively decentralizing

### **NOT a File Storage System**
- ❌ **Avoid:** "Upload unlimited files to Arkiv"
- ✅ **Instead:** "Store structured data with binary payloads"
- **Why:** While data can include binary content, it's optimized for structured records, not massive files

### **NOT Instant Like Traditional Databases**
- ❌ **Avoid:** "Millisecond query response times"
- ✅ **Instead:** "Block-level data updates optimized for blockchain use cases"
- **Why:** Blockchain operations have inherent latency tied to block times

---


## 🎁 Key Features to Highlight

### **1. Developer Experience**
> "Start building in minutes. Arkiv SDKs are designed to feel familiar, with comprehensive documentation and working examples."

- Intuitive APIs matching modern development patterns
- Full type safety and IDE autocomplete
- Sync and async operation modes
- SDKs: Python, JavaScript/TypeScript (available), Rust (planned)

### **2. Storage Cost Advantage**
> "Build the Web3 product you want, not the one gas prices allow."

**Key Messages:**
- Significantly more cost-efficient than typical L2s
- Makes previously unaffordable use cases economically viable
- Predictable costs with automatic data cleanup

**Technical Foundation:** Specialized storage architecture, automatic expiration, L3-based DB-Chain design, multi-token gas economy ($GLM preferred)

**Note:** Exact tokenomics being finalized—focus on architectural advantages.

### **3. Automatic Data Expiration**
> "Never worry about blockchain bloat. Data automatically expires, keeping networks lean and costs predictable. It's like garbage collection for Web3."

- Pay only for the time you need data to live
- No manual cleanup required
- Configurable per-record with extendable lifetimes

### **4. SQL-Like Query Capabilities**
> "Query blockchain data like a database. Filter by attributes, sort results, and find exactly what you need—without complex indexing infrastructure."

- Familiar SQL-like syntax for developers
- Filter, sort, and paginate natively
- No separate indexing service required
- Powerful subset optimized for blockchain (not full SQL)

### **5. Real-Time Event Monitoring**
> "React to changes in real-time. Watch for creates, updates, deletes, and ownership transfers as they happen—build truly reactive Web3 applications."

**Event Types:** Created, Updated, Extended, Deleted, Ownership Changed

**Use Cases:** Dashboards, notifications, automated workflows, live feeds

---

## Technical Specifications (Safe to Share)

### **Data Structure**
Each record ("entity") contains:
- **Unique Identifier**: 256-bit key for addressing
- **Payload**: Binary data (up to network limits)
- **Content Type**: MIME type (e.g., "application/json", "image/png")
- **Attributes**: Key-value pairs for querying (strings/integers)
- **Owner**: Ethereum address with write permissions
- **Expiration**: Block number when data expires

### **Operations Supported**
- Create data
- Update data (owner only)
- Delete data (owner only)
- Extend data lifetime (owner only, or anyone if flagged)
- Transfer ownership (owner only)
- Query data (anyone can read)

### **Network Compatibility**
- Built on Ethereum as a data storage protocol
- Compatible with Ethereum-standard wallets and tools
- Web3 RPC interface for queries
- Testnet available (Kaolin network)

### **Token Economy**
- **$GLM**: Preferred token for gas fees
- **Multi-Token Support**: Pay in ETH, USDC, or other supported tokens
- **Fee Model**: Based on data size, retention time, and attributes

---

## Common Marketing Mistakes to Avoid

**Critical Don'ts:**
- ❌ Storage: "unlimited data" | "replace cloud storage" | "free storage"
- ❌ Performance: "faster than databases" | "millisecond queries" | "real-time like Redis"
- ❌ Permanence: "permanent storage" | "data stored forever" | "never expires"
- ❌ Decentralization: "fully decentralized network today" | "no centralized components"
- ❌ Cost: "free blockchain storage" | specific multipliers (1000x) | "cheaper than AWS"
- ❌ Scope: "deploy any smart contract" | "run complex computations"

**What to Say Instead:**
- ✅ "Structured application data" | "time-limited with configurable expiration"
- ✅ "Optimized for blockchain use cases" | "block-level granularity"
- ✅ "Permissionless protocol, owner-controlled entities, network decentralizing gradually"
- ✅ "Significantly more cost-efficient than typical L2s" (always specify vs. L2)
- ✅ "Data storage layer with programmable access control"

**Key Reminders:**
- All data expires (TTL required, extendable)
- Transaction/gas costs exist ($GLM, ETH, or other tokens)
- Tokenomics being finalized—focus on architectural advantages
- Protocol is permissionless; entities are owner-controlled; network infrastructure decentralizing
- Blockchain latency tied to block times

---

## Approved Marketing Messages

### **Elevator Pitch**
> "Arkiv is enabling Data Autonomy for Everyone by making Web3 applications finally economically viable. Built on Ethereum, we provide significantly more cost-efficient storage than typical L2s, with SQL-like queries, automatic data lifecycle management, and real-time events. Built by the Golem Network team and powered by $GLM, Arkiv is the Web3 database protocol that lets you build the product you want, not the one gas prices allow."

### **One-Liners**
1. "Enabling Data Autonomy for Everyone"
2. "Build the Web3 product you want, not the one gas prices allow"
3. "The Web3 equivalent of databases—finally affordable and practical"
4. "Powered by $GLM, secured by Ethereum"

---

## Example Use Cases (Vetted)

> **See USE_CASES.md for detailed technical implementations with code examples**

### **Good Use Cases**

1. **NFT Metadata & Small Images**
   - Store NFT metadata and small images (icons, pixel art, thumbnails) directly on-chain
   - Significantly more cost-efficient than typical L2 storage
   - Queryable by traits and attributes
   - No IPFS trust assumptions

2. **Gaming Inventory & Player State**
   - Real-time game state updates without breaking the bank
   - Automatic cleanup of inactive player accounts (via expiration)
   - Queryable for matchmaking, leaderboards, guild rosters
   - On-chain verifiable for tournaments

3. **Social Media & Content Platforms**
   - Decentralized posts, profiles, and interactions
   - Natural content lifecycle via auto-expiration
   - User owns and controls their data
   - Queryable feeds (following, hashtags, trending)

4. **DAO Proposals & Governance**
   - Full proposal text on-chain (not just IPFS hash)
   - Update vote counts cheaply as voting progresses
   - Historical governance records with controlled retention
   - Queryable proposal archives

5. **Supply Chain & Document Tracking**
   - Immutable audit trails for compliance
   - Multi-party verification without centralized databases
   - Affordable for high-volume operations
   - Queryable for reporting and audits

6. **File Vault with Chunking**
   - Store files larger than entity size limit via chunking
   - Truly on-chain without IPFS dependencies
   - Queryable metadata across chunks
   - Suitable for videos, documents, high-res artwork

7. **DeFi Analytics & Oracle Data**
   - High-frequency price feed updates
   - On-chain historical time-series data
   - Affordable enough for real-time market data
   - Queryable for backtesting and analysis

8. **AI Model Versioning**
   - Track ML model versions and training metadata
   - Reproducible research with on-chain provenance
   - Queryable model registry
   - Collaborative AI development tracking

### **Poor Use Cases (Don't Market These)**

1. ❌ **Permanent Document Archive**
   - Why: All data expires via expires_in, not suitable for permanent legal records
   - Alternative: Extend important entities regularly, but acknowledge the maintenance

2. ❌ **Real-Time Database Replacement**
   - Why: Blockchain latency (block times), not sub-second query performance
   - Alternative: "Blockchain-backed queryable storage" not "real-time database"

3. ❌ **Public Open-Access Platform**
   - Why: Permissioned model - entities are owned and controlled
   - Alternative: "Permissioned collaborative storage" not "public wiki"

4. ❌ **High-Frequency Trading Engine**
   - Why: Block-level granularity, not microsecond execution
   - Alternative: Analytics and data storage, not execution layer

5. ❌ **Cryptocurrency or Token Platform**
   - Why: Arkiv is for data storage, not financial instruments
   - Alternative: Data layer for DeFi, not DeFi itself

---

## Competitive Positioning

### **vs. Traditional Cloud Databases**
- ✅ "Adds blockchain benefits: ownership, transparency, decentralization"
- ✅ "True data autonomy—you own your data, not the platform"
- ❌ "Replaces cloud databases entirely"

**Message:** Arkiv brings Web3 principles to application data—complementing, not replacing, existing infrastructure.

### **vs. IPFS/Arweave**
- ✅ "Structured queryable data vs. content-addressed files"
- ✅ "Built-in expiration vs. permanent storage"
- ✅ "Rich metadata and SQL-like queries vs. just file hashes"
- ✅ "No pinning services or trust assumptions required"
- ✅ "Owner-controlled lifecycle vs. pay-once-store-forever"

**Message:** Arkiv is for application data that needs queries, lifecycle management, and automatic cleanup—not general file archives.

### **vs. Traditional L2 Blockchain Storage**
- ✅ "Significantly more cost-efficient than typical L2s"
- ✅ "Purpose-built for data storage, not general computation"
- ✅ "Automatic data expiration (cost efficiency + no bloat)"
- ✅ "SQL-like queries out of the box—no separate indexers"
- ✅ "Real-time event monitoring built-in"
- ✅ "Multi-token gas economy powered by $GLM"

**Message:** Specialized storage architecture and L3-based design make Web3 applications economically viable where general L2s are prohibitively expensive. Exact tokenomics being finalized, but architectural advantages are clear.

### **vs. Other Storage Solutions**
**What Makes Arkiv Unique:**
1. **Economic Viability**: Significant cost reduction unlocks new use cases
2. **Developer Experience**: Familiar SDKs across languages with full type safety
3. **Query Power**: SQL-like capabilities without building indexing infrastructure
4. **Lifecycle Management**: Automatic expiration keeps costs predictable
5. **Ethereum Alignment**: L2 on Ethereum, fee burning, $GLM integration
6. **Proven Team**: Built by Golem Network with years of distributed systems expertise

---

## Technical Accuracy Checklist

Before publishing any marketing material, verify:

- [ ] Cost claims reference "vs. L2" or "vs. typical L2s" or "vs. traditional blockchain storage"
- [ ] "Significantly more cost-efficient than typical L2s" used (no specific multipliers like 100x)
- [ ] Tokenomics disclaimer included when discussing costs ("still being finalized")
- [ ] No claims about "permanent" or "forever" storage (all data has TTL)
- [ ] No performance comparisons without benchmarks or proper context
- [ ] Decentralization described accurately: "permissionless protocol, owner-controlled entities, network infrastructure decentralizing gradually"
- [ ] No claims that "anyone can modify any data" (only entity owners control their entities)
- [ ] Entity ownership model explained (create = own, transfer = change ownership)
- [ ] Data size limitations acknowledged if discussing storage capacity
- [ ] TTL/expiration mentioned when discussing data lifecycle
- [ ] "Time-limited" or "configurable expiration" used instead of "permanent"
- [ ] No promises about features not yet implemented
- [ ] Language-agnostic messaging (multiple SDKs planned: Python, JS/TS, Rust)
- [ ] Use cases align with those vetted in USE_CASES.md
- [ ] IPFS comparison clarifies "no pinning trust assumptions"
- [ ] $GLM mentioned as preferred gas token with multi-token support
- [ ] L2/L3 architecture explained (Arkiv = L2, DB-Chains = L3)
- [ ] Ethereum integration highlighted (security foundation)
- [ ] Golem Network relationship acknowledged
- [ ] "Data Autonomy" mission included where appropriate

---

# Quick Reference: Arkiv in One Page

**Mission:**
Enable Data Autonomy for Everyone

**What it is:**
Data storage protocol built on Ethereum — the Web3 equivalent of traditional Web2 databases — for affordable, queryable blockchain data. Purpose-built to make decentralized applications economically viable.

**Architecture:**
- **L1 (Ethereum)**: Security foundation and settlement
- **L2 (Arkiv Protocol)**: Coordination layer (vanilla OP network)
- **L3 (DB-Chains)**: Where your data lives (modified OP nodes with databases)

**Best for:**
Applications needing queryable, time-limited blockchain data with real-time events and affordable economics.

**Key benefits:**
- Significantly more cost-efficient than typical L2 storage (makes Web3 economically viable)
- Automatic data cleanup (cost efficiency + no bloat)
- SQL-like queries (no separate indexers needed)
- Real-time events (reactive applications)
- Developer-friendly SDKs (Python now, JS/TS & Rust coming)
- Powered by $GLM with multi-token gas support

**Key limitations:**
- All data expires (TTL required, can be extended)
- Network infrastructure decentralizing gradually (sequencers, nodes)
- Entity ownership model (only owner can modify their entities)
- Data size limits (can chunk larger files)
- Not a traditional database replacement
- Block-level latency (not millisecond queries)

**Safe claims:**
✅ Significantly more cost-efficient than typical L2s
✅ Enables Data Autonomy
✅ Permissionless protocol (anyone can store/query)
✅ Owner-controlled entities (true data ownership)
✅ Time-limited blockchain storage
✅ SQL-like query capabilities
✅ Real-time event monitoring
✅ Developer-friendly across languages
✅ No IPFS pinning trust assumptions
✅ Built on Ethereum (L2 with L3 DB-Chains)
✅ Powered by $GLM, multi-token gas
✅ Network on gradual decentralization journey

**Unsafe claims:**
❌ Permanent storage
❌ Fully decentralized network today
❌ Replaces databases
❌ Unlimited storage
❌ Real-time database performance
❌ Free storage
❌ Faster than cloud databases
❌ Anyone can modify any entity (only owners control their entities)

**Elevator pitch:**
"Arkiv enables Data Autonomy for Everyone by making Web3 storage significantly more cost-efficient than typical L2 chains. Built on Ethereum and powered by $GLM, Arkiv is the Web3 database protocol with SQL-like queries, automatic expiration, and real-time events. Build the product you want, not the one gas prices allow."

**Top use cases (see USE_CASES.md):**
- NFT metadata & small images (truly on-chain)
- Gaming state & inventory (real-time updates)
- Social media platforms (decentralized posts)
- DAO governance & proposals (full text on-chain)
- Supply chain tracking (audit trails)
- DeFi analytics & oracles (time-series data)
- AI model versioning (reproducible research)

---

**Remember:** When in doubt, ask! It's better to verify than to make incorrect claims that damage customer trust.
