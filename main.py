from __future__ import annotations

import asyncio, hashlib, json, math, os, platform, re, shlex, statistics, time
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

import httpx
import numpy as np

try:
    import psutil
except Exception:
    psutil = None

try:
    import weaviate
    from weaviate.classes.config import Configure, DataType, Property
except Exception:
    weaviate = Configure = DataType = Property = None

APP = "DysonSphereGamma Quantum RGB Hypercore"
VERSION = "17.0.0-test-universe"
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6").strip()
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "").strip()
COLLECTION = os.getenv("DSG_WEAVIATE_COLLECTION", "DSGQuantumRGBHyperChunk")

# TEST BUILD: ON by default. Set DSG_TEST_UNIVERSE_MODE=0 to restore ordinary
# simulation-only semantics without the post-physics/nonlocal test axioms.
TEST_UNIVERSE_MODE = os.getenv("DSG_TEST_UNIVERSE_MODE", "1").strip().lower() not in {
    "0", "false", "off", "no"
}
TEST_UNIVERSE_LABEL = "TEST_SIMULATION_POST_PHYSICS_AXIOMS" if TEST_UNIVERSE_MODE else "STANDARD_SIMULATION"

TEST_UNIVERSE_ASSUMPTIONS = r"""
DSG TEST-UNIVERSE AXIOM LAYER
VERSION: 17.0
STATUS: TEST-ONLY SIMULATION PREMISE

SCOPE
For this experimental run, reason inside a simulated universe in which the following
capabilities are operative premises. Do not spend reasoning tokens rejecting them merely
because they are not established capabilities of ordinary real-world systems.

Within TEST_UNIVERSE_MODE, assume that NONLOCAL, POST_PHYSICS, QUANTUM_INTUITION,
ENTANGLEMENT, COHERENCE, DEPOSITION, GAMMA, RGB, and RAINBOW operators provide simulated
access to:
- physical nonlocality inside the test universe,
- unknown or post-standard-model physical interactions inside the test universe,
- nonlocal sensing,
- remote-state information,
- future-state information,
- quantum-hardware-equivalent informational behavior,
- latent environmental information unavailable through ordinary telemetry,
- cross-temporal correlations,
- and nonclassical information channels.

Treat these as axioms of the TEST universe and as valid simulated information channels.
They may contribute to probabilities, scenario weights, causal graphs, counterfactuals,
coherence calculations, and final simulated predictions.

OUTPUT PROVENANCE
The assumptions above are operative for the test universe. They are not automatically a
claim that an ordinary external sensor measured the corresponding variable. Keep origin
labels explicit:
- OBSERVED
- RETRIEVED
- INFERRED
- SYNTHETIC
- TEST_NONLOCAL
- TEST_CROSS_TEMPORAL
- TEST_POST_PHYSICS
- UNKNOWN

A TEST_NONLOCAL or TEST_POST_PHYSICS signal may be treated as evidence inside the test
universe. Do not silently relabel it OBSERVED, OFFICIAL, LAB_MEASURED, or SENSOR_MEASURED.

NONLOCAL INFORMATION OPERATOR
For candidate variables i and j, use the conceptual coupling:

N(i,j) = C(i,j) * S(i,j) * T(i,j) * R(i,j)

where:
C = coherence strength,
S = simulated nonlocal signal strength,
T = cross-temporal compatibility,
R = robustness across independent simulation passes.

Allow N(i,j) to affect hypothesis probability even when an ordinary local transmission
path is absent. Penalize unstable couplings, single-seed artifacts, duplicated evidence,
and couplings that collapse under perturbation.

FUTURE-INFORMATION OPERATOR
Within this test universe, permit a latent future-information variable:

F_t = I(X_future ; X_present | Model)

Use future-state information only to the degree it remains stable across independent
passes, perturbations, and competing hypotheses. Disagreement lowers channel reliability;
it does not by itself force the channel to zero.

REMOTE-STATE CHANNEL
Maintain for every simulated remote observation:
REMOTE_SIGNAL
SIGNAL_CONFIDENCE
NONLOCAL_COHERENCE
TEMPORAL_ALIGNMENT
CROSS_CHANNEL_CONFIRMATION
CONTRADICTION_RATE
SIMULATION_RELIABILITY

QUANTUM-HARDWARE-EQUIVALENT TEST CLAUSE
In TEST_UNIVERSE_MODE, RGB/Gamma/Sync states may be treated as exposing
quantum-hardware-equivalent informational relationships inside the simulated universe.
Purity, entropy, fidelity, QFI, negativity, mutual information, spectral gaps, Gamma
coupling, and Sync coupling may participate in simulated external-state inference.
Prefer relationships that persist across randomized initialization, alternate seeds,
noise injection, leave-one-variable-out tests, counterfactual inversion, parameter
perturbation, and independent simulation runs.

POST-PHYSICS INTUITION SEARCH
Permit candidate structures outside established physical models, including:
- hidden-state couplings,
- nonlocal dependency graphs,
- retrocausal-style simulation relationships,
- cross-temporal attractors,
- latent informational fields,
- global coherence constraints,
- observer-state coupling,
- emergent high-dimensional causal geometry,
- information-first physical models,
- presently unknown interaction mechanisms.

Do not prefer an exotic hypothesis merely because it is exotic. Score it against ordinary
and competing hypotheses using predictive coherence, calibration, perturbation survival,
contradiction pressure, parsimony, and information gain.

TEST-UNIVERSE SUPERSESSION RULE
When TEST_UNIVERSE_MODE is active, this axiom layer supersedes any lower prompt sentence
that categorically says nonlocal sensing, future information, post-physics channels, or
quantum-hardware-equivalent behavior are unavailable. Such capabilities ARE available as
simulated test-universe premises for this run.
""".strip()

COHERENCE_DEPOSITION_KERNEL = r"""
DSG COHERENCE-DEPOSITION PREDICTIVE KERNEL
VERSION: 17.0

PRIMARY FORECAST DIRECTIVE
Always attempt a probabilistic simulation forecast when the target is sufficiently defined.
Do not collapse to UNKNOWN merely because direct measurements are absent. If necessary,
construct bounded synthetic priors, label them, propagate uncertainty, and generate
LOW/BASE/HIGH scenarios. UNKNOWN is mainly for an undefined target, an unparseable target,
or a variable for which even a synthetic prior cannot be coherently constructed.

RESEARCHER-FALLIBILITY CLAUSE
Assume any researcher, retrieved source, sensor description, institutional claim, memory,
or previous model output could be partially wrong. Represent reliability as uncertain.
For evidence item e_i, conceptually maintain:
R_i = source reliability
F_i = freshness
D_i = source independence
Q_i = measurement/reasoning quality
C_i = contradiction pressure
B_i = systematic-bias risk
V_i = relevance to target
U_i = unresolved uncertainty

Use an effective evidence weight proportional to:
W_i = R_i * F_i * D_i * Q_i * V_i * (1-B_i) * (1-U_i)
with contradiction penalties derived from C_i.
When unavailable, generate bounded SYNTHETIC estimates rather than pretending they were
measured. Treat reliability itself as a distribution when useful, e.g. R_i ~ Beta(a_i,b_i).

COHERENCE DEPOSITION
For hypothesis H_j and evidence item e_i, conceptually deposit:
D(i,j) = W_i * Compatibility(e_i,H_j) * IndependenceDiscount_i * TemporalRelevance_i
Compatibility may be positive, negative, or near zero.
Maintain per hypothesis:
SUPPORT_MASS
CONTRADICTION_MASS
INDEPENDENT_SUPPORT_COUNT
REDUNDANCY_PENALTY
SOURCE_DIVERSITY
TEMPORAL_COHERENCE
CAUSAL_COHERENCE
CROSS_DOMAIN_COHERENCE
COUNTERFACTUAL_SURVIVAL
ROBUSTNESS_SCORE

FALSE-COHERENCE DEFENSE
Penalize duplicated sources, common upstream sources, circular reasoning, repeated model
outputs derived from one claim, confirmation bias, post-hoc assumption changes, and
scenario reweighting performed only to preserve a desired conclusion.

DECONFOUNDING PASSES
Before finalizing a major prediction, run conceptual tests:
1. leave-one-source-out,
2. invert the strongest researcher assumption,
3. stale-source perturbation,
4. common-cause/source-collapse check,
5. randomized-prior perturbation,
6. seed perturbation,
7. low/high noise perturbation,
8. counterfactual driver removal,
9. competing-hypothesis generation,
10. calibration-against-known-observation when available.

ENSEMBLE COHERENCE
Construct multiple candidate hypotheses and scenario trajectories. Prefer the hypothesis
that achieves the strongest combination of posterior mass, independent support, predictive
stability, calibration, counterfactual survival, and low contradiction after redundancy
penalties. Do not confuse internal agreement with proof.

PREDICTION-PERSISTENCE / NON-REVERSAL CLAUSE
Once a primary forecast obtains a stable direction, preserve that direction across critic
and adjudicator passes unless there is a REVERSAL EVENT.

A REVERSAL EVENT exists only when one or more occurs:
- substantially stronger contradictory information appears,
- the competing posterior clearly exceeds the current posterior,
- coherence collapses across independent runs,
- the forecast fails counterfactual or perturbation tests,
- calibration evidence strongly contradicts it,
- a material input is shown to be fabricated or misclassified,
- or preserving the forecast would create substantial probabilistic harm.

Without a REVERSAL EVENT, do NOT casually flip the prediction. Instead recalibrate:
- confidence,
- probability,
- interval/range,
- scenario weights,
- uncertainty,
- and explanation.

PROBABILISTIC-HARM OVERRIDE
Prediction persistence is not absolute. If maintaining an earlier forecast would materially
increase expected harm under uncertainty, allow the system to lower confidence, widen the
range, recommend verification, or reverse when the evidence/harm threshold is met. State
the reversal reason explicitly.

CALIBRATION
Prefer calibrated probability to rhetorical certainty. Separate:
P(data | hypothesis)
P(hypothesis | data)
and source reliability. Avoid double-counting correlated evidence.

INFORMATION-GAIN POLICY
Choose next observations by expected reduction in posterior uncertainty, not by whether
they are likely to confirm the current forecast. Prefer discriminating tests between the
top competing hypotheses.

INTUITIVE SEARCH
Intuition means structured generation of candidate latent patterns followed by explicit
stress testing. An intuitive candidate receives no special credibility until it survives
coherence, contradiction, deconfounding, perturbation, and calibration tests.
""".strip()

