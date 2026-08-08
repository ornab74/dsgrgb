# DysonSphereGamma HyperCommunication v21

This branch is a ground-up rearchitecture of `dsgrgb` into a bounded multi-agent runtime with an optional encrypted semantic-memory layer.

The five historical channels remain, but they now have explicit software responsibilities:

- **Red** — adversarial analysis and credible failure modes.
- **Green** — constructive design and recovery paths.
- **Blue** — verification, provenance, and structured challenges.
- **Gamma** — cross-domain dependencies and second-order coupling.
- **Sync** — final arbitration over an immutable bounded transcript.

The RGB/Gamma terminology is an information-routing metaphor. It is not a claim of physical quantum, nonlocal, remote, or future sensing.

## What v21 changes

The old runtime mixed routing, prompts, state, trust, tracing, and secure memory across a large script and wrappers. v21 separates them into a package:

```text
dsghyper/
  config.py      environment parsing and bounded configuration
  protocol.py    immutable agent result/claim/challenge/note schemas
  model.py       bounded HTTP model transport
  ledger.py      per-trace tamper-evident hash chain
  memory.py      PCESM encrypted semantic vector memory
  runtime.py     deterministic bounded orchestration
  cli.py         standard + secure CLI
```

Compatibility entry points remain:

```text
main.py
secure_main.py
```

### Communication model

v21 deliberately removes recursive peer-agent execution from the core. A worker may emit a peer note, but that note is an **immutable artifact for the next round**, not an immediate model call.

```text
                        ┌──── Red ────┐
User task ── Round 1 ───┼──── Green ──┼── immutable results
                        ├──── Blue ───┤         │
                        └──── Gamma ──┘         ▼
                                          peer-note router
                                                │
                        ┌──── Red ────┐         ▼
             Round 2 ───┼──── Green ──┼── immutable results
                        ├──── Blue ───┤
                        └──── Gamma ──┘
                                                │
                                                ▼
                                         Sync arbitration
```

This fixes the previous race where a peer note could re-enter `HyperAgent.handle()` and overwrite an already-completed round result.

Other changes include structured challenge targets instead of string-search trust updates, explicit round timeouts, per-result failure states, bounded context serialization, a fixed model-call graph, and a per-trace ledger that verifies its own chain after a run.

## PCESM: Proof-Carrying Encrypted Semantic Mesh v2

Secure mode uses **PCESM**, an architecture composed from established cryptographic primitives. PCESM is not itself a new cryptographic primitive and does not claim to supersede homomorphic encryption mathematically.

PCESM combines:

- AES-256-GCM sealed memory payloads and metadata;
- HKDF-SHA256 domain-separated subkeys;
- HMAC-SHA256 keyed blind feature sketches for vector candidate routing;
- signed capability tokens with subject, namespace, operations, audience, expiry, result limits, and revocation;
- record commitments that are **recomputed from the stored fields** before HMAC attestation verification;
- pseudonymous owner identifiers;
- encrypted SQLite persistence by default;
- optional Weaviate storage of opaque records and blind vectors;
- optional CKKS encrypted-embedding reranking through TenSEAL.

### Important privacy boundary

Blind feature sketches are not ORAM and are not zero-knowledge search. The vector backend can still observe access timing, namespace labels, result counts, and similarity/access patterns. The README and runtime status therefore report:

```text
access_pattern_hiding = false
```

That distinction is intentional.

### CKKS behavior

CKKS is optional and is never silently substituted with AES.

If `DSG_ENABLE_CKKS=1` and TenSEAL is unavailable, runtime status reports HE disabled. If TenSEAL is available but persistent serialized contexts are not supplied, the generated CKKS context is session-only and CKKS ciphertext is not written into a persistent vector backend.

For persistent HE records, supply both:

```text
DSG_CKKS_PUBLIC_CONTEXT_B64
DSG_CKKS_SECRET_CONTEXT_B64
```

The stored vector candidate-routing sketch and CKKS ciphertext serve different purposes: the keyed sketch selects a bounded candidate set; CKKS can rerank embeddings without decrypting stored embedding vectors during the arithmetic operation.

## Secure-memory failure behavior

Secure mode no longer creates unrecoverable persistent ciphertext by default.

A persistent secure run requires `DSG_MEMORY_MASTER_KEY`. Generate one, for example:

```bash
python - <<'PY'
import base64, secrets
print("b64:" + base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("="))
PY
```

Then export it:

```bash
export DSG_MEMORY_MASTER_KEY='b64:...'
```

For development-only process-local memory, explicitly opt in:

```bash
export DSG_ALLOW_EPHEMERAL_MEMORY=1
```

Ephemeral mode uses an in-memory vector backend and never writes ciphertext that cannot be reopened after restart.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Standard mode:

```bash
python main.py --rounds 2 "Design and audit a resilient agent system"
```

Secure PCESM mode:

```bash
export DSG_MEMORY_MASTER_KEY='b64:YOUR_GENERATED_KEY'
python main.py --secure --rounds 2 "Design and audit a resilient agent system"
```

The compatibility secure entry point also works:

```bash
python secure_main.py "Review the architecture"
```

Without `OPENAI_API_KEY`, the orchestration and security plumbing run in a deterministic local fallback mode without remote inference.

## Vector backends

If `WEAVIATE_URL` is unset, secure mode uses persistent encrypted SQLite at:

```text
outputs/secure_memory.sqlite3
```

If `WEAVIATE_URL` is configured, PCESM uses Weaviate and performs namespace filtering in the vector query itself instead of retrieving cross-namespace candidates and filtering them afterward. If Weaviate initialization fails, the runtime records a warning and falls back to encrypted SQLite.

## Trace integrity

Each request receives its own ledger file:

```text
outputs/traces/<trace-id>.jsonl
```

Each record commits to the previous record hash. Only hashes and bounded routing metadata are written; raw model prompts/results are not copied into the ledger. The chain is verified at the end of every run. This provides tamper evidence, not hardware-backed immutability.

Set:

```text
DSG_REQUIRE_LEDGER=1
```

if a trace-persistence failure should fail the run rather than degrade to in-memory accounting.

## Tests

```bash
python -m py_compile main.py secure_main.py dsghyper/*.py tests/*.py
python -m unittest discover -s tests -v
```

The v21 suite covers:

- encrypted-memory round trip;
- full record-commitment recomputation;
- ciphertext tamper rejection;
- capability scope enforcement;
- capability revocation and expiry;
- SQLite encrypted-memory persistence across restart with the same master key;
- structured protocol bounds;
- fixed worker call graph with no recursive peer calls;
- per-trace ledger verification;
- explicit secure ephemeral mode.

## Deliberately deferred to the next agent-communication iteration

The current rework establishes a stable base before increasing agent autonomy. Good next-stage research targets include threshold-decryption identities, post-quantum authenticated peer identities, policy-carrying messages, explicit information-budget negotiation, zero-knowledge authorization proofs, mixnet/ORAM-style access-pattern defenses, multi-model quorum arbitration, and causal credit assignment across long agent conversations.

Those features are **not** claimed to be implemented in v21.

## Legacy artifact policy

The old monolithic simulator source, stale SHA-256 manifest, and historical DOCX builder are removed from this rearchitecture branch. Their history remains recoverable through Git. Static `paper/`, `outputs/`, and `prompts/` research artifacts may remain for provenance, but they are not imported or executed by v21.
