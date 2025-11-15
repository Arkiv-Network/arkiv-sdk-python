# Arkiv SDK for Typescript / JS

## Commands

### Run voating-board.ts

```shell
npm start
```

### Update SDK

```shell
npm update arkiv-sdk
```

## Files

### package.json

```json
{
  "type": "module",
  "scripts": {
    "start": "tsx voting-board.ts",
    "build": "tsc",
    "dev": "tsx watch voting-board.ts"
  },
  "dependencies": {
    "@arkiv-network/sdk": "^0.4.4",
    "dotenv": "^16.4.5",
    "tslib": "^2.8.1",
    "ethers": "^6.13.4"
  },
  "devDependencies": {
    "tsx": "^4.19.2",
    "typescript": "^5.6.3"
  }
}
```

### tsconfig.json

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true
  },
  "include": ["*.ts"]
}
```

### voting-board.ts

```ts
import { createWalletClient, createPublicClient, http } from '@arkiv-network/sdk';
import { mendoza } from '@arkiv-network/sdk/chains';
import { privateKeyToAccount } from '@arkiv-network/sdk/accounts';
import { eq } from '@arkiv-network/sdk/query';

const PRIVATE_KEY = '0x...';
const MENDOZA_RPC = 'https://mendoza.hoodi.arkiv.network/rpc'

// Suppress SDK debug logs
console.debug = () => {};

function createClients() {
    const walletClient = createWalletClient({
        chain: mendoza,
        transport: http(MENDOZA_RPC),
        account: privateKeyToAccount(PRIVATE_KEY),
    });

    const publicClient = createPublicClient({
        chain: mendoza,
        transport: http(MENDOZA_RPC),
    });

    return { walletClient, publicClient };
}

async function openProposal(walletClient: any, proposalText: string) {
    console.log('Creating proposal entity...');

    const enc = new TextEncoder();
    const { entityKey: proposalKey } = await walletClient.createEntity({
        payload: enc.encode(proposalText),
        contentType: 'text/plain',
        attributes: [
            { key: 'type', value: 'proposal' },
            { key: 'status', value: 'open' },
            { key: 'version', value: '1' },
        ],
        expiresIn: 200, // seconds
    });

    console.log('- Proposal key:', proposalKey);
    return proposalKey;
}

async function castVote(walletClient: any, proposalKey: string, choice: string, weight: string = '1') {
    console.log(`Casting vote "${choice}" for proposal ${proposalKey} ...`);

    const enc = new TextEncoder();
    const voterAddr = walletClient.account.address;

    await walletClient.mutateEntities({
        creates: [
            {
                payload: enc.encode(`vote: ${choice}`),
                contentType: 'text/plain',
                attributes: [
                    { key: 'type', value: 'vote' },
                    { key: 'proposalKey', value: proposalKey },
                    { key: 'voter', value: voterAddr },
                    { key: 'choice', value: choice },
                    { key: 'weight', value: weight },
                ],
                expiresIn: 200,
            },
        ],
    });

    console.log('- Vote cast');
}

async function castVotesBatch(walletClient: any, proposalKey: string, choice: string, count: number) {
    console.log(`Casting ${count} batch votes "${choice}" for proposal ${proposalKey} ...`);

    const enc = new TextEncoder();
    const voterAddr = walletClient.account.address;

    const creates = Array.from({ length: count }, (_, i) => ({
        payload: enc.encode(`vote: ${choice} #${i + 1}`),
        contentType: 'text/plain',
        attributes: [
            { key: 'type', value: 'vote' },
            { key: 'proposalKey', value: proposalKey },
            { key: 'voter', value: `${voterAddr}-bot${i}` },
            { key: 'choice', value: choice },
            { key: 'weight', value: '1' },
        ],
        expiresIn: 200,
    }));

    await walletClient.mutateEntities({ creates });
    console.log(`- Batch created: ${creates.length} votes`);
}

async function tallyVotes(publicClient: any, proposalKey: string) {
    console.log(`Tallying votes for proposal ${proposalKey} ...`);

    const yes = await publicClient
    .buildQuery()
    .where([eq("type", "vote"), eq("proposalKey", proposalKey), eq("choice", "yes")])
    .fetch();

    const no = await publicClient
    .buildQuery()
    .where([eq("type", "vote"), eq("proposalKey", proposalKey), eq("choice", "no")])
    .fetch();

    console.log(`- Tallies - YES: ${yes.entities.length}, NO: ${no.entities.length}`);
    return { yes: yes.entities.length, no: no.entities.length };
}

async function helloWorld() {
    console.log('Doing the hello world ...');

    // 1) Connect your account to Arkiv
    const { walletClient, publicClient } = createClients();

    // 2) Write one small record on-chain
    const enc = new TextEncoder();
    const { entityKey, txHash } = await walletClient.createEntity({
        payload: enc.encode('Hello, Arkiv!'),
        contentType: 'text/plain',
        attributes: [{ key: 'type', value: 'hello' }],
        expiresIn: 120,
    });

    // 3) Read it back and decode to string
    const entity = await publicClient.getEntity(entityKey);
    const data = new TextDecoder().decode(entity.payload);

    // 4) Display results
    console.log('- Key:', entityKey);
    console.log('- Data:', data);
    console.log('- Tx:', txHash);
}

async function main() {
    await helloWorld();

    const { walletClient, publicClient } = createClients();
    const dec = new TextDecoder();

    const stop = await publicClient.subscribeEntityEvents({
        onEntityCreated: async (e) => {
            try {
                const ent = await publicClient.getEntity(e.entityKey);
                const attrs = Object.fromEntries(
                    ent.attributes.map(a => [a.key, a.value])
                );
                const text = dec.decode(ent.payload);

                if (attrs.type === 'vote') {
                    console.log('[Vote created]', text, 'key=', e.entityKey);
                } else if (attrs.type === 'proposal') {
                    console.log('[Proposal created]', text, 'key=', e.entityKey);
                }
            } catch (err) {
                console.error('[onEntityCreated] error:', err);
            }
        },

        onEntityExpiresInExtended: (e) => {
            console.log('[Extended]', e.entityKey, '→', e.newExpirationBlock);
        },

        onError: (err) => console.error('[subscribeEntityEvents] error:', err),
    });

    console.log('Watching for proposal/vote creations and extensions…');

    const proposalKey = await openProposal(
        walletClient,
        'Proposal: Switch stand-up to 9:30?',
    );

    await castVote(
        walletClient,
        proposalKey,
        'no',
    );

    const numberOfVotes = 5;
    await castVotesBatch(
        walletClient,
        proposalKey,
        'yes',
        numberOfVotes,
    );

    await tallyVotes(publicClient, proposalKey);
}

// Run the main function
main().catch(console.error);
```
