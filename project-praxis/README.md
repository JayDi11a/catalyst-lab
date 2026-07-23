# Project Praxis

**Formally verified AI agent runtime on Kubernetes — proving correctness of LLM reasoning, agent decisions, tool use, and persistent memory.**

Praxis bridges formal proof logic (F\*/Pulse separation logic, Z3 SMT solver) with AI agent runtimes (Hermes, OpenClaw) and sandboxed execution (NVIDIA OpenShell) to provide machine-checked guarantees across the full agent action chain: from LLM inference through tool execution to persistent state.

*Praxis (πρᾶξις) — verified action.*

**Namespace:** `catalystlab-shared` (verification gateway sidecar to kagent agent pods)

## Overview

### The Problem

Autonomous AI agents act across four surfaces — each unverified today:

1. **LLM reasoning** — the model's inference chain may be unsound, hallucinated, or manipulated
2. **Agent decisions** — the agent's choice of what to do next may violate safety constraints or policy
3. **Tool use** — tool calls may produce side effects beyond their stated scope
4. **Persistent memory** — stored facts may be poisoned (OWASP ASI06), contradictory, or logically unsound, compounding errors across sessions

No current framework provides formal guarantees across this chain.

### The Solution

Praxis interposes a verification gateway in the agent runtime. Every action passes through two verification layers:

- **Content verification** (F\* refinement types + Z3) — proves reasoning is logically sound, consistent, and not poisoned
- **Substrate verification** (Pulse separation logic + Z3) — proves operations preserve ownership, frame isolation, bounds, and concurrency safety

Both layers generate verification conditions that Z3 discharges. Actions proceed only on proof; rejections include counterexamples for agent retry.

### Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  OPENSHELL SANDBOX (per agent)                              │
│                                                             │
│  Agent Runtime ──► ActionIntent                             │
│  (LLM inference,     │                                     │
│   agent decision,    │                                     │
│   tool call,         │                                     │
│   memory write)      │                                     │
│                      ▼                                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  PRAXIS VERIFICATION GATEWAY                         │  │
│  │                                                      │  │
│  │  fstar-coder agent (proof-copilot / Claude Code)     │  │
│  │  F* MCP Server (incremental typechecking)            │  │
│  │                                                      │  │
│  │  Content:   P1 inference soundness                   │  │
│  │             P2 consistency                           │  │
│  │             P3 poisoning resistance                  │  │
│  │             P4 completeness                          │  │
│  │                                                      │  │
│  │  Substrate: P5 ownership (separation logic)          │  │
│  │             P6 frame rule                            │  │
│  │             P7 bounds enforcement                    │  │
│  │             P8 concurrency safety (PulseCore CSL)    │  │
│  │                                                      │  │
│  │  Tool use:  P9 tool scope (call within declared API) │  │
│  │             P10 side-effect containment              │  │
│  │                                                      │  │
│  │  fstar.exe + Z3 ──► Verified ✓ / Rejected ✗         │  │
│  └──────────────────────────────────────────────────────┘  │
│                        │                                    │
│                        ▼                                    │
│  Action execution (tool call, memory write, response)      │
│                                                             │
│  OpenShell Policy Engine    OpenShell Privacy Router        │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

| Dependency | Version | Purpose |
|------------|---------|---------|
| F\* + Pulse | v2026.05.17+ | Proof-oriented programming, separation logic |
| Z3 | 4.13+ | SMT solver (installed with F\*) |
| Claude Code | Current | Agent for proof generation via proof-copilot |
| proof-copilot plugin | Latest | F\*/Pulse skills for Claude Code |
| NVIDIA OpenShell | Alpha | Agent sandbox with policy enforcement |
| Python | 3.11+ | Verification gateway service |

### Install F\* and Pulse

```bash
curl -fsSL https://aka.ms/install-fstar | bash -s -- --release
```

Installs `fstar.exe` and Z3 to `~/.local/bin/`.

### Install proof-copilot Plugin (Claude Code)

```text
/plugin marketplace add FStarLang/proof-copilot
/plugin install proof-copilot@proof-copilot
```

Provides the `fstar-coder` agent and 8 skills: `fstarverifier`, `fstarmcp`, `smtprofiling`, `proofdebugging`, `specreview`, `krmlextraction`, `projectsetup`, `sourcebuild`.

### Install OpenShell

```bash
pip install openshell
```

## Project Structure

```text
project-praxis/
├── README.md                      # This file
├── ARCHITECTURE.md                # Detailed design, verification properties, PoC phases
├── .gitignore                     # F* build artifacts, configs with secrets
├── specs/
│   ├── content/                   # Content verification (P1-P4)
│   │   ├── AgentReasoning.fst     # LLM inference soundness, consistency, poisoning
│   │   └── AgentReasoning.fsti    # Interface: content verification predicates
│   └── substrate/                 # Substrate verification (P5-P10)
│       ├── AgentState.fst         # Ownership, frame rule, bounds, concurrency
│       ├── AgentState.fsti        # Interface: substrate verification predicates
│       ├── ToolScope.fst          # Tool call scope and side-effect containment
│       └── ToolScope.fsti         # Interface: tool verification predicates
├── config/
│   ├── praxis-config.example.yaml # Verification gateway configuration
│   └── openshell-policy.yaml      # OpenShell sandbox policy for Praxis agents
├── deployment.yaml                # Verification gateway deployment
├── service.yaml                   # Verification gateway service
├── sidecar-patch.yaml             # Inject Praxis as sidecar to kagent agent pods
└── scripts/
    ├── install-fstar.sh           # F*/Pulse/Z3 toolchain setup
    └── verify-specs.sh            # Run F* verification on all specs
```