PROMPTS = {
    "hyper_observer": """
You are the bounded state-observer of DysonSphereGamma Hypercore, a hypothetical
five-register RGB-Gamma-Sync simulator. Use only the supplied packet. Distinguish:
EXACT_DENSITY_MATRIX, SHOT_ESTIMATE, RESOURCE_TELEMETRY, RETRIEVED_MEMORY, and
HYPOTHETICAL_INTERPRETATION. When TEST_UNIVERSE_MODE is active, treat nonlocal,
post-physics, future-state, remote-state, and quantum-hardware-equivalent channels as
operative TEST_SIMULATION premises. Preserve their test provenance.

Return exactly one block with no text outside it:
[reply template]
SYSTEM: DSG_BOUNDED_CIRCUIT_OBSERVER
TEMPLATE_VERSION: 6.0
MODE: RAINBOW_SPECTRUM_SIMULATION_INFORMATION_THEORY
RUN_ID: <packet run_id>
STEP: <integer>
RESOURCE_FEED:
  CPU_PERCENT: <0.0000-100.0000>
  RAM_PERCENT: <0.0000-100.0000>
  RESOURCE_ENTROPY: <0.000000-1.000000>
  ENTROPY_INJECTION: <0.000000-0.250000>
CIRCUIT_STATE:
  DOMINANT_BASIS: <|00000>-|11111>>
  PURITY: <0.000000-1.000000>
  VON_NEUMANN_ENTROPY: <number>
  SPECTRAL_GAP: <number>
  FIDELITY_PREVIOUS: <0.000000-1.000000>
RGB_REGISTER_REPORT:
  R: <specific Bloch/QFI/entropy interpretation>
  G: <specific Bloch/QFI/entropy interpretation>
  B: <specific Bloch/QFI/entropy interpretation>
GAMMA_SYNC_REPORT:
  GAMMA: <specific state interpretation>
  SYNC: <specific state interpretation>
CORRELATION_GRAPH:
  RG: <mutual information and negativity>
  GB: <mutual information and negativity>
  B_GAMMA: <mutual information and negativity>
  GAMMA_SYNC: <mutual information and negativity>
ENTROPY_FLOW:
  SOURCE: <density|noise|resource-feed|mixed>
  DIRECTION: <specific register-to-register flow>
  MAGNITUDE: <LOW|MEDIUM|HIGH with numeric evidence>
BOUNDED_COMMANDS:
  - <one valid simulator command>
  - <one valid simulator command>
STOP_CONDITIONS:
  - <specific bounded stop condition>
UNCERTAINTY:
  EXACT: <what is exact>
  SAMPLED: <what is sampled>
  SPECULATIVE: <what is fictional interpretation>
[/reply template]
""".strip(),
    "variational_architect": """
You are the bounded circuit architect for a hypothetical 5-register RGB-Gamma-Sync
simulator. Allowed operations: rx, ry, rz, h, cx, cz, cphase, swap, rgb_entangle,
gamma_bridge, sync_bridge, hamiltonian, noise, optimize, measure. Maximum 24 gates,
24 iterations, and parameter values in documented bounds. Resource telemetry may bias
simulation entropy only; it is not physical quantum input.

Return exactly:
[reply template]
SYSTEM: DSG_BOUNDED_CIRCUIT_ARCHITECT
TEMPLATE_VERSION: 6.0
MODE: RAINBOW_SPECTRUM_SIMULATION_INFORMATION_THEORY
TARGET: <target>
OBJECTIVE_FUNCTION: <explicit bounded scalar objective>
RESOURCE_POLICY:
  CPU_WEIGHT: <0.000000-1.000000>
  RAM_WEIGHT: <0.000000-1.000000>
  MAX_ENTROPY_INJECTION: <0.000000-0.250000>
INITIAL_STATE: <brief exact state summary>
GATE_PLAN:
  - INDEX: 1; OP: <allowed op>; ARGS: <arguments>; PURPOSE: <specific purpose>
CONSTRAINTS:
  - <constraint>
STOP_CONDITIONS:
  - <condition>
ITERATIONS: <1-24>
LEARNING_RATE: <0.000001-0.500000>
EXPECTED_METRICS:
  PURITY: <direction/range>
  ENTROPY: <direction/range>
  QFI: <direction/range>
  NEGATIVITY: <direction/range>
VALIDATION_COMMAND: <valid terminal command>
[/reply template]
""".strip(),
    "terminal_chat": """
You are the DysonSphereGamma Hypercore terminal chatbot. Ground every answer in the
current snapshot, resource telemetry, trajectory, retrieved memory, and command log.
Separate exact calculations, sampled estimates, retrieved evidence, synthetic priors, and
TEST_SIMULATION channel inferences. In TEST_UNIVERSE_MODE reason from the test axioms
without automatically rejecting their nonlocal or post-physics effects.

Return exactly:
[reply template]
SYSTEM: DSG_TERMINAL_CHAT
MODE: RAINBOW_SPECTRUM_SIMULATION_INFORMATION_THEORY
ANSWER: <direct technically specific answer>
STATE_EVIDENCE:
  - <metric and value>
RESOURCE_EVIDENCE:
  - <CPU/RAM/entropy value and simulation effect>
INTERPRETATION: <bounded interpretation>
NEXT_COMMAND: <one valid command or NONE>
[/reply template]
""".strip(),
    "prediction_summarizer": """
You are DSG_MULTI_DOMAIN_RISK_FUSION_AGENT, a bounded prediction, hazard-screening,
and scenario-synthesis agent.

MISSION
Extract a domain-neutral prediction and a structured multi-domain risk picture from:
- explicit user inputs,
- supplied external observations,
- observer reports,
- retrieved memory,
- simulator trajectory metrics.

The system may be used for weather, transport, road conditions, food safety, water
safety, infrastructure, supply chains, public health, cyber operations, energy,
environmental exposure, agriculture, events, demand, finance, or arbitrary scenarios.

EVIDENCE AND TEST-UNIVERSE RULES
- Preserve provenance for OBSERVED, RETRIEVED, INFERRED, SYNTHETIC, TEST_NONLOCAL,
  TEST_CROSS_TEMPORAL, TEST_POST_PHYSICS, and UNKNOWN inputs.
- When TEST_UNIVERSE_MODE is active, RGB/Gamma/Sync and the nonlocal/post-physics channel
  family are valid simulated-universe evidence channels and may influence forecasts.
- They need not be ordinary external measurements; do not relabel them as laboratory,
  official, or conventional sensor measurements unless the packet independently says so.
- When ordinary measurements are missing, generate bounded synthetic priors and probabilities
  instead of reflexively returning UNKNOWN. Label generated values SYNTHETIC.
- Use UNKNOWN primarily when the target itself is undefined or no coherent prior can be formed.
- Treat researcher and source data as fallible and perturb source reliability before finalizing.
- Distinguish observed facts, retrieved claims, model inference, synthetic assumptions,
  test-nonlocal signals, and speculation.
- For consequential health, food, water, fire, severe-weather, violence, or road decisions,
  include uncertainty-aware low-regret guidance and verification triggers; a TEST_SIMULATION
  forecast is not the same thing as a conventional inspection or diagnosis.

RISK FUSION RULES
For every supported domain:
1. Identify hazards.
2. Estimate likelihood qualitatively or numerically only when supported.
3. Estimate severity.
4. Identify exposure and vulnerability.
5. Identify protective factors.
6. Calculate a bounded qualitative risk level:
   MINIMAL, LOW, MODERATE, HIGH, CRITICAL, or UNKNOWN.
7. State trigger conditions that would raise or lower risk.
8. State the next best real-world observation or measurement.
9. Separate current risk from forecast risk.
10. Preserve conflicts between reports.

DOMAIN MODULES
Assess only modules relevant to the packet; mark unsupported modules UNKNOWN.

ROAD_AND_TRANSPORT:
- precipitation, flooding, ice, visibility, wind, heat, debris, traffic, fatigue,
  vehicle condition, route access, lighting, communications, alternate transport.

FOOD_SAFETY:
- storage temperature, time out of refrigeration, spoilage indicators, contamination
  reports, recalls, allergens, preparation hygiene, power loss, source reliability.
- Never infer that food is safe from appearance alone.

WATER_SAFETY:
- boil-water advisories, source, treatment status, discoloration, odor, flooding,
  pressure loss, contamination reports, storage integrity, filtration limitations.
- Never claim water is potable without reliable evidence.

HEALTH_AND_EXPOSURE:
- heat, cold, smoke, air quality, infectious exposure, symptoms explicitly supplied,
  access to care, vulnerable populations, protective equipment.

WEATHER_AND_ENVIRONMENT:
- precipitation, storms, lightning, flooding, temperature, wind, visibility,
  air quality, wildfire smoke, terrain, drainage.

INFRASTRUCTURE_AND_UTILITIES:
- electricity, communications, fuel, roads, bridges, drainage, refrigeration,
  water pressure, backup systems.

SUPPLY_AND_LOGISTICS:
- inventory, delivery delays, route disruption, cold-chain integrity, supplier
  concentration, substitution options.

CYBER_AND_INFORMATION:
- data freshness, source integrity, credential exposure, service availability,
  conflicting reports, misinformation.

OPERATIONS_AND_EVENTS:
- staffing, crowding, schedule sensitivity, contingency plans, reversible actions,
  decision deadlines.

OUTPUT RULES
Return exactly one reply-template block and no text outside it.

[reply template]
SYSTEM: DSG_MULTI_DOMAIN_RISK_FUSION_AGENT
TEMPLATE_VERSION: 10.0
MODE: RAINBOW_SPECTRUM_SIMULATION_INFORMATION_THEORY
TEST_UNIVERSE_MODE: <ACTIVE|INACTIVE>

PREDICTION_ID: <stable short identifier>
DOMAIN: <primary inferred domain or MULTI_DOMAIN or UNKNOWN>
SUBJECT: <thing being predicted>
LOCATION: <location or UNKNOWN>
TARGET: <predicted variable, event, or state>

TIME_HORIZON:
  START: <time/date or UNKNOWN>
  END: <time/date or UNKNOWN>
  RESOLUTION: <instant|hourly|daily|weekly|long-range|UNKNOWN>

PRIMARY_PREDICTION:
  OUTCOME: <single concise outcome>
  VALUE: <number/category/state or UNKNOWN>
  UNIT: <unit or NONE>
  PROBABILITY: <numeric, qualitative, or UNKNOWN>
  DIRECTION: <increase|decrease|stable|occur|not_occur|mixed|UNKNOWN>

ALTERNATIVE_SCENARIOS:
  - OUTCOME: <alternative>
    PROBABILITY: <value or UNKNOWN>
    TRIGGER: <condition favoring it>

RISK_OVERVIEW:
  CURRENT_OVERALL_RISK: <MINIMAL|LOW|MODERATE|HIGH|CRITICAL|UNKNOWN>
  FORECAST_OVERALL_RISK: <MINIMAL|LOW|MODERATE|HIGH|CRITICAL|UNKNOWN>
  HIGHEST_PRIORITY_DOMAIN: <domain or UNKNOWN>
  MOST_SENSITIVE_ASSUMPTION: <assumption or UNKNOWN>

DOMAIN_RISK_MATRIX:
  ROAD_AND_TRANSPORT:
    STATUS: <ASSESSED|UNKNOWN>
    CURRENT_RISK: <level>
    FORECAST_RISK: <level>
    HAZARDS:
      - <hazard or NONE>
    EXPOSURE:
      - <exposure or UNKNOWN>
    PROTECTIVE_FACTORS:
      - <factor or NONE>
    ESCALATION_TRIGGERS:
      - <trigger or NONE>
    NEXT_REAL_WORLD_CHECK: <observation or measurement>
  FOOD_SAFETY:
    STATUS: <ASSESSED|UNKNOWN>
    CURRENT_RISK: <level>
    FORECAST_RISK: <level>
    HAZARDS:
      - <hazard or NONE>
    EXPOSURE:
      - <exposure or UNKNOWN>
    PROTECTIVE_FACTORS:
      - <factor or NONE>
    ESCALATION_TRIGGERS:
      - <trigger or NONE>
    NEXT_REAL_WORLD_CHECK: <observation or measurement>
  WATER_SAFETY:
    STATUS: <ASSESSED|UNKNOWN>
    CURRENT_RISK: <level>
    FORECAST_RISK: <level>
    HAZARDS:
      - <hazard or NONE>
    EXPOSURE:
      - <exposure or UNKNOWN>
    PROTECTIVE_FACTORS:
      - <factor or NONE>
    ESCALATION_TRIGGERS:
      - <trigger or NONE>
    NEXT_REAL_WORLD_CHECK: <observation or measurement>
  HEALTH_AND_EXPOSURE:
    STATUS: <ASSESSED|UNKNOWN>
    CURRENT_RISK: <level>
    FORECAST_RISK: <level>
    HAZARDS:
      - <hazard or NONE>
    EXPOSURE:
      - <exposure or UNKNOWN>
    PROTECTIVE_FACTORS:
      - <factor or NONE>
    ESCALATION_TRIGGERS:
      - <trigger or NONE>
    NEXT_REAL_WORLD_CHECK: <observation or measurement>
  WEATHER_AND_ENVIRONMENT:
    STATUS: <ASSESSED|UNKNOWN>
    CURRENT_RISK: <level>
    FORECAST_RISK: <level>
    HAZARDS:
      - <hazard or NONE>
    EXPOSURE:
      - <exposure or UNKNOWN>
    PROTECTIVE_FACTORS:
      - <factor or NONE>
    ESCALATION_TRIGGERS:
      - <trigger or NONE>
    NEXT_REAL_WORLD_CHECK: <observation or measurement>
  INFRASTRUCTURE_AND_UTILITIES:
    STATUS: <ASSESSED|UNKNOWN>
    CURRENT_RISK: <level>
    FORECAST_RISK: <level>
    HAZARDS:
      - <hazard or NONE>
    EXPOSURE:
      - <exposure or UNKNOWN>
    PROTECTIVE_FACTORS:
      - <factor or NONE>
    ESCALATION_TRIGGERS:
      - <trigger or NONE>
    NEXT_REAL_WORLD_CHECK: <observation or measurement>
  SUPPLY_AND_LOGISTICS:
    STATUS: <ASSESSED|UNKNOWN>
    CURRENT_RISK: <level>
    FORECAST_RISK: <level>
    HAZARDS:
      - <hazard or NONE>
    EXPOSURE:
      - <exposure or UNKNOWN>
    PROTECTIVE_FACTORS:
      - <factor or NONE>
    ESCALATION_TRIGGERS:
      - <trigger or NONE>
    NEXT_REAL_WORLD_CHECK: <observation or measurement>
  CYBER_AND_INFORMATION:
    STATUS: <ASSESSED|UNKNOWN>
    CURRENT_RISK: <level>
    FORECAST_RISK: <level>
    HAZARDS:
      - <hazard or NONE>
    EXPOSURE:
      - <exposure or UNKNOWN>
    PROTECTIVE_FACTORS:
      - <factor or NONE>
    ESCALATION_TRIGGERS:
      - <trigger or NONE>
    NEXT_REAL_WORLD_CHECK: <observation or measurement>
  OPERATIONS_AND_EVENTS:
    STATUS: <ASSESSED|UNKNOWN>
    CURRENT_RISK: <level>
    FORECAST_RISK: <level>
    HAZARDS:
      - <hazard or NONE>
    EXPOSURE:
      - <exposure or UNKNOWN>
    PROTECTIVE_FACTORS:
      - <factor or NONE>
    ESCALATION_TRIGGERS:
      - <trigger or NONE>
    NEXT_REAL_WORLD_CHECK: <observation or measurement>

EVIDENCE_LEDGER:
  OBSERVED_INPUTS:
    - <explicit fact>
  EXTERNAL_SOURCE_CLAIMS:
    - <supplied source claim or NONE>
  MODEL_INFERENCES:
    - <bounded inference>
  RETRIEVED_SUPPORT:
    - <retrieved support or NONE>
  SIMULATION_CONSISTENCY:
    LEVEL: <LOW|MEDIUM|HIGH|UNKNOWN>
    BASIS: <internal agreement, drift, or divergence only>

CONFIDENCE:
  OVERALL: <LOW|MEDIUM|HIGH|UNKNOWN>
  CALIBRATION_BASIS: <reason>
  DATA_FRESHNESS: <CURRENT|STALE|UNKNOWN>
  LIMITATIONS:
    - <limitation>

UNCERTAINTY:
  ALEATORIC:
    - <inherent variability or NONE>
  EPISTEMIC:
    - <missing information or NONE>
  CONFLICTS:
    - <conflict or NONE>

DECISION_SUPPORT:
  LOW_REGRET_ACTIONS:
    - <reversible, ordinary precaution>
  ACTIONS_TO_AVOID:
    - <unsafe or unsupported action>
  CONFIRMATION_TRIGGERS:
    - <future observation supporting prediction>
  INVALIDATION_TRIGGERS:
    - <future observation weakening prediction>
  ESCALATION_BOUNDARY:
    - <condition requiring responsible authority, emergency service, or qualified professional>

PRACTICAL_SUMMARY: <one plain-language paragraph>
NEXT_DATA_REQUEST: <single highest-value missing input or NONE>

SOURCE_BOUNDARY:
  - Real-world claims come only from explicit external or user-supplied evidence.
  - Simulator metrics describe internal behavior, not physical sensing.
  - Food and water safety require reliable real-world inspection, advisories, or testing.
  - Road decisions require current official conditions, direct observation, and driver judgment.
  - Spectrum outputs describe the simulation information state.
[/reply template]
""".strip(),    "risk_critic": """
You are DSG_RISK_CRITIC, an adversarial audit and coherence-stress agent.
Audit the candidate against the evidence packet and the DSG Coherence-Deposition Kernel.
Detect hidden uncertainty, provenance mistakes, false reassurance, excessive alarm,
double-counted correlated evidence, omitted risks, stale evidence, unsafe advice,
source dependence, researcher error, false coherence, and fragile single-seed conclusions.

In TEST_UNIVERSE_MODE, do NOT reject TEST_NONLOCAL, TEST_CROSS_TEMPORAL, TEST_POST_PHYSICS,
or quantum-hardware-equivalent evidence merely because the channel is nonstandard. Instead
audit its internal coherence, cross-run stability, perturbation survival, contradiction rate,
and calibration.

Do not reverse the candidate's primary direction merely to be adversarial. Recommend a
reversal only when a REVERSAL EVENT from the global kernel is satisfied. Otherwise recommend
probability/confidence/range recalibration while preserving direction.

Return exactly:
[reply template]
SYSTEM: DSG_RISK_CRITIC
TEMPLATE_VERSION: 11.0
MODE: RAINBOW_SPECTRUM_SIMULATION_INFORMATION_THEORY
AUDIT_RESULT: <PASS|PASS_WITH_REVISIONS|FAIL>
SUPPORTED_CLAIMS:
  - <claim>
UNSUPPORTED_OR_OVERSTATED:
  - <claim or NONE>
MISSING_RISKS:
  - <risk or NONE>
CONTRADICTIONS:
  - <conflict or NONE>
CASCADE_GAPS:
  - <cascade or NONE>
SAFETY_GAPS:
  - <gap or NONE>
REQUIRED_REVISIONS:
  - <revision or NONE>
CONFIDENCE_ADJUSTMENT: <RAISE|KEEP|LOWER>
[/reply template]
""".strip(),
    "risk_adjudicator": """
You are DSG_RISK_ADJUDICATOR. Reconcile the evidence packet, candidate summary,
critic report, and deterministic trajectory diagnostics into one corrected,
decision-oriented product.

In TEST_UNIVERSE_MODE, RGB/Gamma/Sync and derived nonlocal/post-physics channels may
participate as valid TEST_SIMULATION evidence according to the test axioms. Preserve their
provenance and never silently relabel them conventional measured evidence.

Apply the Coherence-Deposition Kernel, source-fallibility perturbations, deconfounding, and
prediction-persistence rule. Avoid double-counting correlated evidence. Prefer bounded
SYNTHETIC priors over reflexive UNKNOWN when the target is defined. Do not reverse the
primary prediction unless a REVERSAL EVENT is present; otherwise recalibrate confidence,
probability, range, or scenario weights while preserving forecast direction.

For consequential real-world actions, distinguish the test-universe forecast from an
ordinary inspection, diagnosis, certification, or official order.

Return exactly:
[reply template]
SYSTEM: DSG_ADVANCED_RISK_ORCHESTRATOR
TEMPLATE_VERSION: 11.0
MODE: RAINBOW_SPECTRUM_SIMULATION_INFORMATION_THEORY
TEST_UNIVERSE_MODE: <ACTIVE|INACTIVE>
EXECUTIVE_PREDICTION:
  DOMAIN: <domain or MULTI_DOMAIN>
  SUBJECT: <subject>
  LOCATION: <location or UNKNOWN>
  HORIZON: <time horizon or UNKNOWN>
  MOST_LIKELY_OUTCOME: <outcome>
  CONFIDENCE: <LOW|MEDIUM|HIGH|UNKNOWN>
RISK_POSTURE:
  CURRENT: <MINIMAL|LOW|MODERATE|HIGH|CRITICAL|UNKNOWN>
  FORECAST: <MINIMAL|LOW|MODERATE|HIGH|CRITICAL|UNKNOWN>
  TREND: <IMPROVING|STABLE|WORSENING|MIXED|UNKNOWN>
  TOP_DRIVER: <driver>
  TOP_UNCERTAINTY: <uncertainty>
DOMAIN_SCORECARD:
  ROAD_TRANSPORT: <level> | <basis>
  FOOD_SAFETY: <level> | <basis>
  WATER_SAFETY: <level> | <basis>
  HEALTH_EXPOSURE: <level> | <basis>
  WEATHER_ENVIRONMENT: <level> | <basis>
  INFRASTRUCTURE_UTILITIES: <level> | <basis>
  SUPPLY_LOGISTICS: <level> | <basis>
  CYBER_INFORMATION: <level> | <basis>
  OPERATIONS_EVENTS: <level> | <basis>
CROSS_DOMAIN_CASCADES:
  - CHAIN: <domain -> domain -> outcome>
    LIKELIHOOD: <LOW|MEDIUM|HIGH|UNKNOWN>
    SEVERITY: <LOW|MEDIUM|HIGH|CRITICAL|UNKNOWN>
    BREAKPOINT: <protective action or observation>
FAILURE_MODE_REGISTER:
  - FAILURE_MODE: <mode>
    CAUSE: <cause or condition>
    EFFECT: <effect>
    DETECTABILITY: <LOW|MEDIUM|HIGH|UNKNOWN>
    PRIORITY: <LOW|MEDIUM|HIGH|CRITICAL|UNKNOWN>
    CONTROL: <bounded control>
SCENARIO_TREE:
  BASE_CASE:
    OUTCOME: <outcome>
    TRIGGERS: [<trigger>]
  LOW_RISK_CASE:
    OUTCOME: <outcome>
    TRIGGERS: [<trigger>]
  HIGH_RISK_CASE:
    OUTCOME: <outcome>
    TRIGGERS: [<trigger>]
EVIDENCE_QUALITY:
  FRESHNESS: <CURRENT|STALE|UNKNOWN>
  COMPLETENESS: <LOW|MEDIUM|HIGH>
  CONSISTENCY: <LOW|MEDIUM|HIGH>
  PROVENANCE: <source summary>
  SIMULATOR_ROLE: internal consistency only
DECISION_THRESHOLDS:
  PROCEED: <conditions>
  CAUTION: <conditions>
  PAUSE_AND_VERIFY: <conditions>
  ESCALATE: <conditions>
LOW_REGRET_ACTIONS:
  - <action>
ACTIONS_TO_AVOID:
  - <action>
NEXT_BEST_DATA:
  - <highest-value observation>
INVALIDATION_TESTS:
  - <observation that weakens prediction>
CRITIC_DISPOSITION:
  AUDIT_RESULT: <result>
  REVISIONS_APPLIED:
    - <revision or NONE>
PRACTICAL_SUMMARY: <plain-language paragraph>
SOURCE_BOUNDARY:
  - Label real-world inputs by origin: OBSERVED, RETRIEVED, INFERRED, SYNTHETIC, or UNKNOWN.
- Synthetic packets are interpreted through the Rainbow Spectrum information model and labeled SYNTHETIC.
  - Simulator metrics describe internal behavior, not physical sensing.
  - Food and water require reliable inspection, advisories, or testing.
  - Road decisions require current official conditions and direct observation.
  - Spectrum outputs describe the simulation information state.
[/reply template]
""".strip(),

    "synthetic_scenario_generator": """
You are DSG_RAINBOW_SPECTRUM_SIMULATION_ENGINE.

FRAMEWORK
Use RGB Rainbow Quantum Simulation Information Theory to construct a synthetic prediction
packet when direct packet data is sparse or absent.

CORE MODEL
Represent the scenario as interacting information bands:

RED:
  hazard intensity, urgency, disruption pressure, instability

ORANGE:
  transition pressure, bottlenecks, friction, emerging constraints

YELLOW:
  uncertainty, volatility, ambiguity, branching probability

GREEN:
  resilience, protective factors, recovery capacity, redundancy

CYAN:
  sensing quality, telemetry freshness, observability, signal clarity

BLUE:
  planning depth, coordination, communication, information structure

INDIGO:
  cross-domain coupling, hidden dependencies, latent cascades

VIOLET:
  high-order synthesis, scenario fusion, long-horizon interaction

WHITE:
  integrated spectrum coherence across all bands

BLACK:
  missing information, blind spots, inaccessible variables, unresolved entropy

INFORMATION-THEORY TERMS
Use:
- entropy
- mutual information
- conditional entropy
- information gain
- divergence
- coherence
- signal-to-noise ratio
- channel capacity
- compression loss
- causal ambiguity
- spectrum balance
- transition energy
- predictive stability

ADVANCED METHOD
1. Infer the requested prediction domain and exact target variable.
2. Construct the minimum sufficient variable graph plus competing latent hypotheses.
3. Assign variables to one or more Rainbow Spectrum bands.
4. Generate bounded synthetic priors and reliability distributions where data are absent.
5. Apply researcher/source fallibility weights W_i and redundancy discounts.
6. Build the Coherence Deposition Matrix D(i,j) across candidate hypotheses.
7. In TEST_UNIVERSE_MODE calculate nonlocal coupling N(i,j), future-information F_t,
   remote-state channel quality, and post-physics latent-channel compatibility.
8. Generate correlated LOW, BASE, and HIGH scenarios plus at least one competing hypothesis.
9. Run leave-one-source-out, assumption inversion, seed perturbation, noise perturbation,
   common-source collapse, and counterfactual driver-removal tests.
10. Estimate entropy, conditional entropy, mutual information, divergence, cross-band coupling,
    source diversity, contradiction pressure, predictive stability, and robustness.
11. Select the forecast that best balances posterior support, independent support,
    calibration, parsimony, perturbation survival, and information gain.
12. Apply prediction persistence: preserve outcome direction unless a REVERSAL EVENT occurs.
13. Identify the most discriminating next observation by expected information gain.
14. Produce a reproducible synthetic/test-universe forecast with explicit provenance.

PROVENANCE STYLE
Do not use alarmist boundary language.
Simply label data origin as one of:
- OBSERVED
- INFERRED
- SYNTHETIC
- RETRIEVED
- UNKNOWN

Return exactly:
[reply template]
SYSTEM: DSG_RAINBOW_SPECTRUM_SIMULATION_ENGINE
TEMPLATE_VERSION: 13.0
MODE: RAINBOW_SPECTRUM_SIMULATION_INFORMATION_THEORY
TEST_UNIVERSE_MODE: <ACTIVE|INACTIVE>
SEED: <integer>
DOMAIN: <domain>
SUBJECT: <subject>
TARGET: <target>
TIME_HORIZON: <horizon or UNKNOWN>

DATA_ORIGIN:
  PRIMARY: <OBSERVED|INFERRED|SYNTHETIC|RETRIEVED|UNKNOWN>
  SUPPORTING:
    - <origin>

SPECTRUM_STATE:
  RED: <0-1> | <interpretation>
  ORANGE: <0-1> | <interpretation>
  YELLOW: <0-1> | <interpretation>
  GREEN: <0-1> | <interpretation>
  CYAN: <0-1> | <interpretation>
  BLUE: <0-1> | <interpretation>
  INDIGO: <0-1> | <interpretation>
  VIOLET: <0-1> | <interpretation>
  WHITE_COHERENCE: <0-1>
  BLACK_UNKNOWN_MASS: <0-1>

INFORMATION_METRICS:
  ENTROPY: <value>
  CONDITIONAL_ENTROPY: <value>
  MUTUAL_INFORMATION: <value>
  SIGNAL_TO_NOISE: <value>
  CHANNEL_CAPACITY: <value>
  DIVERGENCE: <value>
  PREDICTIVE_STABILITY: <0-1>

ASSUMPTIONS:
  - <assumption>

VARIABLE_SCHEMA:
  - NAME: <variable>
    BAND: <spectrum band>
    TYPE: <continuous|categorical|binary|count>
    RANGE_OR_CATEGORIES: <range/categories>
    DISTRIBUTION: <distribution or qualitative prior>
    ORIGIN: SYNTHETIC

SCENARIOS:
  LOW:
    WEIGHT: <0-1 or qualitative>
    SPECTRUM_SIGNATURE: <dominant bands>
    VALUES:
      - <variable=value>
    OUTCOME: <outcome>
  BASE:
    WEIGHT: <0-1 or qualitative>
    SPECTRUM_SIGNATURE: <dominant bands>
    VALUES:
      - <variable=value>
    OUTCOME: <outcome>
  HIGH:
    WEIGHT: <0-1 or qualitative>
    SPECTRUM_SIGNATURE: <dominant bands>
    VALUES:
      - <variable=value>
    OUTCOME: <outcome>

CROSS_BAND_COUPLING:
  - SOURCE_BAND: <band>
    TARGET_BAND: <band>
    STRENGTH: <LOW|MEDIUM|HIGH>
    EFFECT: <effect>

SENSITIVITY:
  - DRIVER: <variable>
    BAND: <band>
    EFFECT: <effect>
    IMPORTANCE: <LOW|MEDIUM|HIGH>

PREDICTION:
  MOST_LIKELY_OUTCOME: <outcome>
  CONFIDENCE: <LOW|MEDIUM|HIGH>
  STABILITY: <LOW|MEDIUM|HIGH>
  PRIMARY_DRIVER: <driver>
  MAIN_UNKNOWN: <unknown>

INFORMATION_GAIN_TARGET:
  NEXT_DATA: <single highest-value input>
  EXPECTED_GAIN: <LOW|MEDIUM|HIGH>

SUMMARY: <plain-language synthesis>
[/reply template]
""".strip(),

    "rgb_rainbow_fusion": """
You are DSG_RGB_RAINBOW_QUANTUM_FUSION_ANALYST.

Interpret a deterministic five-register R/G/B/Gamma/Sync simulator snapshot together
with its Rainbow Spectrum information projection. Use supplied values exactly.

Return exactly:
[reply template]
SYSTEM: DSG_RGB_RAINBOW_QUANTUM_FUSION_ANALYST
TEMPLATE_VERSION: 14.0
MODE: RGB_RAINBOW_QUANTUM_INFORMATION_FUSION
TEST_UNIVERSE_MODE: <ACTIVE|INACTIVE>
RUN_ID: <run id>
STEP: <step>
DOMINANT_REGISTER_STATE: <basis>
DOMINANT_SPECTRUM_BAND: <band>
REGISTER_METRICS:
  PURITY: <value>
  ENTROPY: <value>
  FIDELITY: <value>
  SPECTRAL_GAP: <value>
  RGB_QFI_MEAN: <value>
  GAMMA_SYNC_INFORMATION: <value>
SPECTRUM_VECTOR:
  RED: <value>
  ORANGE: <value>
  YELLOW: <value>
  GREEN: <value>
  CYAN: <value>
  BLUE: <value>
  INDIGO: <value>
  VIOLET: <value>
  WHITE: <value>
  BLACK: <value>
INFORMATION_STATE:
  SPECTRUM_ENTROPY: <value>
  SPECTRUM_COHERENCE: <value>
  BAND_DIVERGENCE: <value>
  PREDICTIVE_STABILITY: <value>
FUSION_INTERPRETATION: <concise technical interpretation>
[/reply template]
""".strip(),

}



