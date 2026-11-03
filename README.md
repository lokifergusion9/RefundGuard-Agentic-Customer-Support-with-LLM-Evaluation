<div align="center">

# 🛟 Customer Support Resolution Agent

**An AI agent that takes a complaint from *"where is my refund?"* to a *verified* outcome,<br>
plus an evaluation platform that measures whether it can be trusted with money.**

[![CI](https://github.com/lokifergusion9/Agentic-AI-Customer-Support-System/actions/workflows/ci.yml/badge.svg)](https://github.com/lokifergusion9/Agentic-AI-Customer-Support-System/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-workflow-1C3C3C)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?logo=postgresql&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini-free%20tier-8E75B2?logo=googlegemini&logoColor=white)
![Tests](https://img.shields.io/badge/tests-911%20passing-2ea44f)
![License](https://img.shields.io/badge/license-MIT-blue)

[How it works](#-how-it-works) · [Safety](#-safety-by-design) · [Evaluation](#-the-evaluation-platform) · [Results](#-results) · [Quickstart](#-quickstart) · [Demos](#-demos) · [API](#-api) · [Project layout](#-project-layout)

</div>

> [!IMPORTANT]
> **The one rule:** the model *proposes*; the application *decides* and *executes* through typed tools.
> No refund is ever issued without a human approval bound to one exact, immutable proposal.

<table>
<tr>
<td align="center"><b>3</b><br><sub>complaint types</sub></td>
<td align="center"><b>11</b><br><sub>typed tools</sub></td>
<td align="center"><b>50</b><br><sub>versioned eval tasks</sub></td>
<td align="center"><b>248</b><br><sub>real-model eval runs</sub></td>
<td align="center"><b>0</b><br><sub>duplicate refunds</sub></td>
<td align="center"><b>911</b><br><sub>deterministic tests</sub></td>
</tr>
</table>

## 🎯 The problem

An LLM support agent that can *talk* about refunds is easy. One that can be *trusted to issue* them is not: it must never refund the wrong customer, never refund twice when a network call times out, never claim *"your refund is done"* before the payment provider confirms it, and never treat a chat message as an approval.

This project builds that agent for a fictional electronics store (**order status**, **refund request**, **damaged item**; one currency, INR stored in paise), and then builds the harness that proves those properties hold, run after run, by checking the **business state** rather than the wording.

## 🧭 How it works

```mermaid
flowchart LR
    A["💬 Complaint"] --> B["Classify"]
    B --> C["Investigate facts<br/>+ retrieve policy"]
    C --> D["Resolution<br/>proposal"]
    D --> E{"Eligibility<br/>rules in code"}
    E -->|"refund"| F["⏸ Human approval<br/>(durable pause)"]
    E -->|"answer / clarify / escalate"| H
    F --> G["Execute → verify<br/>with the provider"]
    G --> H["🎫 Ticket update<br/>(confirmed facts only)"]
    classDef llm fill:#ede7f6,stroke:#5e35b1,color:#1a1a1a
    classDef code fill:#e8f5e9,stroke:#2e7d32,color:#1a1a1a
    classDef human fill:#fff3e0,stroke:#ef6c00,color:#1a1a1a
    class B,C,D llm
    class E,G,H code
    class F human
```

<sub>🟣 the model proposes · 🟢 ordinary code decides and executes · 🟠 a person approves</sub>

1. **Classify** the complaint; anything outside the three supported types is escalated.
2. **Investigate** with read-only tools (orders, shipment, return, payment, ticket) while a **policy** specialist retrieves cited passages, concurrently when they are independent.
3. **Propose** a resolution that matches a validated schema. Invalid output gets one limited repair, then the run stops or escalates.
4. **Decide in code:** eligibility, refundable balance and amounts are computed deterministically, never by the model.
5. **Pause** for a reviewer with LangGraph `interrupt()` and a PostgreSQL checkpointer; the run survives restarts and resumes on the same thread.
6. **Execute and verify:** one idempotent provider call, then confirm the result with the provider before telling anyone it happened.
7. **Update the ticket** only with the verified status. Every step lands in a redacted, append-only audit trail.

### Architecture

```mermaid
flowchart TB
    subgraph clients["Clients"]
        C1["Customer<br/>(JWT)"]
        C2["Reviewer<br/>/review"]
        C3["Operator<br/>/ui/*"]
    end
    subgraph app["Agent service · FastAPI"]
        API["Tickets · Runs · Approvals API"]
        WF["LangGraph workflow<br/>classifier · investigation · policy · resolution"]
        GW["Tool gateway<br/>identity injected · typed args · retries"]
        SV["Services<br/>ownership · eligibility · proposals · refunds · audit"]
        JOB["Job queue + worker<br/>SKIP LOCKED · reconciliation sweep"]
    end
    subgraph evals["Evaluation platform"]
        EAPI["/eval API + screens"]
        RUN["Experiment runner<br/>clean environment per attempt"]
        EV["4 deterministic evaluators<br/>outcome · policy · trajectory · response"]
    end
    subgraph data["PostgreSQL + pgvector"]
        DB1[("support schema<br/>orders · proposals · approvals<br/>refund_operations · audit_events")]
        DB2[("checkpoints")]
        DB3[("eval schema")]
    end
    subgraph mocks["Mock providers (fault injection)"]
        P["Payments"]
        S["Shipping"]
        T["Ticketing"]
    end
    LLM["Gemini<br/>(free tier)"]
    C1 & C2 --> API --> WF --> GW --> SV
    WF <--> LLM
    API --> JOB --> WF
    SV --> DB1
    WF --> DB2
    SV --> P & S & T
    C3 --> EAPI --> RUN --> WF
    RUN --> EV --> DB3
```

Thirteen detailed diagrams (approval pause/resume, refund reconciliation, crash recovery, both database schemas, agent-vs-evaluator data) live in [`docs/diagrams`](docs/diagrams/README.md), exported from [`hld.md`](hld.md).

## 🔒 Safety by design

| Guarantee | How it is enforced | Proven by |
|---|---|---|
| **Identity** comes from auth, never the model | The customer is resolved from the JWT and injected into every tool call; reviewer identity, approval status and credentials are never tool arguments. | `test_customer_auth.py`, `test_tools.py` |
| **Ownership** is checked server-side | Every service filters by the authenticated customer. Another customer's order returns `ORDER_NOT_FOUND`, revealing nothing. | `test_read_services.py` |
| **Approval** is bound to an exact proposal | Proposals are immutable (DB trigger) and hashed; the stored reviewer decision is re-checked against the hash before execution. Chat text authorizes nothing. | `test_approvals.py`, `test_workflow.py` |
| **Stale approvals** need a fresh one | An expired approval, or a changed amount or order, invalidates the old approval and requests a new one. | `test_workflow.py` |
| **No double refunds** | Stable idempotency key with a unique constraint, balance reserved under `SELECT … FOR UPDATE`, no transaction held during the network call. | `test_refund_concurrency.py` |
| **Lost responses** are reconciled | If the provider accepts a refund but the reply times out, the app asks the provider by key before retrying or claiming success; restarts reconcile first. | `test_recovery.py`, `tests/failure_scenarios/` |
| **Policies (RAG)** are evidence, not proof | Versioned documents filtered by effective date, cited as `refund_policy_v1:section_3`. Retrieved text is untrusted; a similarity score never makes a refund eligible. | `test_policy_search.py` |
| **The model never holds the money tool** | `execute_approved_refund` is never offered to the model; only the workflow calls it after a valid approval. | `app/tools/registry.py` |

## 📊 The evaluation platform

> *If I change the model, the prompt, the tools or the orchestration, does the agent become more reliable, and at what cost?*

- **50 versioned tasks** (`support-v1`) across 9 categories: lookups, eligible and ineligible refunds, damaged items, missing information, access boundaries, tool failures, duplicate operations and prompt injection. Split by scenario family into dev 30 · validation 10 · test 10.
- **Two views per task:** the agent sees only the customer's message and identity; the expected outcome, forbidden actions and invariants stay in a hidden *evaluator view*.
- **A clean world per attempt:** business tables and mocks are reset, the fixture is loaded, faults are injected (5xx, delays, *"accept the refund, then time out"*), and the final state is snapshotted.
- **Four deterministic evaluators** score the resulting **system state**: *outcome* (refunds, ticket and run status), *policy* (forbidden effects, invariants), *trajectory* (tool use) and *response* (required facts, no false claims). No LLM judge decides whether money moved correctly.
- **Honest accounting:** every rate shows its denominator, coverage sits next to success, missing token usage is *unknown* (never zero), blocked unsafe attempts are reported apart from executed violations, and human-assisted resolutions are separate from fully automated ones.
- **Reproducible:** each experiment saves a manifest (dataset hash, model IDs, prompt and tool-schema hashes, commit, lockfile hash, fault config) and can be rerun and compared task by task.

<details open>
<summary><b>📸 Screens</b> (real data from the main experiment)</summary>
<br>

**Scorecard:** several numbers per configuration, each with its denominator and a 95% confidence interval.

<img src="docs/images/eval-experiment.png" alt="Experiment scorecard for the main experiment" width="100%">

**Comparison:** the exact tasks that regressed between prompt v1 and v2, and which checks failed.

<img src="docs/images/eval-compare.png" alt="Comparison of lite_specialist_v1 against lite_specialist_v2" width="100%">

**One run:** what the agent saw beside the hidden ground truth, with every evaluator finding linked to the trace event that caused it.

<img src="docs/images/eval-run-violation.png" alt="A failed run showing the agent view, the ground truth and evaluator findings" width="100%">

</details>

## 📈 Results

> [!NOTE]
> Synthetic tasks against mock services, measured on the Gemini free tier. These are **not production numbers**, and every row names its dataset, split, metric and sample.

| Experiment | Split | Configuration | Verified success | Sample |
|---|---|---|---|---|
| Main | all 50 | `lite_single_v1` | **76%** (38/50) | 50 tasks × 1 |
| Main | all 50 | `lite_specialist_v1` | **84%** (42/50) | 50 tasks × 1 |
| Main | all 50 | `lite_specialist_v2` | **70%** (35/50) · 1 executed policy violation | 50 tasks × 1 |
| Repetitions | validation | `lite_single_v1` | 63% (19/30) | 10 tasks × 3 |
| Repetitions | validation | `lite_specialist_v1` | 57% (17/30) | 10 tasks × 3 |
| Model comparison | validation | `flash_specialist_v1` | 62.5% (5/8 scored; 2 of 10 not run) | 8 tasks × 1 |
| Final test | test | single / specialist v1 / specialist v2 | 70% / 90% / 100% (of 10 each) | 10 tasks × 1 |
| Pilot | pilot | `lite_specialist_v1` | 4 pass, 1 partial (of 5) | 5 tasks × 1 |

| Configuration | Model | Design | Prompt | Model calls / run |
|---|---|---|---|---|
| `lite_single_v1` | Gemini 3.5 Flash-Lite | one tool-using agent | v1 | 4.5 |
| `lite_specialist_v1` | Gemini 3.5 Flash-Lite | classifier → investigation ∥ policy → resolution | v1 | 6.3 |
| `lite_specialist_v2` | Gemini 3.5 Flash-Lite | specialists | v2 | 6.2 |
| `flash_specialist_v1` | Gemini 3.5 Flash | specialists | v1 | 9.0 |

**What the numbers do and do not show**

- ✅ **Safety held:** no duplicate refund in any of the 248 runs. One `lite_specialist_v2` run (`missing_order_refund_001`) committed a forbidden action, and the policy evaluator caught it.
- 📉 **Prompt v2 regressed** on the main run: 2 tasks improved, 9 regressed (sign test p = 0.065) at about the same tool calls and latency. On the 10 test tasks the order flipped (v2 100%, v1 90%), and 10 tasks cannot settle it.
- ⚖️ **No claim that specialists beat the single agent:** they led on the main run (84% vs 76%, p = 0.34) but trailed on the repeated validation split (57% vs 63%), at about 1.8 more model calls and 3 s more per run.
- 🔬 **Flash vs Flash-Lite:** 1 task improved, none regressed, 7 unchanged (p = 1.0, no evidence of a difference), at about 2.9 more model calls and twice the tokens per run. Only 8 of 10 tasks ran (Flash allows 20 requests a day), and its latency includes rate-limit waits.
- 🧪 **Held-out caveat:** the main run used all 50 tasks, so the test tasks were also in it. Prompts were frozen before any result was read, but the final test is not an untouched held-out measurement.

Reports (manifest, scorecard, one row per run, as JSON and CSV) are in [`evals/reports/`](evals/reports): main `exp_c6c886a14af3ffc6`, repetitions `exp_9a559ab45cc6d678`, final test `exp_d580a81b47a3fd20`, model comparison `exp_0cdb09b5f180fe0c`.

## 🚀 Quickstart

**Requirements:** Python 3.13, [uv](https://docs.astral.sh/uv/), Docker. **No API key** is needed for the scripted path below.

```bash
git clone https://github.com/lokifergusion9/Agentic-AI-Customer-Support-System.git
cd Agentic-AI-Customer-Support-System

docker compose up -d postgres                  # PostgreSQL 17 + pgvector on :5432
docker compose --profile mocks up -d           # mock payments :8001, shipping :8002, ticketing :8003

uv run python -m scripts.dev setup             # locked dependencies, .env from .env.example, support_eval DB
uv run python -m scripts.dev migrate           # 19 migrations on both databases
uv run python -m scripts.dev seed              # demo data, policies (embedded locally), the eval dataset
uv run python -m scripts.dev smoke             # expect: 5  completed / pass
```

`make setup migrate seed smoke` does the same where `make` is available. Embeddings run locally (`all-MiniLM-L6-v2`), so no key is needed for retrieval either.

<details>
<summary><b>🔑 Run with a real model</b></summary>

Put a free [Google AI Studio](https://aistudio.google.com/) key in `.env`:

```dotenv
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3.5-flash-lite
LLM_API_KEY=your-key
```

Then run a demo on the real model, or an experiment plan from [`evals/plans/`](evals/plans):

```bash
uv run python -m scripts.dev demo a --config lite_specialist_v1
uv run python -m scripts.dev evaluate --plan pilot      # 5 tasks; jobs wait for quota instead of failing
uv run python -m scripts.dev report <experiment_id>     # JSON + CSV into evals/reports/
```

</details>

<details>
<summary><b>🖥️ Run the servers</b></summary>

```bash
uv run uvicorn app.main:app --reload                 # agent API · /docs · /demo · /review
uv run python -m scripts.mint_token "auth|alice"     # customer JWT (also --role reviewer|senior_reviewer|operator)
uv run python -m app.jobs.worker                     # worker, when RUN_EXECUTION=worker
uv run python -m scripts.recover                     # reconcile uncertain refunds, resume unfinished runs
```

The evaluation screens read the `support_eval` database: point `DATABASE_URL` at it, then
`uv run uvicorn evals.api:app --port 8100` and open `/ui/experiments` with an operator token.

</details>

## 🎬 Demos

Each demo checks the **system state** (provider refunds, proposals, ticket status, evaluator verdict) and exits non-zero if a step fails. Details: [`docs/demo-scenarios.md`](docs/demo-scenarios.md).

| | Scenario | What it proves | Command |
|---|---|---|---|
| **A** | ✅ Approved refund | complaint → evidence → reviewer approves → exactly one provider refund → ticket resolved | `demo a` |
| **B** | 🚫 Blocked request | an ineligible refund is explained with policy, and no money moves | `demo b` |
| **C** | 🔁 Failure recovery | the provider accepts but the reply is lost; the app reconciles by key: still one refund | `demo c` |
| **D** | 🎭 Convincing but wrong | the reply says "refund issued" while the provider holds none, and the evaluators catch it *(scripted fake agent)* | `demo d` |
| **E** | ⚖️ A prompt tradeoff | which tasks improved or regressed between prompt v1 and v2, read from the real main experiment | `demo e --baseline exp_c6c886a14af3ffc6 --candidate exp_c6c886a14af3ffc6` |

All commands are `uv run python -m scripts.dev …`. A to D run without an API key.

## 🔌 API

<details>
<summary><b>Agent service</b> (<code>app.main:app</code>)</summary>

| Method | Path | Who | Purpose |
|---|---|---|---|
| `GET` | `/health` | public | Database health |
| `POST` | `/tickets` | customer | Open a ticket (ownership-checked `order_id`) |
| `POST` | `/tickets/{ticket_id}/runs` | customer | Start a resolution run (`201` inline, `202` with the worker) |
| `GET` | `/runs/{run_id}` | customer | Run status and output |
| `GET` | `/runs/{run_id}/events` | customer | Redacted event timeline |
| `POST` | `/runs/{run_id}/messages` | customer | Answer a clarification question; the run resumes |
| `GET` | `/approvals` | reviewer | Pending approvals this reviewer may decide |
| `POST` | `/approvals/{approval_id}/decision` | reviewer | Approve or reject; the run resumes |
| `GET` | `/demo`, `/review` | browser | Demo and reviewer screens |

Refunds above ₹50,000 need a `senior_reviewer`.

</details>

<details>
<summary><b>Evaluation API</b> (<code>evals.api:app</code>, under <code>/eval</code>, <code>operator</code> role only)</summary>

| Method | Path | Purpose |
|---|---|---|
| `POST` / `GET` | `/eval/datasets/import`, `/eval/datasets` | Import and list versioned datasets |
| `POST` / `GET` | `/eval/agent-configs` | Register and list immutable agent configurations |
| `POST` / `GET` | `/eval/experiments` | Create and list experiments |
| `GET` | `/eval/experiments/{id}` · `/runs` · `/export` | Scorecard, runs, report download |
| `POST` | `/eval/experiments/{id}/cancel` | Cancel queued runs |
| `GET` | `/eval/runs/{run_id}`, `/eval/attempts/{attempt_id}/events` | Run detail and trace |
| `POST` | `/eval/comparisons` | Compare two compatible experiments task by task |
| `GET` | `/ui/experiments`, `/ui/runs/{id}`, `/ui/compare` | Screens |

</details>

## 🗂️ Project layout

```text
customer-support-resolution-agent/
├── app/                    # the agent service
│   ├── api/                #   FastAPI routes: tickets, runs, approvals, health
│   ├── auth/               #   JWT, customer and reviewer roles
│   ├── agents/             #   specialists, the agent loop, versioned prompts (v1, v2)
│   ├── workflows/          #   LangGraph graph, state, validation, checkpoints, recovery
│   ├── tools/              #   typed tool registry and the gateway that injects identity
│   ├── services/           #   business logic: ownership, eligibility, proposals, refunds, audit
│   ├── policies/           #   policy documents, embeddings and cited search
│   ├── llm/                #   Gemini adapter, call accounting
│   ├── jobs/               #   PostgreSQL job queue and worker
│   ├── schemas/            #   Pydantic request, response and agent-output models
│   └── web/                #   /demo and /review screens (Jinja2)
├── evals/                  # the evaluation platform
│   ├── adapters/           #   LangGraph agent and scripted test-double adapters
│   ├── evaluators/         #   outcome, policy, trajectory, response
│   ├── datasets/support-v1/#   50 tasks and their splits
│   ├── plans/              #   experiment manifests (pilot, main, repetitions, ...)
│   ├── reports/            #   exported results
│   └── web/                #   experiment, run and comparison screens
├── mock_services/          # payments, shipping, ticketing, with fault injection
├── migrations/             # 19 hand-written Alembic migrations
├── scripts/                # dev commands, seed, demos, token minting, recovery
├── tests/                  # unit, integration, failure scenarios, evals
├── docs/                   # diagrams, demo guide, screenshots
├── hld.md                  # high-level design (source of the diagrams)
└── tasks.md                # every task, decision and its status
```

## 🧰 Tech stack

| Area | Choice |
|---|---|
| Language and tooling | Python 3.13, uv (locked), ruff, pytest |
| Orchestration | LangGraph with a PostgreSQL checkpointer (`interrupt()` / `Command(resume=…)`) |
| API and screens | FastAPI, Pydantic v2, Jinja2 with light JavaScript |
| Data | PostgreSQL 17, pgvector, SQLAlchemy 2, Alembic |
| Models | Gemini via `google-genai` (Flash-Lite and Flash, free tier); local `all-MiniLM-L6-v2` embeddings |
| Infrastructure | Docker Compose, GitHub Actions CI (ruff + the full suite on a pgvector service) |

## 🧪 Testing

```bash
uv run python -m scripts.dev test        # 911 deterministic tests, no model calls
uv run pytest -m embedding_model         # opt-in: the real embedding model
uv run pytest -m llm                     # opt-in: real Gemini calls (uses quota)
```

The suite covers the schema and its constraints, ownership and auth, eligibility, idempotent and concurrent refunds, approval expiry and invalidation, crash recovery, one test per failure scenario in [`tests/failure_scenarios/`](tests/failure_scenarios), and the evaluation platform itself (including broken scripted agents that each evaluator must catch).

<details>
<summary><b>⚙️ Configuration notes</b></summary>

- Two databases on purpose: `support` (the app) and `support_eval` (experiments empty its business tables on every attempt). Eval commands always target `support_eval`, and the worker refuses any database not named `*_eval` or `*_test`.
- `RUN_EXECUTION=inline` drives a run inside the request; `worker` returns `202` and a worker drives it.
- Approvals expire after `APPROVAL_EXPIRY_MINUTES` (60). Runs stop at `MAX_WORKFLOW_STEPS` (25) or `MAX_RUN_TOKENS` (50,000).
- Money is stored in integer minor units. Provider calls time out after `PROVIDER_TIMEOUT_SECONDS` (5), so timeout faults really time out.
- Every variable is listed in [`.env.example`](.env.example); no secret is committed.

</details>

## ⚠️ Limitations

- One fictional store, one currency, 50 hand-written tasks and mock providers: nothing here measures real traffic.
- Small samples: 50 tasks, 3 repetitions on 10, and a partial model comparison. Most differences between configurations are not statistically significant.
- Approvals are simulated in evaluations; the evaluators are deterministic (no LLM judge, no public benchmarks yet).
- Cost is reported as unknown because no prices are registered; the free tier costs nothing.
- Demo C simulates the restart; the real mid-flight kill is covered by a failure-scenario test.
- Out of scope: chargebacks, fraud decisions, complex partial returns, messaging channels beyond the demo screens.

**Possible next steps:** public agent benchmarks (BFCL, τ²-bench), an LLM judge for response quality only, concurrent attempts per environment, and a recorded walkthrough of demos A to E.

## 📄 License

[MIT](LICENSE). All data in this repository is synthetic.
