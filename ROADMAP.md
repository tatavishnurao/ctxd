# Engineering roadmap

Objectives, not another mechanically numbered research phase. No work below was started by this consolidation beyond documentation and validation.

## NEXT

### A. Ground truth and benchmark completion

Audit all 106 candidates and record dispositions for all 121 historical cases; verify exact span occurrence, necessary/sufficient evidence, alternatives, joint obligations, provenance and measured difficulty. Complete leakage/fact/template audit, deterministic provisional split, versioned review tooling and diverse review batches. Obtain real independent human review, preserve corrections/disagreements, then generate a fresh final split. Canonical scoring remains blocked until those gates pass. Historical 121-case tooling cannot silently approve the 106-case revision.

### D. Production reliability

Specify trusted tenant authentication/authorization, deployment secrets, dependency/model provisioning and database backup/restore procedures. Define readiness separate from liveness, test operational recovery and document ownership of timeouts/capacity. Do not claim production readiness from integration tests alone.

### E. Observability

Document existing metric/span contracts and provide an operational runbook. Establish isolated-host latency baselines/SLO requirements and correlate client/server resource signals before diagnosing historical spikes. Preserve raw anomaly evidence; do not guess a cause.

## LATER — conditional on requirements and reviewed evidence

### B. Context selection

Only revisit alternatives when reviewed evidence/provenance labels support preservation gates. Greedy remains the default. No tuning or new selector is justified by source-level token savings alone.

### C. Retrieval scalability

Profile exact pgvector and large posting sets under a specified deployment workload. Measure index/storage/update tradeoffs and quality gates before revisiting ANN. Current tested HNSW result is not a deployment recommendation.

### F. Eventual model/runtime integration

First define output contracts, tokenizer/budget semantics, inference failures, cost/security requirements and model-artifact lifecycle. Existing response/model schemas do not implement a router or inference runtime.

### G. Eventual agent/tool runtime

Requires a separate security design for authorization, sandbox boundaries, tool lifecycle, budgets and auditing. MCP fixture evaluation is not tool execution. Agent loops, SSE and frontend remain future work.

## NOT CURRENTLY JUSTIFIED

Another reranker/model sweep, BM25/embedding/RRF tuning, packing promotion, ANN defaults, unreviewed holdout scoring, invented LLM judgments, or expansion into full agent/UI runtime. First complete ground truth and operational engineering.

## Top five next priorities

1. Finish case/disposition/span/provenance/leakage audit without retrieval outcomes.
2. Complete versioned review tooling/packets/batches and obtain independent review.
3. Establish trusted tenant authorization and deployment configuration contract.
4. Define readiness/recovery/model provisioning and database runbooks.
5. Establish isolated-host observability/capacity evidence with declared SLOs.

## Safe git checkpoint plan (proposal only)

Base before consolidation: `83352ac`, clean tree. No history rewriting and no automatic commits/pushes. Preserve historical reports/artifacts and checksums. Suggested reviewed commits:

1. `docs: clarify implemented scope and runtime defaults` — README, ARCHITECTURE, CURRENT_STATE.
2. `docs: index experiments and engineering priorities` — EXPERIMENTS, ROADMAP, PERFORMANCE/BENCHMARKS navigation.
3. `docs: record engineering audit and evidence inventory` — docs audit, validation manifest, checksum inventory.

Review the diff and run inventory checksum verification and the full dedicated-DB suite before committing. No release tag until authorized. Recommended descriptive checkpoint: **retrieval-research-checkpoint**, not alpha/production release. Existing package/service version need not be changed to imply new maturity.
