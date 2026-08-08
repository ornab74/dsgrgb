# DysonSphereGamma HyperCommunication v23

`dsgrgb` is a bounded multi-agent runtime with selective epistemic routing, an explicit **Agent Information Economy**, and an optional encrypted semantic-memory layer.

The five historical channels remain as software roles:

- **Red** — adversarial analysis and credible failure modes.
- **Green** — constructive design and recovery paths.
- **Blue** — verification, provenance, and structured challenges.
- **Gamma** — cross-domain dependencies and second-order coupling.
- **Sync** — final arbitration over the bounded epistemic graph.

The RGB/Gamma terminology is an information-routing metaphor. It is not a claim of physical quantum, nonlocal, remote, or future sensing.

## v23: Agent Information Economy

v22 introduced the Selective Epistemic Mesh. v23 makes communication capacity an explicit allocatable resource and adds research-grade communication-analysis primitives around that mesh.

Operational v23 mechanisms include:

- claim freshness decay and hard round-based expiration;
- deterministic information-market allocation under hard token budgets;
- claim-level structural causal-credit propagation over explicit graph edges;
- deterministic replay snapshots and counterfactual market evaluation;
- proof-carrying HMAC policy envelopes with payload binding, audience, purpose, operation, expiry, and nonce replay checks;
- bounded specialist planning plus **opt-in** conflict-specialist execution under count/token/time quotas;
- bounded multi-model quorum cells over explicitly configured model IDs;
- explicit capability reporting for threshold authentication, post-quantum identity, ORAM, PIR, and zero-knowledge authorization.

The advanced cryptographic/privacy capabilities are **not reported active unless a real backend is registered**. The default runtime does not claim threshold signatures, post-quantum transport authentication, ORAM, PIR, or ZK authorization.

## Communication path

```text
User task
   │
   ▼
Round 1: Red / Green / Blue / Gamma
   │
   ├── immutable claims
   ├── evidence references
   ├── challenge edges
   ├── support/dependency edges
   └── targeted information requests
   │
   ▼
Selective Epistemic Mesh
   │
   ├── global claim identities
   ├── targeted role routing
   └── contested/dependency bookkeeping
   │
   ▼
Freshness gate
   │
   ├── decay stale evidence
   └── expire claims past TTL
   │
   ▼
Information Market
   │
   ├── utility
   ├── confidence
   ├── salience
   ├── freshness
   └── estimated token cost
   │
   ▼
Role-specific winning communication packet
   │
   ▼
Round 2..N
   │
   ▼
Conflict specialist planner / optional executor
   │
   ▼
Sync arbitration
   │
   ├── claim graph summary
   ├── causal-credit diagnostics
   ├── specialist evidence
   ├── optional multi-model quorum cell
   └── policy envelope verification
   │
   ▼
Final answer + replay/counterfactual metadata
```

`recursive_peer_calls` remains `0` and `full_prior_round_broadcast` remains `false`.

## Claim-level causal credit

`dsghyper.research.CausalCreditEngine` propagates bounded structural credit backward through explicit graph edges such as:

- `supports`
- `refines`
- `depends_on`
- `contradicts`
- `challenges`

This is **communication-graph attribution**, not proof of real-world causality. Runtime output names the mode accordingly:

```text
bounded-graph-structural-credit-not-real-world-causality
```

The engine is cycle-bounded, depth-bounded, and decay-weighted.

## Evidence freshness and expiration

Freshness is controlled with:

```text
DSG_FRESHNESS_TTL_ROUNDS=4
DSG_FRESHNESS_HALF_LIFE_ROUNDS=2.0
```

A claim older than the TTL is not allowed to enter the information market. Claims inside the TTL receive a deterministic exponential freshness score.

## Information-market allocation

Each candidate communication artifact becomes a `MarketBid` containing:

- sender and recipient;
- globally addressed claim/artifact ID;
- utility;
- confidence;
- salience;
- freshness;
- estimated token cost.

The deterministic market ranks benefit relative to cost and admits winners until the recipient's token budget is exhausted.

Configure the hard per-recipient/per-round budget with:

```text
DSG_MARKET_TOKEN_BUDGET=4500
```

The runtime records allocation digests, tokens used, winning bid IDs, and rejected bid IDs in the tamper-evident ledger.

## Conflict-focused specialists

The `SpecialistScheduler` creates bounded plans only for sufficiently contested claims. Default behavior is **plan-only** so v23 does not silently increase model cost.

```text
DSG_SPECIALIST_LIMIT=2
DSG_SPECIALIST_TOKEN_QUOTA=3000
DSG_EXECUTE_SPECIALISTS=0
```

To opt in to specialist execution:

```bash
export DSG_EXECUTE_SPECIALISTS=1
```

`SpecialistExecutor` then enforces:

- maximum specialist count;
- total output-token reservation;
- per-specialist token cap;
- per-specialist timeout;
- advisory-only results that do not replace Red/Green/Blue/Gamma worker state.

## Multi-model quorum cells

Additional compatible model IDs may be configured with:

```text
DSG_QUORUM_MODELS=model-a,model-b,model-c
```

When an API key is configured, `QuorumCell` sends the same bounded Sync packet independently to those models with model-count, timeout, and token caps.

The runtime reports:

- each model result digest;
- answer fingerprints;
- response diversity;
- mean confidence;
- status counts;
- quorum digest.

It deliberately reports:

```text
truth_probability = null
```