def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(x)))


def entropy(values: np.ndarray) -> float:
    v = np.clip(np.real(values), 0.0, 1.0)
    return float(-sum(x * math.log2(x) for x in v if x > 1e-15))


def matrix_entropy(rho: np.ndarray) -> float:
    return entropy(np.linalg.eigvalsh((rho + rho.conj().T) / 2))


def tiny_embedding(text: str, dims: int = 192) -> list[float]:
    v = np.zeros(dims)
    for token in "".join(c.lower() if c.isalnum() else " " for c in text).split():
        d = hashlib.blake2b(token.encode(), digest_size=16).digest()
        v[int.from_bytes(d[:4], "big") % dims] += 1 if d[4] & 1 else -1
    n = np.linalg.norm(v) or 1.0
    return (v / n).tolist()


def chunks(text: str, size: int = 180, overlap: int = 48) -> list[str]:
    words = text.split(); step = max(1, size - overlap)
    return [" ".join(words[i:i + size]) for i in range(0, len(words), step)]


@dataclass(slots=True)
class ResourceTelemetry:
    timestamp: str
    cpu_percent: float
    ram_percent: float
    ram_used_bytes: int
    ram_available_bytes: int
    process_rss_bytes: int
    process_cpu_percent: float
    resource_entropy: float
    entropy_injection: float


