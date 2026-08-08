# DysonSphereGamma HyperCommunication v22

`dsgrgb` is now a bounded multi-agent runtime with selective epistemic routing and an optional encrypted semantic-memory layer.

The five historical channels remain as software roles:

- **Red** — adversarial analysis and credible failure modes.
- **Green** — constructive design and recovery paths.
- **Blue** — verification, provenance, and structured challenges.
- **Gamma** — cross-domain dependencies and second-order coupling.
- **Sync** — final arbitration over the bounded epistemic graph.

The RGB/Gamma terminology is an information-routing metaphor. It is not a claim of physical quantum, nonlocal, remote, or future sensing.

## v22: Selective Epistemic Mesh

v21 removed recursive peer-agent execution. v22 goes further: workers no longer receive a broadcast copy of the complete previous-round transcript.

Each round produces immutable artifacts:

- atomic claims with confidence, salience, provenance, and evidence;
- explicit claim relationships: `supports`, `contradicts`, `depends_on`, `refines`, `duplicates`;
- targeted challenges against specific agent/claim identifiers;
- targeted information requests with estimated utility;
- small peer notes for the next bounded round only.

The new `dsghyper/epistemic.py` builds globally addressable claim IDs such as:

```text
r2:blue:claim_4
```

and converts those artifacts into a deterministic claim graph.

### Communication path

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
Epistemic Mesh
   │
   ├── resolve global claim identities
   ├── discard unresolved reputation challenges
   ├── compute bounded communication priorities
   ├── enforce claim / character / request budgets
   └── create role-specific next-round packets
   │
   ▼
Round 2..N: selective role-specific context
   │
   ▼
Sync receives compact graph + contested claims + unresolved requests
```

`full_prior_round_broadcast` is explicitly reported as `false`.

## Communication budgets

The mesh enforces deterministic limits rather than letting agent communication grow without bound. The default budget currently limits:

- claims delivered per worker;
- total routed claim characters;
- targeted information requests;
- peer notes and peer-note characters;
- total claims exposed to Sync.

Dropped-by-budget artifacts are counted in runtime metrics.

This makes communication capacity a controlled resource rather than an accidental function of how verbose agents become.

## Quorum bookkeeping is not truth

For each claim, the mesh derives bookkeeping values including:

- weighted support mass;
- weighted challenge mass;
- support fraction;
- reviewer diversity;
- dependency count;
- supporters and challengers;
- status: `weak`, `provisional`, `cross_supported`, or `contested`.

These values are **not truth probabilities**. Agreement does not make a claim true, and disagreement does not make it false. Sync is explicitly instructed to preserve materially contested claims and missing information.

## Influence safety

Agent influence is a bounded reliability heuristic, not a truth score.

A challenge affects influence only when the Epistemic Mesh can resolve the referenced claim to the stated target agent. Invalid, ambiguous, or missing claim references are counted as unresolved and have no influence effect.

This closes a class of reputation-poisoning errors where arbitrary claim IDs could previously lower another agent's score.

## Package architecture

```text
dsghyper/
  config.py      environment parsing and bounded configuration
  protocol.py    immutable claims, relations, challenges, requests and notes
  epistemic.py   claim graph, selective routing, budgets and quorum bookkeeping
  model.py       bounded HTTP model transport
  ledger.py      per-trace tamper-evident hash chain
  memory.py      PCESM encrypted semantic vector memory
  runtime.py     bounded orchestration + selective mesh integration
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

Runtime status therefore reports:

```text
access_pattern_hiding = false
```

CKKS is optional and never silently replaced by AES or ordinary vector search.

## Secure-memory behavior

Persistent secure mode requires:

```text
DSG_MEMORY_MASTER_KEY
```

Generate one:

```bash
python - <<'PY'
import base64, secrets
print("b64:" + base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("="))
PY
```

Development-only process-local memory requires explicit opt-in:

```bash
export DSG_ALLOW_EPHEMERAL_MEMORY=1
```

Ephemeral mode uses an in-memory backend and does not write unrecoverable ciphertext.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
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

Without `OPENAI_API_KEY`, orchestration and security plumbing run in deterministic local fallback mode without remote model inference.

## Trace integrity

Each request gets its own ledger:

```text
outputs/traces/<trace-id>.jsonl
```

Every record commits to the previous hash. The chain is verified after the run. This is tamper evidence, not hardware-backed immutability.

## Tests

```bash
python -m compileall -q main.py secure_main.py dsghyper tests
python -m unittest discover -s tests -v
```

The suite now covers the v21 security/runtime cases plus v22 communication properties:

- global claim identities;
- targeted challenge resolution;
- unresolved challenges cannot affect reputation;
- selective routing respects claim budgets;
- information requests reach only intended roles;
- quorum bookkeeping never emits Boolean truth flags;
- no recursive peer calls;
- no full previous-round broadcast;
- encrypted-memory persistence and tamper rejection;
- capability scope, expiry, and revocation;
- per-trace ledger verification.

GitHub Actions runs compile, unit tests, standard fallback smoke, and secure-ephemeral smoke on Python 3.10 and 3.12.

## Next communication research layer

v22 provides a stable base for a later iteration with substantially stronger communication semantics, such as:

- claim-level causal credit assignment;
- evidence freshness and expiration;
- explicit information-market bidding under token budgets;
- multi-model quorum cells;
- conflict-focused specialist spawning with hard quotas;
- proof-carrying policy/capability messages;
- threshold-authenticated peer identities;
- post-quantum authenticated transport identities;
- privacy-preserving routing with ORAM/PIR-style access-pattern defenses;
- zero-knowledge authorization proofs;
- deterministic replay and counterfactual communication evaluation.

Those are research directions, not claims about current v22 behavior.
