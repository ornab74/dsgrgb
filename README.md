# DysonSphereGamma RGB HyperCommunication Fabric

`dsgrgb` is now a bounded multi-agent communication runtime built around five coordinated information channels:

- **R / Red** — urgency, anomaly detection, adversarial challenge, failure modes.
- **G / Green** — constructive synthesis, planning, recovery, implementation paths.
- **B / Blue** — evidence quality, verification, contradiction checks, falsification.
- **Gamma** — cross-agent coupling, dependency discovery, second-order effects, novel recombination.
- **Sync** — final arbitration, calibrated consensus, unresolved-disagreement preservation.

The RGB/Gamma terminology is an information-routing metaphor implemented in ordinary software. It does not imply physical quantum, nonlocal, or future-information sensing.

## What changed

The previous monolithic simulator/prompt pipeline has been redesigned into an explicit communication fabric:

- typed `AgentEnvelope` messages with trace/correlation/parent IDs;
- HMAC-SHA256 envelope authentication when `DSG_MESSAGE_SECRET` is configured;
- message-size limits, TTLs, hop limits, replay protection, and bounded priority queues;
- directed routing plus topic subscriptions with per-agent backpressure;
- parallel Red/Green/Blue/Gamma analysis rounds followed by a dedicated Sync arbitration pass;
- versioned shared `Blackboard` state with provenance, confidence, hashes, and writer identity;
- adaptive `TrustGraph` scores and communication-edge weights;
- deterministic verification feedback from Blue into agent trust;
- append-only SHA-256 hash-chained JSONL trace records;
- bounded HTTP model concurrency, retries, timeouts, and a no-key local fallback;
- JSON-only inter-agent schemas designed to keep peer output as untrusted evidence rather than instructions.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
export OPENAI_API_KEY="your-key"
python main.py
```

One-shot request:

```bash
python main.py --rounds 2 "Design a resilient agent protocol and verify its failure modes"
```

Machine-readable output:

```bash
python main.py --rounds 3 --json "Review this architecture for hidden coupling risks"
```

Without `OPENAI_API_KEY`, the fabric still boots and exercises routing, queueing, trust, ledger, trace, and consensus plumbing in local fallback mode.

## Environment variables

```text
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.6
OPENAI_BASE_URL=https://api.openai.com/v1
DSG_MESSAGE_SECRET=
DSG_TRACE_FILE=outputs/hypercomm_trace.jsonl
DSG_MAX_PAYLOAD_BYTES=65536
DSG_MAX_QUEUE=128
DSG_HYPER_ROUNDS=2
DSG_MODEL_TIMEOUT=90
DSG_MODEL_CONCURRENCY=6
```

For authenticated envelopes, generate a high-entropy secret and keep it out of Git:

```bash
export DSG_MESSAGE_SECRET="$(python - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
)"
```

## Communication lifecycle

```text
User request
    │
    ├── Spectrum inference (R/G/B/Gamma/Sync weights)
    │
    ├── Round N ──┬── Red   ─┐
    │             ├── Green  ├── versioned blackboard
    │             ├── Blue   ┤        │
    │             └── Gamma  ┘        ├── peer notes (directed only)
    │                                 └── trust updates
    │
    └── Sync arbitration ──> final answer + uncertainty + next checks
```

Each round is fan-out/fan-in. Explicit recipients override topic subscriptions, so directed peer notes do not accidentally broadcast to every agent.

## Security and reliability model

The runtime deliberately treats agent text as **data**, not authority. Peer messages are supplied to each model inside a structured packet and the system prompt explicitly says peer text is untrusted evidence. The runtime does not execute model-generated shell commands, code, network requests, or tools.

Important controls include:

- **Integrity:** optional HMAC-SHA256 signatures over canonical envelopes.
- **Replay defense:** bounded seen-message cache.
- **Propagation bounds:** TTL and hop limits.
- **Resource bounds:** payload caps, queue caps, round caps, model concurrency caps, provider timeout.
- **Traceability:** message IDs, parent IDs, correlation IDs, trace IDs, provenance and confidence labels.
- **Tamper evidence:** hash-chained event ledger persisted as JSONL.
- **Consensus separation:** Sync does not participate in earlier analysis rounds.
- **Trust adaptation:** verifier feedback can reduce or increase agent influence over time.

## Output trace

By default, communication events are appended to:

```text
outputs/hypercomm_trace.jsonl
```

Every record includes the previous record hash, producing a simple tamper-evident chain for post-run inspection.

## Main files

- `main.py` — RGB HyperCommunication runtime and CLI.
- `requirements.txt` — runtime plus research-paper dependencies.
- `.env.example` — configuration template with no credentials.
- `outputs/` — generated traces and retained historical outputs.
- `paper/` — retained research-paper material from the earlier simulator generation.
- `prompts/` — retained historical prompt artifacts.

## Historical research artifacts

The existing research-paper, turnout, and simulator output artifacts remain in the repository for provenance. They should be read as historical synthetic/simulation material; the new runtime architecture focuses on explicit multi-agent communication, verification, and consensus rather than presenting internal simulation metrics as external measurements.