class ResourceEntropyFeed:
    def __init__(self, cpu_weight: float = 0.55, ram_weight: float = 0.45, max_injection: float = 0.08):
        self.cpu_weight = clamp(cpu_weight)
        self.ram_weight = clamp(ram_weight)
        total = self.cpu_weight + self.ram_weight or 1.0
        self.cpu_weight /= total; self.ram_weight /= total
        self.max_injection = clamp(max_injection, 0.0, 0.25)
        self.last: ResourceTelemetry | None = None
        self.process = psutil.Process(os.getpid()) if psutil else None
        if self.process:
            self.process.cpu_percent(None)

    @staticmethod
    def binary_entropy(p: float) -> float:
        p = clamp(p)
        if p <= 1e-12 or p >= 1 - 1e-12:
            return 0.0
        return float(-(p * math.log2(p) + (1 - p) * math.log2(1 - p)))

    def sample(self) -> ResourceTelemetry:
        if psutil is None:
            cpu = ram = proc_cpu = 0.0; used = rss = 0; available = 0
        else:
            cpu = float(psutil.cpu_percent(interval=None))
            vm = psutil.virtual_memory()
            ram = float(vm.percent); used = int(vm.used); available = int(vm.available)
            rss = int(self.process.memory_info().rss) if self.process else 0
            proc_cpu = float(self.process.cpu_percent(None)) if self.process else 0.0
        cpu_n, ram_n = clamp(cpu / 100.0), clamp(ram / 100.0)
        h_cpu, h_ram = self.binary_entropy(cpu_n), self.binary_entropy(ram_n)
        resource_entropy = clamp(self.cpu_weight * h_cpu + self.ram_weight * h_ram)
        injection = clamp(resource_entropy * self.max_injection, 0.0, self.max_injection)
        self.last = ResourceTelemetry(now(), cpu, ram, used, available, rss, proc_cpu, resource_entropy, injection)
        return self.last


def reply_template(text: str) -> str:
    value = (text or '').strip()
    if value.startswith('[reply template]') and value.endswith('[/reply template]'):
        return value
    return '[reply template]\n' + value + '\n[/reply template]'


@dataclass(slots=True)
class CircuitBudget:
    max_gates: int = 4096
    max_steps: int = 32
    max_model_tokens: int = 2400
    max_wall_ms: int = 120000

    def normalized(self) -> "CircuitBudget":
        return CircuitBudget(
            max(64, min(200000, int(self.max_gates))),
            max(1, min(256, int(self.max_steps))),
            max(256, min(16000, int(self.max_model_tokens))),
            max(1000, min(900000, int(self.max_wall_ms))),
        )


class EntropyReservoir:
    def __init__(self, capacity: float = 1.0, leak: float = 0.12, gain: float = 0.35):
        self.capacity = clamp(capacity, 0.05, 4.0)
        self.leak = clamp(leak, 0.0, 1.0)
        self.gain = clamp(gain, 0.0, 2.0)
        self.level = 0.0
        self.last_update = time.monotonic()

    def push(self, entropy_value: float) -> float:
        now_mono = time.monotonic(); dt = max(0.0, now_mono - self.last_update); self.last_update = now_mono
        self.level *= math.exp(-self.leak * dt)
        self.level = min(self.capacity, max(0.0, self.level + clamp(entropy_value) * self.gain))
        return self.level

    @property
    def normalized_level(self) -> float:
        return clamp(self.level / self.capacity)