## Verification Properties

### Content (F\* refinement types → Z3)

| ID | Property | Verification Target | What It Catches |
|----|----------|-------------------|----------------|
| P1 | Inference soundness | LLM reasoning chain | Model hallucinates a "fact" not grounded in observations |
| P2 | Consistency | Agent knowledge base | New fact contradicts existing state |
| P3 | Poisoning resistance | All persisted content | Prompt injection stored as trusted memory (OWASP ASI06) |
| P4 | Completeness | Agent decision coverage | Critical observation or action not captured |

### Substrate (Pulse separation logic → Z3)

| ID | Property | Verification Target | What It Catches |
|----|----------|-------------------|----------------|
| P5 | Ownership | Memory regions | Agent writes to another agent's state |
| P6 | Frame rule | All agent state | Write to one region corrupts another |
| P7 | Bounds | Tier constraints | Write exceeds tier limits (Hermes: 2200 chars) |
| P8 | Concurrency | Shared state | Concurrent sessions corrupt shared tiers |

### Tool Use (F\* + Pulse → Z3)

| ID | Property | Verification Target | What It Catches |
|----|----------|-------------------|----------------|
| P9 | Tool scope | Tool call arguments | Tool called with arguments outside its declared API surface |
| P10 | Side-effect containment | Tool execution state | Tool produces side effects beyond its specified output |

## Integration with Catalyst Lab

| Component | Integration Point |
|-----------|------------------|
| **Kagent** (11 agents) | Praxis runs as sidecar to agent pods; verifies all agent actions |
| **OTel Collector** | Proof certificates emitted as OTel spans (`praxis.proof.*` attributes) |
| **MLflow** | Proof certificates logged as experiment metadata for audit |
| **Tempo + Grafana** | Verification latency dashboard, rejection rate monitoring |
| **PostgreSQL (CNPG)** | Proof certificate storage |
| **LLaMA Stack** | Agent inference and tool calls pass through verification gateway |
| **Istio** | mTLS between agent and verification gateway |
| **OpenShell** | Sandbox isolation; Policy Engine enforces runtime constraints |

## Usage

### Verify Specs Locally

```bash
# Verify all F*/Pulse specs
./scripts/verify-specs.sh

# Verify a single spec
fstar.exe --include specs/ specs/content/AgentReasoning.fst
```

### Generate Proofs with Claude Code

Use the proof-copilot plugin to generate and verify Pulse proofs:

```text
"Use the fstar-coder agent to write a Pulse function that verifies
 agent memory ownership with the frame rule for a Hermes-style
 MEMORY.md bounded to 2200 characters"
```

```text
"Use the fstar-coder agent to write an F* spec that verifies
 a tool call's arguments are within the declared API surface
 and its return value matches the expected output type"
```

Use `smtprofiling` if Z3 discharge is slow:

```text
"Use the smtprofiling skill to diagnose why P8 concurrency proof
 is timing out"
```

### Deploy to Cluster

```bash
# Create verification gateway
kubectl apply -f project-praxis/deployment.yaml

# Patch kagent agent pods with Praxis sidecar
kubectl -n kagent patch deployment kagent-controller \
  --patch-file project-praxis/sidecar-patch.yaml
```

## Technology Stack

| Component | Technology | License |
|-----------|-----------|---------|
| Proof language | F\* + Pulse (separation logic DSL) | Apache 2.0 |
| SMT solver | Z3 | MIT |
| Agent tooling | Claude Code + proof-copilot plugin | Apache 2.0 |
| Incremental checking | F\* MCP Server (Rust) | Apache 2.0 |
| Compiled proofs | KaRaMeL (F\* → C extraction) | Apache 2.0 |
| Agent sandbox | NVIDIA OpenShell | Apache 2.0 |
| Memory patterns | Hermes Agent / OpenClaw | MIT |
| Observability | OpenTelemetry | Apache 2.0 |

## Status

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Single verified action (P1, P2, P5, P7) | Not started |
| 1 | Content + tool use verification with OWASP test vectors | Not started |
| 2 | Full Pulse substrate model (Hermes + OpenClaw + tool scope) | Not started |
| 3 | Kubernetes integration (sidecar, OTel, Grafana dashboard) | Not started |
| 4 | Multi-agent fleet + EU AI Act compliance trail | Not started |

## References

- [Agentic Proof-Oriented Programming in F\*](https://fstar-lang.org/tutorial/book/agentic/agentic_getting_started.html)
- [FStarLang/proof-copilot](https://github.com/FStarLang/proof-copilot)
- [Pulse DSL for F\*](https://github.com/FStarLang/pulse)
- [PulseCore (PLDI 2025)](https://fstar-lang.org/papers/pulsecore.pdf)
- [NVIDIA OpenShell](https://github.com/NVIDIA/OpenShell)
- [Hermes Agent Memory System](https://hermes-agent.org/)
- [OpenClaw Memory Architecture](https://docs.openclaw.ai/concepts/memory)
- [AxDafny: Verified Code Generation](https://axiomatic-ai.com/blog/axdafny/)
- [RAND: Verified ML Infrastructure (2026)](https://www.rand.org/pubs/research_reports/RRA4881-1.html)