Agreement is diagnostic bookkeeping, not proof and not a truth probability. The primary Sync result remains the user-facing answer unless a future explicit adjudication policy says otherwise.

## Proof-carrying policy messages

If configured:

```text
DSG_POLICY_AUTH_KEY=
```

v23 can attach an HMAC-authenticated policy envelope to the Sync packet. The envelope binds:

- sender;
- audience;
- purpose;
- allowed operations;
- payload digest;
- issued/expiry times;
- nonce;
- policy digest;
- HMAC authenticator.

This protects integrity/authenticity under the shared policy key. It is **not zero knowledge**, **not threshold authentication**, and **not post-quantum authentication**.

## Deterministic replay and counterfactual communication evaluation

Every completed run can emit a deterministic replay snapshot over:

- request digest;
- epistemic mesh digest;
- influence digest;
- information-market allocation digests;
- final result digest.

Configure counterfactual market budgets with:

```text
DSG_COUNTERFACTUAL_BUDGETS=1024,2048,4096
```

The replay engine reruns the deterministic allocation policy over the same recorded bids and reports which artifacts would have won under each budget. It does not re-contact models and therefore isolates communication-policy effects from model nondeterminism.

## Advanced security capability surface

The runtime exposes explicit status entries for:

- `threshold_authenticated_identity`
- `post_quantum_transport_identity`
- `oram_access_pattern_hiding`
- `pir_private_retrieval`
- `zero_knowledge_authorization`

Default state is intentionally:

```text
implemented = false
active = false
```

until a vetted backend is integrated and registered. This prevents architecture names from being mistaken for cryptographic guarantees.

## Package architecture

```text
dsghyper/
  config.py      runtime, memory, and v23 research configuration
  protocol.py    immutable claims, relations, challenges, requests and notes
  epistemic.py   selective claim graph and bounded routing
  research.py    freshness, markets, causal credit, replay, policy/security surface
  cells.py       bounded specialist and multi-model quorum execution cells
  model.py       bounded HTTP model transport with per-call model/token overrides
  ledger.py      per-trace tamper-evident hash chain
  memory.py      PCESM encrypted semantic vector memory
  runtime.py     v23 orchestration integration
  cli.py         standard + secure CLI
```

Compatibility entry points:

```text
main.py
secure_main.py
```

## Secure memory: PCESM

Secure mode continues to use **PCESM — Proof-Carrying Encrypted Semantic Mesh**, an architecture composed from established primitives:

- AES-256-GCM sealed payloads;
- HKDF-SHA256 domain-separated subkeys;
- HMAC-SHA256 keyed blind feature sketches;
- scoped, expiring, revocable capabilities;
- recomputed SHA-256 record commitments plus HMAC attestations;
- pseudonymous owner IDs;
- encrypted SQLite persistence;
- optional Weaviate opaque-vector storage;
- optional CKKS reranking through TenSEAL.

PCESM is not itself a new cryptographic primitive.

### Privacy boundary

Blind feature sketches are not ORAM, PIR, or zero-knowledge search. Backends may still observe timing, namespace labels, result counts, and access/similarity patterns.

Runtime status therefore does not claim access-pattern hiding.

CKKS is optional and never silently replaced by AES or ordinary vector search.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
cp .env.example .env
```

Standard mode:

```bash
python main.py --rounds 3 "Design and verify a resilient agent communication system"
```

Secure mode:

```bash
export DSG_MEMORY_MASTER_KEY='b64:YOUR_GENERATED_KEY'
python main.py --secure --rounds 3 "Design and verify a resilient agent communication system"
```

Without `OPENAI_API_KEY`, orchestration and security plumbing run in deterministic local fallback mode without remote model inference. Quorum model IDs are not activated by the main runtime when no API key is configured.

## Tests

```bash
python -m compileall -q main.py secure_main.py dsghyper tests
python -m unittest discover -s tests -v
```

The suite covers v21/v22 guarantees plus v23 behavior:

- encrypted-memory persistence and tamper rejection;
- capability scope, expiry, and revocation;
- per-trace ledger verification;
- global claim identities and targeted challenge resolution;
- no recursive peer calls or full previous-round broadcast;
- freshness decay and expiration;
- deterministic budget-bounded information-market allocation;
- bounded structural causal-credit propagation;
- HMAC policy-envelope payload binding and nonce replay rejection;
- specialist hard quotas and explicit opt-in execution;
- multi-model quorum diagnostic behavior;
- advanced security features default inactive when no backend exists;
- deterministic replay/counterfactual market primitives.

GitHub Actions runs compile, unit tests, standard fallback smoke, secure-ephemeral smoke, and specialist opt-in fallback smoke on Python 3.10 and 3.12.

## Research roadmap beyond v23

The next credible steps are deeper implementations rather than names alone:

1. integrate a vetted threshold-signature library and real M-of-N peer authentication;
2. add hybrid classical + ML-DSA / ML-KEM authenticated transport identities using a maintained cryptographic backend;
3. evaluate concrete ORAM or PIR libraries for memory retrieval with fixed-size request/result envelopes;
4. implement zero-knowledge authorization only with a real proving/verifying system and explicit circuit/policy semantics;
5. add persistent replay corpora and offline communication-policy benchmarks;
6. measure specialist/quorum information gain against token cost instead of assuming extra agents help;
7. add multi-provider quorum adapters so independent models need not share one API endpoint or provider.

Those are future work and are not claimed by v23 unless their capability status explicitly reports `implemented=true` and `active=true`.