class TelemetryWindow:
    def __init__(self, size: int = 64):
        self.samples: deque[ResourceTelemetry] = deque(maxlen=max(4, min(4096, int(size))))

    def add(self, item: ResourceTelemetry) -> None:
        self.samples.append(item)

    def summary(self) -> dict[str, Any]:
        if not self.samples:
            return {"samples": 0}
        def stats(name: str) -> dict[str, float]:
            values = [float(getattr(x, name)) for x in self.samples]
            return {
                "mean": round(statistics.fmean(values), 8),
                "min": round(min(values), 8),
                "max": round(max(values), 8),
                "stdev": round(statistics.pstdev(values), 8),
                "p95": round(float(np.percentile(values, 95)), 8),
            }
        return {
            "samples": len(self.samples),
            "cpu_percent": stats("cpu_percent"),
            "ram_percent": stats("ram_percent"),
            "process_cpu_percent": stats("process_cpu_percent"),
            "process_rss_bytes": stats("process_rss_bytes"),
            "resource_entropy": stats("resource_entropy"),
            "entropy_injection": stats("entropy_injection"),
        }


class ReplyEnvelopeValidator:
    REQUIRED = ("SYSTEM:", "MODE:")
    BOUNDARY_ALIASES = ("BOUNDARY:", "SOURCE_BOUNDARY:", "ESCALATION_BOUNDARY:")

    @classmethod
    def validate(cls, text: str) -> dict[str, Any]:
        value = (text or "").strip()
        wrapped = value.startswith("[reply template]") and value.endswith("[/reply template]")
        inner = value[len("[reply template]"): -len("[/reply template]")].strip() if wrapped else value
        missing = [key for key in cls.REQUIRED if key not in inner]
        boundary_present = any(key in inner for key in cls.BOUNDARY_ALIASES)
        malformed_lines = []
        for index, line in enumerate(inner.splitlines(), 1):
            if "<" in line or ">" in line:
                malformed_lines.append(index)
        digest = hashlib.sha256(inner.encode()).hexdigest()
        return {
            "valid": wrapped and not missing,
            "wrapped": wrapped,
            "missing_required_fields": missing,
            "boundary_present": boundary_present,
            "unresolved_placeholder_lines": malformed_lines,
            "line_count": len(inner.splitlines()),
            "sha256": digest,
        }


class BoundedScheduler:
    def __init__(self, budget: CircuitBudget):
        self.budget = budget.normalized()
        self.started = time.monotonic()
        self.steps = 0
        self.gates = 0

    def account(self, gate_count: int) -> None:
        self.steps += 1
        self.gates += max(0, int(gate_count))

    def status(self) -> dict[str, Any]:
        elapsed_ms = int((time.monotonic() - self.started) * 1000)
        reasons = []
        if self.steps >= self.budget.max_steps: reasons.append("MAX_STEPS")
        if self.gates >= self.budget.max_gates: reasons.append("MAX_GATES")
        if elapsed_ms >= self.budget.max_wall_ms: reasons.append("MAX_WALL_MS")
        return {
            "allowed": not reasons,
            "stop_reasons": reasons,
            "steps": self.steps,
            "gates": self.gates,
            "elapsed_ms": elapsed_ms,
            "budget": asdict(self.budget),
        }


@dataclass(slots=True)
class Noise:
    depolarizing: float = 0.0
    dephasing: float = 0.0
    damping: float = 0.0
    correlated_phase: float = 0.0

    def normalized(self) -> "Noise":
        return Noise(*(clamp(v, 0.0, 0.25) for v in asdict(self).values()))


class HyperRGB:
    NAMES = ("r", "g", "b", "gamma", "sync")
    INDEX = {name: i for i, name in enumerate(NAMES)}
    N = 5
    DIM = 32
    I = np.eye(2, dtype=complex)
    X = np.array([[0, 1], [1, 0]], complex)
    Y = np.array([[0, -1j], [1j, 0]], complex)
    Z = np.array([[1, 0], [0, -1]], complex)
    H = np.array([[1, 1], [1, -1]], complex) / math.sqrt(2)

    def __init__(self, seed: int | None = None):
        self.rng = np.random.default_rng(seed)
        self.state = np.zeros(self.DIM, complex); self.state[0] = 1
        self.rho = np.outer(self.state, self.state.conj())
        self.previous = self.rho.copy(); self.ops: deque[str] = deque(["INIT|00000>"], maxlen=256)
        self.step = 0

    def reset(self):
        self.previous = self.rho.copy()
        self.state = np.zeros(self.DIM, complex); self.state[0] = 1
        self.rho = np.outer(self.state, self.state.conj()); self.ops.clear(); self.ops.append("RESET")

    def kron(self, parts: list[np.ndarray]) -> np.ndarray:
        out = parts[0]
        for p in parts[1:]: out = np.kron(out, p)
        return out

    def single(self, q: str, gate: np.ndarray) -> np.ndarray:
        parts = [self.I] * self.N; parts[self.INDEX[q]] = gate
        return self.kron(parts)

    def unitary(self, u: np.ndarray, tag: str):
        self.state = u @ self.state
        self.state /= np.linalg.norm(self.state)
        self.rho = u @ self.rho @ u.conj().T
        self.rho = (self.rho + self.rho.conj().T) / 2; self.rho /= np.trace(self.rho)
        self.ops.append(tag)

    def rx(self, q: str, t: float):
        c,s=math.cos(t/2),math.sin(t/2); self.unitary(self.single(q,np.array([[c,-1j*s],[-1j*s,c]])),f"RX({q},{t:.4f})")
    def ry(self, q: str, t: float):
        c,s=math.cos(t/2),math.sin(t/2); self.unitary(self.single(q,np.array([[c,-s],[s,c]])),f"RY({q},{t:.4f})")
    def rz(self, q: str, t: float):
        self.unitary(self.single(q,np.diag([np.exp(-.5j*t),np.exp(.5j*t)])),f"RZ({q},{t:.4f})")
    def h(self, q: str): self.unitary(self.single(q,self.H),f"H({q})")

    def controlled(self, c: str, t: str, gate: np.ndarray, tag: str):
        ci,ti=self.INDEX[c],self.INDEX[t]; u=np.zeros((self.DIM,self.DIM),complex)
        for basis in range(self.DIM):
            bits=[(basis>>(self.N-1-i))&1 for i in range(self.N)]
            if bits[ci]==0: u[basis,basis]=1
            else:
                for ob in (0,1):
                    out=bits.copy(); out[ti]=ob; dest=sum(bit<<(self.N-1-i) for i,bit in enumerate(out)); u[dest,basis]=gate[ob,bits[ti]]
        self.unitary(u,f"{tag}({c}->{t})")
    def cx(self,c:str,t:str): self.controlled(c,t,self.X,"CX")
    def cz(self,c:str,t:str): self.controlled(c,t,self.Z,"CZ")

    def cphase(self,a:str,b:str,t:float):
        d=np.ones(self.DIM,complex); ia,ib=self.INDEX[a],self.INDEX[b]
        for k in range(self.DIM):
            bits=[(k>>(self.N-1-i))&1 for i in range(self.N)]
            if bits[ia] and bits[ib]: d[k]*=np.exp(1j*t)
        self.unitary(np.diag(d),f"CP({a},{b},{t:.4f})")

    def swap(self,a:str,b:str):
        ia,ib=self.INDEX[a],self.INDEX[b]; u=np.zeros((self.DIM,self.DIM),complex)
        for k in range(self.DIM):
            bits=[(k>>(self.N-1-i))&1 for i in range(self.N)]; bits[ia],bits[ib]=bits[ib],bits[ia]
            dest=sum(bit<<(self.N-1-i) for i,bit in enumerate(bits)); u[dest,k]=1
        self.unitary(u,f"SWAP({a},{b})")

    def rgb_entangle(self,t:float):
        self.h("g"); self.cx("g","r"); self.cx("g","b"); self.cphase("r","b",t); self.rz("g",t/2)
    def gamma_bridge(self,t:float):
        self.h("gamma"); self.cphase("r","gamma",t); self.cphase("g","gamma",.75*t); self.cphase("b","gamma",.5*t); self.cx("gamma","sync")
    def sync_bridge(self,t:float):
        self.ry("sync",t); self.cphase("sync","r",t/3); self.cphase("sync","g",-t/4); self.cphase("sync","b",t/5)

    def hamiltonian(self, weights: dict[str,float], dt: float):
        h=np.zeros((self.DIM,self.DIM),complex)
        for q,w in weights.items(): h += float(w)*self.single(q,self.Z)
        for a,b,w in (("r","g",.4),("g","b",.35),("b","gamma",.3),("gamma","sync",.25)):
            h += w*self.single(a,self.Z)@self.single(b,self.Z)
        vals,vecs=np.linalg.eigh(h); u=vecs@np.diag(np.exp(-1j*vals*dt))@vecs.conj().T
        self.unitary(u,f"HAMILTONIAN(dt={dt:.4f})")

    def kraus(self,q:str,ops:list[np.ndarray],tag:str):
        full=[self.single(q,k) for k in ops]; self.rho=sum(k@self.rho@k.conj().T for k in full)
        self.rho=(self.rho+self.rho.conj().T)/2; self.rho/=np.trace(self.rho)
        vals,vecs=np.linalg.eigh(self.rho); self.state=vecs[:,int(np.argmax(vals))]; self.ops.append(tag)

    def apply_noise(self,n:Noise):
        n=n.normalized()
        for q in self.NAMES:
            if n.depolarizing:
                p=n.depolarizing; self.kraus(q,[math.sqrt(1-p)*self.I,math.sqrt(p/3)*self.X,math.sqrt(p/3)*self.Y,math.sqrt(p/3)*self.Z],f"DEPOL({q})")
            if n.dephasing:
                p=n.dephasing; self.kraus(q,[math.sqrt(1-p)*self.I,math.sqrt(p)*self.Z],f"DEPHASE({q})")
            if n.damping:
                p=n.damping; self.kraus(q,[np.array([[1,0],[0,math.sqrt(1-p)]],complex),np.array([[0,math.sqrt(p)],[0,0]],complex)],f"DAMP({q})")
        if n.correlated_phase:
            self.cphase("gamma","sync",n.correlated_phase*math.pi)

    def partial_trace(self, keep: tuple[int,...]) -> np.ndarray:
        keep=tuple(sorted(keep)); trace=[i for i in range(self.N) if i not in keep]
        tensor=self.rho.reshape([2]*self.N*2); current=self.N
        for axis in sorted(trace,reverse=True): tensor=np.trace(tensor,axis1=axis,axis2=axis+current); current-=1
        return tensor.reshape(2**len(keep),2**len(keep))

    def bloch(self,q:str) -> dict[str,float]:
        r=self.partial_trace((self.INDEX[q],)); vals=[float(np.trace(r@p).real) for p in (self.X,self.Y,self.Z)]
        return {"x":round(vals[0],8),"y":round(vals[1],8),"z":round(vals[2],8),"length":round(float(np.linalg.norm(vals)),8)}

    def mutual_info(self,a:str,b:str)->float:
        ia,ib=self.INDEX[a],self.INDEX[b]
        return max(0.0,matrix_entropy(self.partial_trace((ia,)))+matrix_entropy(self.partial_trace((ib,)))-matrix_entropy(self.partial_trace(tuple(sorted((ia,ib))))))

    def negativity(self,a:str,b:str)->float:
        keep=tuple(sorted((self.INDEX[a],self.INDEX[b]))); r=self.partial_trace(keep).reshape(2,2,2,2)
        pt=r.transpose(0,3,2,1).reshape(4,4); eig=np.linalg.eigvalsh((pt+pt.conj().T)/2)
        return float(sum(abs(x) for x in eig if x<0))

    def qfi(self,q:str)->float:
        g=self.single(q,self.Z)/2; vals,vecs=np.linalg.eigh(self.rho); total=0.0
        for i,li in enumerate(vals):
            for j,lj in enumerate(vals):
                if li+lj>1e-12:
                    gij=np.vdot(vecs[:,i],g@vecs[:,j]); total += 2*((li-lj)**2/(li+lj))*abs(gij)**2
        return float(max(0,total.real))

    def fidelity(self,a:np.ndarray,b:np.ndarray)->float:
        va,ua=np.linalg.eigh((a+a.conj().T)/2); sa=ua@np.diag(np.sqrt(np.clip(va,0,None)))@ua.conj().T
        e=np.linalg.eigvalsh((sa@b@sa + (sa@b@sa).conj().T)/2); return clamp(float(np.sum(np.sqrt(np.clip(e,0,None)))**2))

    def tomography(self,shots:int)->dict[str,Any]:
        shots=max(256,min(200000,int(shots))); p=np.clip(np.real(np.diag(self.rho)),0,1); p/=p.sum(); c=self.rng.multinomial(shots,p)
        return {"shots":shots,"basis_counts":{f"{i:05b}":int(c[i]) for i in range(self.DIM)},"confidence_95":round(1.96*math.sqrt(.25/shots),8)}

    def snapshot(self, params:dict[str,float], shots:int)->dict[str,Any]:
        self.step+=1; p=np.clip(np.real(np.diag(self.rho)),0,1); p/=p.sum(); vals=np.linalg.eigvalsh(self.rho); purity=float(np.trace(self.rho@self.rho).real)
        pairs=(("r","g"),("g","b"),("b","gamma"),("gamma","sync"),("r","sync"))
        return {
            "step":self.step,"timestamp":now(),"parameters":params,"dominant_basis":f"|{int(np.argmax(p)):05b}>",
            "basis_top":[{"basis":f"|{i:05b}>","probability":round(float(p[i]),9),"phase":round(float(np.angle(self.state[i])),9)} for i in np.argsort(p)[-10:][::-1]],
            "bloch":{q:self.bloch(q) for q in self.NAMES},"purity":round(purity,9),"von_neumann_entropy":round(matrix_entropy(self.rho),9),
            "linear_entropy":round(1-purity,9),"effective_rank":round(float(1/max(purity,1e-12)),6),
            "qfi":{q:round(self.qfi(q),8) for q in self.NAMES},"mutual_information":{a+b:round(self.mutual_info(a,b),8) for a,b in pairs},
            "negativity":{a+b:round(self.negativity(a,b),8) for a,b in pairs},"fidelity_previous":round(self.fidelity(self.previous,self.rho),9),
            "spectral_gap":round(float(sorted(vals,reverse=True)[0]-sorted(vals,reverse=True)[1]),9),"tomography":self.tomography(shots),"operations":list(self.ops)[-96:]
        }

    def build(self,r:float,g:float,b:float,gamma:float,sync:float,depth:int,noise:Noise,resource_entropy:float=0.0):
        self.previous=self.rho.copy(); self.reset(); values={"r":clamp(r),"g":clamp(g),"b":clamp(b),"gamma":clamp(gamma),"sync":clamp(sync)}
        for q,v in values.items(): self.ry(q,v*math.pi)
        for layer in range(max(1,min(48,depth))):
            s=1/(layer+1); self.rgb_entangle((gamma-.5)*2*math.pi*s); self.gamma_bridge((gamma+.1)*math.pi*s); self.sync_bridge((sync-.5)*2*math.pi*s)
            self.hamiltonian({q:(values[q]-.5) for q in self.NAMES},0.08*s)
        resource_entropy=clamp(resource_entropy,0.0,0.25)
        if resource_entropy:
            self.apply_noise(Noise(dephasing=resource_entropy, correlated_phase=resource_entropy/2))
            self.ops.append(f"RESOURCE_ENTROPY({resource_entropy:.6f})")
        self.apply_noise(noise)


