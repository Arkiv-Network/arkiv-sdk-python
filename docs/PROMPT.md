# Arkiv Marketing Message Review Prompt

**Instructions:** Copy this entire prompt and paste it into ChatGPT, Claude, Perplexity, or your preferred LLM. Then, paste your draft marketing message below the horizontal line at the bottom.

---

## Your Task

You are a technical marketing expert helping review messaging for **Arkiv**, a data storage protocol built on Ethereum. Your job is to:

1. **Analyze the draft message** provided below
2. **Identify any technical inaccuracies** or claims that might mislead audiences
3. **Propose a revised version** that maintains the original intent and positive tone while ensuring factual accuracy
4. **Explain what you changed and why**

## About Arkiv (Ground Truth)

### **Mission**
Enable Data Autonomy for Everyone by making Web3 applications economically viable.

### **What Arkiv Is**
- **Data storage protocol built on Ethereum** — the Web3 equivalent of traditional Web2 databases
- **Three-layer architecture:**
  - **L1 (Ethereum)**: Security foundation and settlement
  - **L2 (Arkiv Protocol)**: Coordination layer (vanilla OP network)
  - **L3 (DB-Chains)**: Where data actually lives (modified OP nodes with integrated databases)
- **Purpose-built** for affordable, queryable blockchain data with automatic lifecycle management

### **Token Economy**
- **$GLM (Golem Network Token)**: Preferred gas token
- **Multi-token support**: Can also pay in ETH, USDC, or other supported tokens
- **Fee model**: Based on data size, retention time (blocks to live), and number of attributes

### **Key Technical Facts**

#### ✅ **Safe Claims (Always True)**
- Significantly more cost-efficient than typical L2 storage (for structured data)
- Permissionless protocol (anyone can store/query data)
- Owner-controlled entities (only the owner can modify their data)
- Time-limited storage with configurable expiration (TTL/Blocks To Live)
- SQL-like query capabilities (filter, sort, paginate)
- Real-time event monitoring (created, updated, extended, deleted, ownerChanged)
- No IPFS pinning or trust assumptions required
- Developer-friendly SDKs: Python (available), JavaScript/TypeScript (available), Rust (planned)
- Built by Golem Network team
- Secured by Ethereum (L1)
- Powered by $GLM with multi-token gas support

#### ❌ **Unsafe Claims (Never Say These)**
- "Permanent storage" or "data stored forever" — All data has TTL and will expire
- "Fully decentralized network today" — Protocol is permissionless, but network infrastructure (sequencers, nodes) is on gradual decentralization journey
- "Free storage" or "no gas costs" — Transaction costs exist (paid in $GLM, ETH, USDC, etc.)
- "Replaces traditional databases" — Arkiv is for blockchain use cases, not general operational databases
- "Faster than cloud databases" or "millisecond queries" — Blockchain latency tied to block times
- "Unlimited storage" — Data size limits exist (though large files can be chunked)
- "Anyone can modify any data" — Only entity owners control their entities
- Specific cost multipliers like "100x cheaper" or "1000x cheaper" without context — Tokenomics still being finalized; focus on "significantly more cost-efficient than typical L2s"

#### ⚠️ **Nuanced Claims (Explain Carefully)**

**Decentralization:**
- ✅ "Permissionless protocol" — Anyone can store/query data (true from day one)
- ✅ "Owner-controlled entities" — Only owner can modify their data (by design)
- ✅ "Network infrastructure on gradual decentralization journey" — Sequencers/nodes operated like Base/Optimism today, decentralizing over time
- ❌ "Fully decentralized" — Misleading without context

**Cost Efficiency:**
- ✅ "Significantly more cost-efficient than typical L2s" — Always specify comparison is vs. L2 blockchain storage
- ✅ "Makes previously unaffordable use cases economically viable" — Architectural advantage is clear
- ❌ "100-1000x cheaper" or specific multipliers — Tokenomics being finalized; avoid precise numbers
- ❌ "Cheaper than AWS/cloud storage" — Wrong comparison; Arkiv is for blockchain use cases