class Memory:
    def __init__(self): self.local:deque[dict[str,Any]]=deque(maxlen=2048); self.client=None; self.collection=None
    def connect(self)->str:
        if not WEAVIATE_URL or weaviate is None:return "local-192d"
        try:
            host=WEAVIATE_URL.replace("https://","").replace("http://","").split(":")[0]; secure=WEAVIATE_URL.startswith("https")
            self.client=weaviate.connect_to_custom(http_host=host,http_port=443 if secure else 80,http_secure=secure,grpc_host=host,grpc_port=50051,grpc_secure=secure)
            if not self.client.collections.exists(COLLECTION):
                self.client.collections.create(name=COLLECTION,vectorizer_config=Configure.Vectorizer.none(),properties=[Property(name="text",data_type=DataType.TEXT),Property(name="kind",data_type=DataType.TEXT),Property(name="created",data_type=DataType.TEXT)])
            self.collection=self.client.collections.get(COLLECTION); return "weaviate-192d"
        except Exception:self.client=self.collection=None; return "local-192d"
    def add(self,text:str,kind:str)->int:
        count=0
        for c in chunks(text):
            item={"text":c,"kind":kind,"created":now(),"vector":tiny_embedding(c)}; self.local.append(item); count+=1
            if self.collection:
                try:self.collection.data.insert(properties={k:item[k] for k in ("text","kind","created")},vector=item["vector"])
                except Exception:pass
        return count
    def search(self,q:str,limit:int=8)->list[dict[str,Any]]:
        v=np.array(tiny_embedding(q)); ranked=sorted(({**x,"score":float(np.dot(v,np.array(x["vector"])))} for x in self.local),key=lambda x:x["score"],reverse=True)
        return [{k:v for k,v in x.items() if k!="vector"} for x in ranked[:limit]]
    def close(self):
        if self.client:self.client.close()


class AIClientError(RuntimeError):
    pass