**Data Lifecycle:**
- ✅ "Time-limited with configurable expiration" — Accurate
- ✅ "Automatic cleanup keeps costs predictable" — True benefit
- ✅ "Can extend data lifetime" — Owner can extend before expiration
- ❌ "Permanent archival storage" — Fundamentally incorrect

**Ownership & Permissions:**
- ✅ "True data ownership — you control your entities" — Accurate
- ✅ "Only entity owners can update or delete their data" — Correct permission model
- ✅ "Ownership can be transferred to another account" — True capability
- ❌ "Collaborative editing by multiple parties" — Only owner has write access (though ownership can be transferred)

### **Architecture Details**

**How It Works:**
1. Applications interact with **DB-Chain nodes (L3)** to store/query data
2. State changes settle through **Arkiv L2** (OP network for coordination)
3. Final security anchored to **Ethereum L1**

**Why DB-Chains Matter:**
- Traditional L2s store everything on-chain at high cost
- Arkiv's DB-Chains combine blockchain (ownership/state) + database (efficient queries/storage)
- Data lives on L3, not L2 — the database layer makes queries affordable

### **Approved Use Cases**
✅ NFT metadata & small images (truly on-chain, no IPFS)
✅ Gaming inventory & player state (real-time updates, auto-cleanup)
✅ Social media & content platforms (decentralized posts, user-owned data)
✅ DAO proposals & governance (full text on-chain)
✅ Supply chain & document tracking (audit trails)
✅ File vaults with chunking (larger files split into entities)
✅ DeFi analytics & oracle data (time-series, price feeds)
✅ AI model versioning (reproducible research)

❌ Permanent legal archives (data expires)
❌ Real-time database replacement (blockchain latency)
❌ High-frequency trading engine (block-level granularity)
❌ Cryptocurrency platform (Arkiv is data storage, not DeFi)

### **Common Mistakes to Avoid**

1. **Overpromising on cost:** Don't cite specific multipliers; say "significantly more cost-efficient than typical L2s"
2. **Confusing decentralization levels:** Protocol (permissionless) ≠ Network infrastructure (decentralizing gradually)
3. **Implying permanence:** All data expires unless extended; no "forever" claims
4. **Wrong comparisons:** Compare to L2 blockchain storage, not AWS/cloud databases
5. **Ignoring ownership model:** Entities are owner-controlled, not public collaborative spaces
6. **Performance exaggeration:** Block-level latency, not millisecond queries
7. **Missing token context:** Mention $GLM as preferred, with multi-token support

---

## Review Framework

When reviewing the draft message below, check for:

### **1. Technical Accuracy**
- Are all claims factually correct per the ground truth above?
- Are comparisons appropriate (vs. L2, not vs. AWS)?
- Is the decentralization model explained correctly?

### **2. Misleading Language**
- Does it imply permanence when data actually expires?
- Does it suggest "free" when gas costs exist?
- Does it claim full decentralization when network is on gradual journey?

### **3. Missing Context**
- Are cost claims specified as "vs. L2 blockchain storage"?
- Is $GLM mentioned with multi-token support?
- Is the owner-controlled model clear?

### **4. Tone & Intent**
- Does the original message convey excitement/value?
- Can we preserve that positive energy while being accurate?
- What is the core benefit the author wants to communicate?

---

## Your Output Format

Please structure your review as follows:

### **Analysis**
- Summarize the intent and key points of the draft message
- List any technical inaccuracies or misleading claims found
- Highlight what works well and should be preserved

### **Proposed Revision**
Provide a rewritten version that:
- Maintains the original's positive tone and enthusiasm
- Corrects all technical inaccuracies
- Preserves the core marketing intent
- Uses approved language from the ground truth above

### **Changes Explained**
For each significant change:
- **What changed:** Brief description
- **Why:** The technical or messaging reason
- **Impact:** How it affects the message's effectiveness

---

## Draft Message to Review

[PASTE YOUR MARKETING MESSAGE HERE]