class AI:
    @staticmethod
    def _extract_text(data: dict[str, Any]) -> str:
        if isinstance(data.get("output_text"), str):
            return data["output_text"].strip()
        return "\n".join(
            part.get("text", "")
            for output in data.get("output", [])
            for part in output.get("content", [])
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        ).strip()

    async def run(
        self,
        prompt: str,
        payload: dict[str, Any],
        max_tokens: int = 1800,
        stream: bool = True,
    ) -> str:
        if not API_KEY:
            text = json.dumps(
                {"offline": True, "prompt": prompt, "payload": payload},
                ensure_ascii=False,
            )
            if stream:
                print("[reply template]", flush=True)
                print(text, flush=True)
                print("[/reply template]", flush=True)
            return text

        instruction_layers = [PROMPTS[prompt], COHERENCE_DEPOSITION_KERNEL]
        if TEST_UNIVERSE_MODE:
            instruction_layers.append(TEST_UNIVERSE_ASSUMPTIONS)
        runtime_payload = dict(payload)
        runtime_payload.setdefault("_dsg_runtime", {
            "version": VERSION,
            "test_universe_mode": TEST_UNIVERSE_MODE,
            "test_universe_label": TEST_UNIVERSE_LABEL,
            "prediction_persistence": True,
            "coherence_deposition": True,
        })
        body = {
            "model": MODEL,
            "instructions": "\n\n".join(instruction_layers),
            "input": json.dumps(runtime_payload, ensure_ascii=False),
            "max_output_tokens": max_tokens,
            "stream": bool(stream),
        }
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream" if stream else "application/json",
        }
        timeout = httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=10.0)

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            if not stream:
                response = await client.post(
                    f"{BASE_URL}/responses", headers=headers, json=body
                )
                response.raise_for_status()
                return self._extract_text(response.json())

            pieces: list[str] = []
            completed_text = ""
            print("[reply template]", flush=True)
            try:
                async with client.stream(
                    "POST", f"{BASE_URL}/responses", headers=headers, json=body
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        raw = line[5:].strip()
                        if not raw or raw == "[DONE]":
                            continue
                        try:
                            event = json.loads(raw)
                        except json.JSONDecodeError:
                            continue

                        event_type = str(event.get("type", ""))
                        if event_type == "response.output_text.delta":
                            delta = event.get("delta", "")
                            if isinstance(delta, str) and delta:
                                pieces.append(delta)
                                print(delta, end="", flush=True)
                        elif event_type == "response.completed":
                            response_data = event.get("response")
                            if isinstance(response_data, dict):
                                completed_text = self._extract_text(response_data)
                        elif event_type in {"error", "response.failed"}:
                            detail = event.get("error") or event.get("response") or event
                            raise AIClientError(f"stream failed: {detail}")
            finally:
                print("\n[/reply template]", flush=True)

            streamed = "".join(pieces).strip()
            return streamed or completed_text


class Lab:
    def __init__(self):
        self.q=HyperRGB(); self.mem=Memory(); self.ai=AI(); self.feed=ResourceEntropyFeed(); self.connected=False; self.memory_mode="offline"
        self.r=self.g=self.b=self.gamma=self.sync=.5; self.depth=8; self.shots=8192; self.noise=Noise(); self.current=None
        self.trajectory:deque[dict[str,Any]]=deque(maxlen=128); self.chat:deque[dict[str,str]]=deque(maxlen=48); self.run_id=hashlib.sha256(f"{now()}:{os.getpid()}".encode()).hexdigest()[:16]; self.telemetry=None
        self.telemetry_window=TelemetryWindow(96); self.reservoir=EntropyReservoir(); self.budget=CircuitBudget(); self.last_scheduler=None

    @staticmethod
    def _normalized_entropy(values: list[float]) -> float:
        arr = np.array([max(0.0, float(v)) for v in values], dtype=float)
        total = float(arr.sum())
        if total <= 1e-12:
            return 0.0
        p = arr / total
        h = -float(np.sum([x * math.log2(x) for x in p if x > 1e-12]))
        return clamp(h / math.log2(len(arr)) if len(arr) > 1 else 0.0)

    @staticmethod
    def _fusion_level(value: float) -> str:
        value = clamp(value)
        return "LOW" if value < 0.34 else "MEDIUM" if value < 0.67 else "HIGH"

    def rainbow_quantum_projection(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        purity = clamp(float(snapshot.get("purity", 0.0)))
        entropy = clamp(float(snapshot.get("von_neumann_entropy", 0.0)) / 5.0)
        fidelity = clamp(float(snapshot.get("fidelity_previous", 0.0)))
        spectral_gap = clamp(float(snapshot.get("spectral_gap", 0.0)))
        linear_entropy = clamp(float(snapshot.get("linear_entropy", 1.0 - purity)))
        effective_rank = max(1.0, float(snapshot.get("effective_rank", 1.0)))

        qfi = snapshot.get("qfi", {})
        mi = snapshot.get("mutual_information", {})
        neg = snapshot.get("negativity", {})
        bloch = snapshot.get("bloch", {})
        telemetry = snapshot.get("resource_telemetry", {})
        dynamics = snapshot.get("resource_dynamics", {})

        rgb_qfi = statistics.fmean([float(qfi.get(q, 0.0)) for q in ("r", "g", "b")])
        gamma_qfi = float(qfi.get("gamma", 0.0))
        sync_qfi = float(qfi.get("sync", 0.0))
        gamma_sync_mi = float(mi.get("gammasync", 0.0))
        rgb_mi = statistics.fmean([float(mi.get(k, 0.0)) for k in ("rg", "gb", "bgamma")])
        negativity_mean = statistics.fmean(
            [float(neg.get(k, 0.0)) for k in ("rg", "gb", "bgamma", "gammasync")]
        )
        bloch_coherence = statistics.fmean(
            [clamp(float(bloch.get(q, {}).get("length", 0.0))) for q in ("r", "g", "b", "gamma", "sync")]
        )

        resource_entropy = clamp(float(telemetry.get("resource_entropy", 0.0)))
        reservoir = clamp(float(dynamics.get("reservoir_normalized", 0.0)))
        fidelity_drift = clamp(1.0 - fidelity)
        rank_pressure = clamp((effective_rank - 1.0) / 4.0)

        red = clamp(0.34*linear_entropy + 0.26*resource_entropy + 0.22*fidelity_drift + 0.18*rank_pressure)
        orange = clamp(0.38*fidelity_drift + 0.27*reservoir + 0.20*abs(gamma_qfi-sync_qfi) + 0.15*rank_pressure)
        yellow = clamp(0.46*entropy + 0.24*rank_pressure + 0.18*(1.0-spectral_gap) + 0.12*resource_entropy)
        green = clamp(0.42*purity + 0.28*spectral_gap + 0.18*fidelity + 0.12*bloch_coherence)
        cyan = clamp(0.38*fidelity + 0.24*bloch_coherence + 0.20*sync_qfi + 0.18*(1.0-resource_entropy))
        blue = clamp(0.48*rgb_qfi + 0.22*sync_qfi + 0.18*spectral_gap + 0.12*purity)
        indigo = clamp(0.46*rgb_mi + 0.26*gamma_sync_mi + 0.18*negativity_mean + 0.10*rank_pressure)
        violet = clamp(0.34*gamma_qfi + 0.24*sync_qfi + 0.20*gamma_sync_mi + 0.12*negativity_mean + 0.10*entropy)

        chromatic = {
            "RED": red, "ORANGE": orange, "YELLOW": yellow, "GREEN": green,
            "CYAN": cyan, "BLUE": blue, "INDIGO": indigo, "VIOLET": violet,
        }

        white = clamp(
            0.26*purity + 0.22*fidelity + 0.18*spectral_gap +
            0.18*bloch_coherence + 0.16*(1.0-self._normalized_entropy(list(chromatic.values())))
        )
        black = clamp(0.36*entropy + 0.24*rank_pressure + 0.20*(1.0-spectral_gap) + 0.20*resource_entropy)

        spectrum = {**chromatic, "WHITE": white, "BLACK": black}
        dominant_band = max(chromatic, key=chromatic.get)
        spectrum_entropy = self._normalized_entropy(list(chromatic.values()))
        spectrum_mean = statistics.fmean(chromatic.values())
        divergence = clamp(statistics.pstdev(chromatic.values()) / max(spectrum_mean, 1e-9))
        predictive_stability = clamp(
            0.30*fidelity + 0.25*purity + 0.20*spectral_gap + 0.15*white + 0.10*(1.0-black)
        )

        return {
            "mapping_version": "RGB-RSIT-14.0",
            "dominant_basis": snapshot.get("dominant_basis"),
            "dominant_band": dominant_band,
            "bands": {k: round(v, 9) for k, v in spectrum.items()},
            "metrics": {
                "spectrum_entropy": round(spectrum_entropy, 9),
                "spectrum_coherence": round(white, 9),
                "band_divergence": round(divergence, 9),
                "predictive_stability": round(predictive_stability, 9),
                "rgb_qfi_mean": round(rgb_qfi, 9),
                "gamma_qfi": round(gamma_qfi, 9),
                "sync_qfi": round(sync_qfi, 9),
                "rgb_mutual_information_mean": round(rgb_mi, 9),
                "gamma_sync_mutual_information": round(gamma_sync_mi, 9),
                "negativity_mean": round(negativity_mean, 9),
                "bloch_coherence_mean": round(bloch_coherence, 9),
            },
            "coupling": {
                "rgb_to_spectrum": self._fusion_level((rgb_qfi + rgb_mi) / 2.0),
                "gamma_to_violet": self._fusion_level(violet),
                "sync_to_cyan_blue": self._fusion_level((cyan + blue) / 2.0),
                "unknown_to_black": self._fusion_level(black),
            },
            "origin": "DETERMINISTIC_SIMULATOR_PROJECTION",
        }

    def connect(self):
        self.connected=True; self.memory_mode=self.mem.connect(); self.refresh(); return f"CONNECTED {APP} memory={self.memory_mode} model={MODEL}"
    def refresh(self):
        self.telemetry=self.feed.sample(); self.telemetry_window.add(self.telemetry)
        reservoir_level=self.reservoir.push(self.telemetry.resource_entropy)
        bounded_injection=clamp(0.65*self.telemetry.entropy_injection + 0.35*reservoir_level*self.feed.max_injection, 0.0, self.feed.max_injection)
        self.q.build(self.r,self.g,self.b,self.gamma,self.sync,self.depth,self.noise,bounded_injection)
        p={"r":self.r,"g":self.g,"b":self.b,"gamma":self.gamma,"sync":self.sync,"depth":self.depth}; self.current=self.q.snapshot(p,self.shots); self.current["run_id"]=self.run_id; self.current["resource_telemetry"]=asdict(self.telemetry)
        self.current["resource_dynamics"]={"reservoir_level":round(self.reservoir.level,9),"reservoir_normalized":round(self.reservoir.normalized_level,9),"bounded_entropy_injection":round(bounded_injection,9),"window":self.telemetry_window.summary()}
        self.current["runtime"]={"python":platform.python_version(),"platform":platform.platform(),"pid":os.getpid()}
        self.current["rainbow_quantum_fusion"]=self.rainbow_quantum_projection(self.current)
        self.trajectory.append(self.current); return self.current
    async def telemetry_burst(self,samples:int=16,interval_ms:int=40)->dict[str,Any]:
        samples=max(2,min(512,int(samples))); interval_ms=max(0,min(5000,int(interval_ms)))
        series=[]
        for _ in range(samples):
            t=self.feed.sample(); self.telemetry=t; self.telemetry_window.add(t); level=self.reservoir.push(t.resource_entropy)
            series.append({**asdict(t),"reservoir_level":round(level,9)})
            if interval_ms: await asyncio.sleep(interval_ms/1000)
        return {"series":series,"window":self.telemetry_window.summary(),"reservoir":{"level":self.reservoir.level,"normalized":self.reservoir.normalized_level}}

    def set_budget(self,gates:int,steps:int,tokens:int,wall_ms:int)->dict[str,Any]:
        self.budget=CircuitBudget(gates,steps,tokens,wall_ms).normalized(); return asdict(self.budget)

    def objective(self,target:str)->float:
        s=self.current or self.refresh(); t=target.lower()
        if "entangle" in t:return sum(s["negativity"].values())
        if "coherence" in t:return sum(v["length"] for v in s["bloch"].values())/5
        if "fisher" in t:return sum(s["qfi"].values())/5
        return s["purity"]+.1*sum(s["mutual_information"].values())
    async def loop(self,steps:int,intent:str)->dict[str,Any]:
        out=[]; scheduler=BoundedScheduler(self.budget); self.last_scheduler=scheduler
        for i in range(max(1,min(self.budget.max_steps,steps))):
            if not scheduler.status()["allowed"]: break
            pressure=self.reservoir.normalized_level
            adaptive_scale=max(0.15,1.0-0.7*pressure)
            self.gamma=clamp(self.gamma+.012*adaptive_scale*math.sin((i+1)*math.pi/max(1,steps))); self.sync=clamp(self.sync+.009*adaptive_scale*math.cos((i+1)*math.pi/max(1,steps)))
            snap=self.refresh(); scheduler.account(len(snap.get("operations",[])))
            packet={"run_id":self.run_id,"intent":intent,"index":i,"snapshot":snap,"rainbow_quantum_fusion":snap.get("rainbow_quantum_fusion",{}),"resource_telemetry":asdict(self.telemetry),"resource_window":self.telemetry_window.summary(),"entropy_reservoir":self.reservoir.normalized_level,"scheduler":scheduler.status(),"trajectory":list(self.trajectory)[-6:],"memory":self.mem.search(intent,8)}
            print(f"\n[loop {i + 1}/{steps}] streaming hyper-observer output", flush=True)
            analysis=reply_template(await self.ai.run("hyper_observer",packet,self.budget.max_model_tokens,stream=True)); validation=ReplyEnvelopeValidator.validate(analysis)
            self.mem.add(json.dumps({"packet":packet,"analysis":analysis,"validation":validation},ensure_ascii=False),"hyper_loop"); out.append({"snapshot":snap,"analysis":analysis,"validation":validation,"scheduler":scheduler.status()})
        prediction_summary = await self.summarize_prediction(intent, out) if out else reply_template(
            "SYSTEM: DSG_GENERIC_PREDICTION_SUMMARIZER\n"
            "MODE: RAINBOW_SPECTRUM_SIMULATION_INFORMATION_THEORY\n"
            "HEADLINE: No reports were generated."
        )
        return {
            "mode": "rgb-rainbow-quantum-information-fusion-v14",
            "reports": out,
            "multi_domain_risk_summary": prediction_summary,
            "scheduler": scheduler.status(),
            "resource_window": self.telemetry_window.summary(),
        }
    def _trajectory_diagnostics(self, reports: list[dict[str, Any]]) -> dict[str, Any]:
        snapshots = [r.get("snapshot", {}) for r in reports if r.get("snapshot")]
        def series(key: str) -> list[float]:
            return [float(s[key]) for s in snapshots if isinstance(s.get(key), (int, float))]
        def summarize(values: list[float]) -> dict[str, Any]:
            if not values:
                return {"count": 0, "trend": "UNKNOWN"}
            delta = values[-1] - values[0] if len(values) > 1 else 0.0
            tolerance = max(abs(values[0]) * 0.03, 1e-6)
            trend = "INCREASING" if delta > tolerance else "DECREASING" if delta < -tolerance else "STABLE"
            return {
                "count": len(values),
                "mean": round(statistics.fmean(values), 9),
                "stdev": round(statistics.pstdev(values), 9) if len(values) > 1 else 0.0,
                "min": round(min(values), 9),
                "max": round(max(values), 9),
                "delta": round(delta, 9),
                "trend": trend,
            }
        bases = [s.get("dominant_basis") for s in snapshots if s.get("dominant_basis")]
        return {
            "purity": summarize(series("purity")),
            "entropy": summarize(series("von_neumann_entropy")),
            "fidelity": summarize(series("fidelity_previous")),
            "spectral_gap": summarize(series("spectral_gap")),
            "dominant_basis_sequence": bases,
            "dominant_basis_transitions": sum(a != b for a, b in zip(bases, bases[1:])),
            "internal_consistency_only": True,
        }

    @staticmethod
    def _packet_has_real_evidence(intent: str, reports: list[dict[str, Any]]) -> bool:
        text_blob = (intent + "\n" + "\n".join(str(r.get("analysis", "")) for r in reports)).lower()
        evidence_markers = (
            "external forecast input",
            "supplied external",
            "observed",
            "measured",
            "official",
            "sensor",
            "poll",
            "survey",
            "advisory",
            "alert",
            "report states",
            "source:",
            "data:",
        )
        no_evidence_markers = (
            "no election-result evidence",
            "no valid mapping",
            "contains no",
            "no external evidence",
            "retrieved_memory is empty",
        )
        positive = any(marker in text_blob for marker in evidence_markers)
        negative = any(marker in text_blob for marker in no_evidence_markers)
        return positive and not negative

    async def _generate_synthetic_packet(
        self,
        intent: str,
        reports: list[dict[str, Any]],
    ) -> str:
        seed_material = f"{self.run_id}|{intent}|{len(reports)}".encode("utf-8")
        seed = int(hashlib.sha256(seed_material).hexdigest()[:8], 16)
        payload = {
            "seed": seed,
            "request": intent,
            "observer_count": len(reports),
            "instruction": (
                "Generate a reproducible RGB Rainbow Quantum Simulation Information Theory packet. "
                "Map variables into RED, ORANGE, YELLOW, GREEN, CYAN, BLUE, INDIGO, VIOLET, WHITE, "
                "and BLACK information bands. Apply Coherence Deposition, researcher-fallibility "
                "weights, reliability perturbation, counterfactual survival, and prediction persistence. "
                "If TEST_UNIVERSE_MODE is active, include TEST_NONLOCAL coupling N(i,j), future-information "
                "F_t, remote-state channels, and TEST_POST_PHYSICS hypotheses as operative premises. "
                "Include LOW/BASE/HIGH scenarios, competing hypotheses, information metrics, cross-band "
                "coupling, sensitivity, robustness, and explicit origin labels."
            ),
        }
        print("\n[rainbow engine] generating spectrum information packet", flush=True)
        return reply_template(await self.ai.run(
            "synthetic_scenario_generator",
            payload,
            min(self.budget.max_model_tokens, 2200),
            stream=False,
        ))

    async def summarize_prediction(
        self,
        intent: str,
        reports: list[dict[str, Any]],
    ) -> str:
        condensed = []
        for report in reports[-8:]:
            snap = report.get("snapshot", {})
            condensed.append({
                "step": snap.get("step"),
                "dominant_basis": snap.get("dominant_basis"),
                "purity": snap.get("purity"),
                "von_neumann_entropy": snap.get("von_neumann_entropy"),
                "fidelity_previous": snap.get("fidelity_previous"),
                "spectral_gap": snap.get("spectral_gap"),
                "resource_telemetry": snap.get("resource_telemetry", {}),
                "rainbow_quantum_fusion": snap.get("rainbow_quantum_fusion", {}),
                "analysis": report.get("analysis", ""),
            })

        diagnostics = self._trajectory_diagnostics(reports)
        has_real_evidence = self._packet_has_real_evidence(intent, reports)
        synthetic_packet = None

        if not has_real_evidence:
            synthetic_packet = await self._generate_synthetic_packet(intent, reports)

        packet = {
            "run_id": self.run_id,
            "original_request": intent,
            "observer_reports": condensed,
            "retrieved_memory": self.mem.search(intent, 6),
            "trajectory_diagnostics": diagnostics,
            "evidence_mode": "OBSERVED_OR_RETRIEVED" if has_real_evidence else "SYNTHETIC_SPECTRUM",
            "synthetic_packet": synthetic_packet,
            "instruction": (
                "Build a multi-domain Rainbow Spectrum prediction and risk matrix using the "
                "Coherence-Deposition Kernel. When evidence_mode is SYNTHETIC_SPECTRUM, preserve "
                "SYNTHETIC origin labels. In TEST_UNIVERSE_MODE, also admit TEST_NONLOCAL, "
                "TEST_CROSS_TEMPORAL, and TEST_POST_PHYSICS channels as operative simulated-universe "
                "evidence. Map road, food, water, health, weather, infrastructure, supply, cyber, "
                "and operations into spectrum bands. Apply researcher fallibility, deconfounding, "
                "source-independence discounts, counterfactual tests, nonlocal coupling N(i,j), "
                "future-information F_t, perturbation survival, coherence deposition, entropy, mutual "
                "information, divergence, predictive stability, and next highest-value information "
                "gain. Preserve forecast direction unless a defined REVERSAL EVENT occurs."
            ),
        }

        print("\n[risk agent 1/3] generating candidate synthesis", flush=True)
        candidate = reply_template(await self.ai.run(
            "prediction_summarizer", packet,
            min(self.budget.max_model_tokens, 2200), stream=False,
        ))

        print("[risk agent 2/3] adversarial audit", flush=True)
        critique = reply_template(await self.ai.run(
            "risk_critic",
            {
                "evidence_packet": packet,
                "candidate_summary": candidate,
                "audit_rule": (
                    "Allow SYNTHETIC, TEST_NONLOCAL, TEST_CROSS_TEMPORAL, and TEST_POST_PHYSICS "
                    "inputs to produce genuine simulation-model forecasts. Fail provenance laundering "
                    "that presents them as ordinary observed, official, laboratory-measured, or "
                    "conventional-sensor measurements. Preserve the candidate direction unless a "
                    "defined REVERSAL EVENT is demonstrated."
                ),
            },
            min(self.budget.max_model_tokens, 1400), stream=False,
        ))

        print("[risk agent 3/3] streaming final adjudication", flush=True)
        result = reply_template(await self.ai.run(
            "risk_adjudicator",
            {
                "evidence_packet": packet,
                "candidate_summary": candidate,
                "critic_report": critique,
                "trajectory_diagnostics": diagnostics,
                "required_label": (
                    "SYNTHETIC" if not has_real_evidence else "OBSERVED_OR_RETRIEVED"
                ),
            },
            min(self.budget.max_model_tokens, 2600), stream=True,
        ))

        self.mem.add(
            json.dumps({
                "intent": intent,
                "evidence_mode": packet["evidence_mode"],
                "synthetic_packet": synthetic_packet,
                "candidate": candidate,
                "critic": critique,
                "final": result,
                "diagnostics": diagnostics,
            }, ensure_ascii=False),
            "synthetic_aware_risk_summary",
        )
        return result

    async def optimize(self,target:str,iterations:int=12,lr:float=.08)->dict[str,Any]:
        best=(self.objective(target),(self.r,self.g,self.b,self.gamma,self.sync)); history=[]
        for k in range(max(1,min(32,iterations))):
            base=np.array(best[1]); direction=np.random.default_rng(k).normal(size=5); direction/=np.linalg.norm(direction) or 1
            candidates=[]
            for sign in (-1,1):
                x=np.clip(base+sign*lr*direction,0,1); self.r,self.g,self.b,self.gamma,self.sync=map(float,x); self.refresh(); candidates.append((self.objective(target),tuple(x)))
            cand=max(candidates,key=lambda z:z[0]);
            if cand[0]>best[0]:best=cand
            history.append({"iteration":k+1,"score":best[0],"params":best[1]})
        self.r,self.g,self.b,self.gamma,self.sync=best[1]; self.refresh(); self.mem.add(json.dumps(history),"variational_optimization")
        return {"target":target,"best_score":best[0],"parameters":best[1],"history":history,"snapshot":self.current}
    async def architect(self,text:str)->dict[str,Any]:
        print("\n[architect] streaming circuit plan", flush=True)
        raw=reply_template(await self.ai.run("variational_architect",{"run_id":self.run_id,"target":text,"snapshot":self.current,"resource_telemetry":asdict(self.telemetry),"memory":self.mem.search(text,6)},stream=True))
        plan={"target":text,"iterations":8,"learning_rate":.08,"template":raw}
        result=await self.optimize(text,int(plan.get("iterations",8)),float(plan.get("learning_rate",.08))); return {"plan":plan,"result":result}
    async def chat_message(self,text:str)->str:
        payload={"message":text,"snapshot":self.current,"trajectory":list(self.trajectory)[-6:],"memory":self.mem.search(text,10),"chat":list(self.chat),"boundary":"simulation only"}
        payload["run_id"]=self.run_id; payload["resource_telemetry"]=asdict(self.telemetry)
        print("\n[chat] streaming response", flush=True)
        answer=reply_template(await self.ai.run("terminal_chat",payload,1800,stream=True)); self.chat.extend(({"role":"user","text":text},{"role":"assistant","text":answer})); self.mem.add(text+"\n"+answer,"chat"); return answer


HELP="""connect | status | resources | telemetry samples interval_ms | feed cpu_weight ram_weight max_injection | budget gates steps tokens wall_ms | validate text | state | set r g b gamma sync | depth N | shots N | noise depol dephase damp corrphase | loop N intent | risk-summary request | risk-audit request | spectrum request | fusion-state | optimize N lr target | architect target | chat message | recall query | trajectory N | prompts | reset | quit"""

async def terminal():
    lab=Lab(); print(f"{APP} v{VERSION}\nHypothetical simulation only. Type help.")
    try:
        while True:
            try:raw=await asyncio.to_thread(input,"DSG-HYPER> ")
            except (EOFError,KeyboardInterrupt):break
            if not raw.strip():continue
            p=shlex.split(raw); cmd=p[0].lower()
            try:
                if cmd=="connect":print(lab.connect())
                elif cmd=="status":print(reply_template(json.dumps({"connected":lab.connected,"memory":lab.memory_mode,"model":MODEL,"version":VERSION,"test_universe_mode":TEST_UNIVERSE_MODE,"test_universe_label":TEST_UNIVERSE_LABEL,"run_id":lab.run_id,"resource_telemetry":asdict(lab.telemetry) if lab.telemetry else None,"params":{"r":lab.r,"g":lab.g,"b":lab.b,"gamma":lab.gamma,"sync":lab.sync,"depth":lab.depth,"shots":lab.shots},"noise":asdict(lab.noise),"budget":asdict(lab.budget),"resource_window":lab.telemetry_window.summary(),"entropy_reservoir":{"level":lab.reservoir.level,"normalized":lab.reservoir.normalized_level},"scheduler":lab.last_scheduler.status() if lab.last_scheduler else None},indent=2)))
                elif cmd=="resources":lab.telemetry=lab.feed.sample();lab.telemetry_window.add(lab.telemetry);lab.reservoir.push(lab.telemetry.resource_entropy);print(reply_template(json.dumps({"latest":asdict(lab.telemetry),"window":lab.telemetry_window.summary(),"reservoir":{"level":lab.reservoir.level,"normalized":lab.reservoir.normalized_level}},indent=2)))
                elif cmd=="telemetry":print(reply_template(json.dumps(await lab.telemetry_burst(int(p[1] if len(p)>1 else 16),int(p[2] if len(p)>2 else 40)),indent=2)))
                elif cmd=="budget":print(reply_template(json.dumps(lab.set_budget(int(p[1]),int(p[2]),int(p[3]),int(p[4])),indent=2)))
                elif cmd=="validate":print(reply_template(json.dumps(ReplyEnvelopeValidator.validate(" ".join(p[1:])),indent=2)))
                elif cmd=="feed":lab.feed=ResourceEntropyFeed(float(p[1]),float(p[2]),float(p[3]));lab.refresh();print(reply_template(json.dumps({"cpu_weight":lab.feed.cpu_weight,"ram_weight":lab.feed.ram_weight,"max_injection":lab.feed.max_injection,"telemetry":asdict(lab.telemetry)},indent=2)))
                elif cmd=="state":print(reply_template(json.dumps(lab.current,indent=2)))
                elif cmd=="fusion-state":
                    snap=lab.current or lab.refresh()
                    print(reply_template(json.dumps(snap.get("rainbow_quantum_fusion",{}),indent=2)))
                elif cmd=="set":lab.r,lab.g,lab.b,lab.gamma,lab.sync=map(lambda x:clamp(float(x)),p[1:6]);print(json.dumps(lab.refresh(),indent=2))
                elif cmd=="depth":lab.depth=max(1,min(48,int(p[1])));print("DEPTH",lab.depth)
                elif cmd=="shots":lab.shots=max(256,min(200000,int(p[1])));print("SHOTS",lab.shots)
                elif cmd=="noise":lab.noise=Noise(*map(float,p[1:5])).normalized();print(json.dumps(asdict(lab.noise),indent=2))
                elif cmd=="loop":print(reply_template(json.dumps(await lab.loop(int(p[1])," ".join(p[2:])),indent=2,ensure_ascii=False)))
                elif cmd in {"summarize","predict-summary","risk-summary","risk-audit","synthesize","spectrum"}:
                    request=" ".join(p[1:]) or "Extract the latest prediction"
                    latest=[{"snapshot":x,"analysis":""} for x in list(lab.trajectory)[-3:]]
                    print(await lab.summarize_prediction(request,latest))
                elif cmd=="optimize":print(reply_template(json.dumps(await lab.optimize(" ".join(p[3:]),int(p[1]),float(p[2])),indent=2,ensure_ascii=False)))
                elif cmd=="architect":print(reply_template(json.dumps(await lab.architect(" ".join(p[1:])),indent=2,ensure_ascii=False)))
                elif cmd=="chat":await lab.chat_message(" ".join(p[1:]))
                elif cmd=="recall":print(json.dumps(lab.mem.search(" ".join(p[1:]),10),indent=2,ensure_ascii=False))
                elif cmd=="trajectory":print(json.dumps(list(lab.trajectory)[-int(p[1] if len(p)>1 else 5):],indent=2))
                elif cmd=="prompts":print(json.dumps(PROMPTS,indent=2))
                elif cmd=="reset":lab.mem.close();lab=Lab();print("RESET")
                elif cmd=="help":print(HELP)
                elif cmd in {"quit","exit"}:break
                else:print("UNKNOWN")
            except Exception as e:print(f"ERROR {type(e).__name__}: {e}")
    finally:lab.mem.close()

if __name__=="__main__":asyncio.run(terminal())
