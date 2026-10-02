# Phase 10 independent review packet

**PROVISIONAL — NOT INDEPENDENTLY REVIEWED**

Authentic pinned repository text; agent-authored questions and proposed labels. This packet alone does NOT establish canonical eligibility or holdout blinding.

## Reviewer instructions

Review every holdout case and at least 50% of development (41 of 82), covering every development family. Prefer all cases. Review source context, not merely matching strings. Do not inspect retrieval/ranking outcomes while authoring or correcting labels.

For EACH case: check question clarity/version scope; exact span/source/tenant; sufficiency and minimality; AND spans versus OR alternatives; optional/supporting roles; independently required provenance; missing valid alternative chunks; and measured whole-chunk feasibility. Identical text at different resources is not interchangeable.

Author status is DRAFT, not VERIFIED_BY_AUTHOR. Exact-string checks are mechanical and do not certify sufficiency. Repeated snippet occurrences use the first source occurrence; verify that it is the intended function/branch. Mark CORRECTED or DISPUTED if labels are overbroad, underspecified or attached to the wrong occurrence.

APPROVED requires a real independent human's identity, timezone-aware timestamp, explicit human attestation and substantive notes. Self-review is rejected. The tool checks the attestation contract; it does NOT authenticate people or prove they read a case. Retain externally verifiable review evidence. Never have an assistant invent approval.

CORRECTED requires a versioned revision and fresh review; it is not scoring approval. Preserve old dataset/review files and assignments. Recompute locators, costs, split hashes and packets. Do not select corrections using holdout outcomes. DISPUTED blocks that case until an explicit, documented resolution. Corrections cannot be laundered through status transitions into approval of unchanged labels.

## Apply one human submission

Create a JSON object with these exact keys: dataset_sha256, previous_review_sha256, case_id, case_sha256, status (APPROVED/CORRECTED/DISPUTED), reviewer_id, human_attestation, reviewed_at, notes. Copy hashes below; use your real identity, actual review date and findings. No prefilled approval example is supplied.

Run `uv run python benchmarks/phase10_review.py apply --submission /path/to/human.json --state evals/phase10_review_state.json --output evals/phase10_review_round1.json`. For the next submission use the previous round as --state and a fresh output path. The parent hash prevents stale/parallel submissions from silently overwriting a review. Render a new packet with `render --state ... --output /new/packet.md`.

Dataset SHA-256: `59d59de6350279834c611ff9b30ee68b11e3577ba2a2db348b50d13327e91748`

Review state SHA-256: `fc3fbc6c2b18eeeb43f0f96052325e608831a0cd5753f26fe0fd51ff0b54693b`

Full immutable documents and chunks: `evals/phase10_evidence_cases.json`. Original-source character and line locators: `evals/phase10_source_locators.json`. Source provenance/permission notes: `evals/phase10_source_manifest.json`.

## Cases

### phase10-001 — What distinguishes missing tenant headers from a mismatched body tenant in _require_tenant?

Partition: holdout; family: api; kind: exact_symbol.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `79bdfc6f3a96ebe825f5162bd1d89acd32f0f330845527031789fa3d8222150c`

Proposed stratum: EASY; minimum whole chunks: 265 approximate tokens; span lower bound: 33.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/api/routes.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/api/routes.py#L1-L47) — chunk `chk_b3ddced4a9198329d7ea9183`, half-open characters [775, 812).

````text
if authenticated_tenant == "unknown":
````

- [ctxd/app/api/routes.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/api/routes.py#L1-L47) — chunk `chk_b3ddced4a9198329d7ea9183`, half-open characters [907, 947).

````text
detail="x-tenant-id header is required",
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/api/routes.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/api/routes.py#L1-L47) — chunk `chk_b3ddced4a9198329d7ea9183`, half-open characters [962, 1004).

````text
if authenticated_tenant != claimed_tenant:
````

- [ctxd/app/api/routes.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/api/routes.py#L1-L47) — chunk `chk_b3ddced4a9198329d7ea9183`, half-open characters [1046, 1084).

````text
status_code=status.HTTP_403_FORBIDDEN,
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-002 — How does document ingestion distinguish invalid content from unavailable storage at the HTTP boundary?

Partition: holdout; family: api; kind: failure.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `28717283fa9496c7f9827872615c561dc251ae7718dfe749a41208164e88bcd2`

Proposed stratum: EASY; minimum whole chunks: 357 approximate tokens; span lower bound: 20.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/api/routes.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/api/routes.py#L50-L108) — chunk `chk_8547c2f87b96f33a8231cb07`, half-open characters [592, 624).

````text
except DocumentLoadError as exc:
````

- [ctxd/app/api/routes.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/api/routes.py#L50-L108) — chunk `chk_8547c2f87b96f33a8231cb07`, half-open characters [666, 716).

````text
status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/api/routes.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/api/routes.py#L50-L108) — chunk `chk_8547c2f87b96f33a8231cb07`, half-open characters [899, 940).

````text
detail="document storage is unavailable",
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-003 — When does the document POST return 200 rather than its declared 201?

Partition: holdout; family: api; kind: contract.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `08aeb1814de1c951aa588df4529b9186fe0cf6deb108b76b60e54b6758a89437`

Proposed stratum: EASY; minimum whole chunks: 357 approximate tokens; span lower bound: 11.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/api/routes.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/api/routes.py#L50-L108) — chunk `chk_8547c2f87b96f33a8231cb07`, half-open characters [964, 979).

````text
if not created:
````

- [ctxd/app/api/routes.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/api/routes.py#L50-L108) — chunk `chk_8547c2f87b96f33a8231cb07`, half-open characters [988, 1029).

````text
response.status_code = status.HTTP_200_OK
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-004 — Does a retrieval timeout have the same query API response as a general storage error?

Partition: holdout; family: api; kind: failure.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `a8573e517abd8e9560cef886ec9ea67d64a87383925894660b3f701304566423`

Proposed stratum: EASY; minimum whole chunks: 357 approximate tokens; span lower bound: 20.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/api/routes.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/api/routes.py#L50-L108) — chunk `chk_8547c2f87b96f33a8231cb07`, half-open characters [1590, 1626).

````text
except RetrievalTimeoutError as exc:
````

- [ctxd/app/api/routes.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/api/routes.py#L50-L108) — chunk `chk_8547c2f87b96f33a8231cb07`, half-open characters [1668, 1712).

````text
status_code=status.HTTP_504_GATEWAY_TIMEOUT,
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/api/routes.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/api/routes.py#L50-L108) — chunk `chk_8547c2f87b96f33a8231cb07`, half-open characters [1908, 1952).

````text
detail="retrieval subsystem is unavailable",
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-005 — Does QueryResponse contain an inferred answer or a model-routing decision today?

Partition: holdout; family: api; kind: negative.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `611a8ed428f3f0c93c5fb445f1407de79956cad77bf077e173cfdd8d26d2939e`

Proposed stratum: EASY; minimum whole chunks: 357 approximate tokens; span lower bound: 15.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/api/routes.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/api/routes.py#L50-L108) — chunk `chk_8547c2f87b96f33a8231cb07`, half-open characters [2006, 2049).

````text
answer="Inference is not implemented yet.",
````

- [ctxd/app/api/routes.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/api/routes.py#L50-L108) — chunk `chk_8547c2f87b96f33a8231cb07`, half-open characters [2169, 2189).

````text
model_decision=None,
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-006 — What are the default retrieval mode, context budget and result limit in QueryRequest?

Partition: holdout; family: api; kind: configuration.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `c7ce4bc12683dba7e5b4e6a17c15704ddda7c94353a9b0f91009b6cc29bfc907`

Proposed stratum: EASY; minimum whole chunks: 388 approximate tokens; span lower bound: 26.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/models/domain.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/models/domain.py#L1-L72) — chunk `chk_fd81127514384965e10f6973`, half-open characters [661, 714).

````text
retrieval_mode: RetrievalMode = RetrievalMode.LEXICAL
````

- [ctxd/app/models/domain.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/models/domain.py#L1-L72) — chunk `chk_fd81127514384965e10f6973`, half-open characters [752, 791).

````text
max_context_tokens: PositiveInt = 8_000
````

- [ctxd/app/models/domain.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/models/domain.py#L1-L72) — chunk `chk_fd81127514384965e10f6973`, half-open characters [796, 842).

````text
top_k: PositiveInt = Field(default=10, le=100)
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-007 — Which upper bounds apply to query text, tenant identity and top_k?

Partition: holdout; family: api; kind: limits.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `6743bebdcd0661abc0dc87959603422cd620474ab8481ef1767638ae3352a454`

Proposed stratum: EASY; minimum whole chunks: 388 approximate tokens; span lower bound: 48.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/models/domain.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/models/domain.py#L1-L72) — chunk `chk_fd81127514384965e10f6973`, half-open characters [529, 580).

````text
query: str = Field(min_length=1, max_length=20_000)
````

- [ctxd/app/models/domain.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/models/domain.py#L1-L72) — chunk `chk_fd81127514384965e10f6973`, half-open characters [585, 656).

````text
tenant_id: str = Field(default="default", min_length=1, max_length=200)
````

- [ctxd/app/models/domain.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/models/domain.py#L1-L72) — chunk `chk_fd81127514384965e10f6973`, half-open characters [796, 842).

````text
top_k: PositiveInt = Field(default=10, le=100)
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-008 — Where do request correlation identifiers come from and how are they returned to callers?

Partition: holdout; family: api; kind: provenance.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `2e3bea41cc56767148002aec2f6fad3e5b2ebb812c62920862e4a3c0f47fbdab`

Proposed stratum: EASY; minimum whole chunks: 380 approximate tokens; span lower bound: 74.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/api/middleware.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/api/middleware.py#L1-L55) — chunk `chk_68a38d2d1f527f6e3d1c543b`, half-open characters [657, 719).

````text
request_id = request.headers.get("x-request-id", str(uuid4()))
````

- [ctxd/app/api/middleware.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/api/middleware.py#L1-L55) — chunk `chk_68a38d2d1f527f6e3d1c543b`, half-open characters [897, 982).

````text
trace_id = f"{span_context.trace_id:032x}" if span_context.is_valid else str(uuid4())
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/api/middleware.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/api/middleware.py#L1-L55) — chunk `chk_68a38d2d1f527f6e3d1c543b`, half-open characters [1514, 1559).

````text
response.headers["x-request-id"] = request_id
````

- [ctxd/app/api/middleware.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/api/middleware.py#L1-L55) — chunk `chk_68a38d2d1f527f6e3d1c543b`, half-open characters [1572, 1613).

````text
response.headers["x-trace-id"] = trace_id
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-009 — How are active-request accounting and request-scoped context variables restored after an exception?

Partition: holdout; family: api; kind: cleanup.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `aef1bc7ac129cbe57cf9f348d5241fa02a8ff4f61ab0ffd6d1458490f69cbdb4`

Proposed stratum: EASY; minimum whole chunks: 380 approximate tokens; span lower bound: 28.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/api/middleware.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/api/middleware.py#L1-L55) — chunk `chk_68a38d2d1f527f6e3d1c543b`, half-open characters [1333, 1350).

````text
status_code = 500
````

- [ctxd/app/api/middleware.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/api/middleware.py#L1-L55) — chunk `chk_68a38d2d1f527f6e3d1c543b`, half-open characters [1650, 1658).

````text
finally:
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/api/middleware.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/api/middleware.py#L1-L55) — chunk `chk_68a38d2d1f527f6e3d1c543b`, half-open characters [1921, 1942).

````text
ACTIVE_REQUESTS.dec()
````

- [ctxd/app/api/middleware.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/api/middleware.py#L1-L55) — chunk `chk_68a38d2d1f527f6e3d1c543b`, half-open characters [1999, 2037).

````text
request_id_var.reset(request_id_token)
````

- [ctxd/app/api/middleware.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/api/middleware.py#L1-L55) — chunk `chk_68a38d2d1f527f6e3d1c543b`, half-open characters [2050, 2086).

````text
tenant_id_var.reset(tenant_id_token)
````

- [ctxd/app/api/middleware.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/api/middleware.py#L1-L55) — chunk `chk_68a38d2d1f527f6e3d1c543b`, half-open characters [2099, 2133).

````text
trace_id_var.reset(trace_id_token)
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-010 — Which retrieval modes and document source types are actually accepted by the request models?

Partition: holdout; family: api; kind: contract.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `e606042862563ef61a767c0354496141e2c7343286b8b21e96b07374fa98eb1a`

Proposed stratum: EASY; minimum whole chunks: 388 approximate tokens; span lower bound: 37.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/models/domain.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/models/domain.py#L1-L72) — chunk `chk_fd81127514384965e10f6973`, half-open characters [391, 420).

````text
class RetrievalMode(StrEnum):
````

- [ctxd/app/models/domain.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/models/domain.py#L1-L72) — chunk `chk_fd81127514384965e10f6973`, half-open characters [425, 444).

````text
LEXICAL = "lexical"
````

- [ctxd/app/models/domain.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/models/domain.py#L1-L72) — chunk `chk_fd81127514384965e10f6973`, half-open characters [449, 470).

````text
SEMANTIC = "semantic"
````

- [ctxd/app/models/domain.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/models/domain.py#L1-L72) — chunk `chk_fd81127514384965e10f6973`, half-open characters [475, 492).

````text
HYBRID = "hybrid"
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/models/domain.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/models/domain.py#L1-L72) — chunk `chk_fd81127514384965e10f6973`, half-open characters [311, 345).

````text
class DocumentSourceType(StrEnum):
````

- [ctxd/app/models/domain.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/models/domain.py#L1-L72) — chunk `chk_fd81127514384965e10f6973`, half-open characters [350, 363).

````text
TEXT = "text"
````

- [ctxd/app/models/domain.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/models/domain.py#L1-L72) — chunk `chk_fd81127514384965e10f6973`, half-open characters [368, 389).

````text
MARKDOWN = "markdown"
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-011 — What environment prefix and dotenv file does Settings read, and how are extra settings treated?

Partition: holdout; family: runtime; kind: configuration.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `4779ba452a826074d75f64b1cf1e7aae6c926cbc4a2fc9870572028906901645`

Proposed stratum: EASY; minimum whole chunks: 300 approximate tokens; span lower bound: 23.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/config/settings.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/config/settings.py#L1-L39) — chunk `chk_783e4ae93945f638b153eb22`, half-open characters [185, 271).

````text
model_config = SettingsConfigDict(env_prefix="CTXD_", env_file=".env", extra="ignore")
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-012 — What connection pool limits and timeout defaults does the service start with?

Partition: holdout; family: runtime; kind: configuration.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `393c5dcfdfb98bbfb7838ce196b6b961fef81660c5590f57302df9862deadf47`

Proposed stratum: EASY; minimum whole chunks: 300 approximate tokens; span lower bound: 58.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/config/settings.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/config/settings.py#L1-L39) — chunk `chk_783e4ae93945f638b153eb22`, half-open characters [646, 698).

````text
database_pool_min_size: int = Field(default=1, ge=0)
````

- [ctxd/app/config/settings.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/config/settings.py#L1-L39) — chunk `chk_783e4ae93945f638b153eb22`, half-open characters [703, 756).

````text
database_pool_max_size: int = Field(default=10, ge=1)
````

- [ctxd/app/config/settings.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/config/settings.py#L1-L39) — chunk `chk_783e4ae93945f638b153eb22`, half-open characters [761, 830).

````text
database_connection_timeout_seconds: float = Field(default=5.0, gt=0)
````

- [ctxd/app/config/settings.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/config/settings.py#L1-L39) — chunk `chk_783e4ae93945f638b153eb22`, half-open characters [835, 894).

````text
database_query_timeout_ms: int = Field(default=5_000, gt=0)
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-013 — Does an explicitly supplied store override storage_backend when creating the runtime?

Partition: holdout; family: runtime; kind: configuration.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `b92bacdd0a18b4295f47d1372bb4bd3fceb4b3951d4c446705af80720d19e359`

Proposed stratum: EASY; minimum whole chunks: 229 approximate tokens; span lower bound: 19.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/runtime.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/runtime.py#L43-L87) — chunk `chk_f22f931d9c3ee42800c88389`, half-open characters [317, 338).

````text
if store is not None:
````

- [ctxd/app/runtime.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/runtime.py#L43-L87) — chunk `chk_f22f931d9c3ee42800c88389`, half-open characters [347, 369).

````text
resolved_store = store
````

- [ctxd/app/runtime.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/runtime.py#L43-L87) — chunk `chk_f22f931d9c3ee42800c88389`, half-open characters [374, 427).

````text
elif resolved_settings.storage_backend == "postgres":
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-014 — Which settings are passed to the real embedding provider, and which to the hash fixture?

Partition: holdout; family: runtime; kind: configuration.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `bf45b5b54b2cfe69b1567264b445129a2896676892906f6b5281b934d463b001`

Proposed stratum: EASY; minimum whole chunks: 229 approximate tokens; span lower bound: 40.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/runtime.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/runtime.py#L43-L87) — chunk `chk_f22f931d9c3ee42800c88389`, half-open characters [933, 988).

````text
if resolved_settings.embedding_provider == "model2vec":
````

- [ctxd/app/runtime.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/runtime.py#L43-L87) — chunk `chk_f22f931d9c3ee42800c88389`, half-open characters [1050, 1098).

````text
cache_dir=resolved_settings.embedding_cache_dir,
````

- [ctxd/app/runtime.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/runtime.py#L43-L87) — chunk `chk_f22f931d9c3ee42800c88389`, half-open characters [1111, 1155).

````text
offline=resolved_settings.embedding_offline,
````

- [ctxd/app/runtime.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/runtime.py#L43-L87) — chunk `chk_f22f931d9c3ee42800c88389`, half-open characters [1168, 1218).

````text
batch_size=resolved_settings.embedding_batch_size,
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/runtime.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/runtime.py#L43-L87) — chunk `chk_f22f931d9c3ee42800c88389`, half-open characters [1304, 1352).

````text
dimension=resolved_settings.embedding_dimension,
````

- [ctxd/app/runtime.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/runtime.py#L43-L87) — chunk `chk_f22f931d9c3ee42800c88389`, half-open characters [1365, 1409).

````text
version=resolved_settings.embedding_version,
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-015 — How does RuntimeServices avoid starting and closing backends without a managed lifecycle?

Partition: holdout; family: runtime; kind: lifecycle.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `cfcd2253d5a03a2e2d155b58a6c8a3627659b2ae4f96ea07116e69a7095affb3`

Proposed stratum: EASY; minimum whole chunks: 237 approximate tokens; span lower bound: 33.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/runtime.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/runtime.py#L1-L45) — chunk `chk_c2e860ad7fb93835d98b7d5a`, half-open characters [856, 880).

````text
def start(self) -> None:
````

- [ctxd/app/runtime.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/runtime.py#L1-L45) — chunk `chk_c2e860ad7fb93835d98b7d5a`, half-open characters [1157, 1199).

````text
if isinstance(self.store, ManagedBackend):
````

- [ctxd/app/runtime.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/runtime.py#L1-L45) — chunk `chk_c2e860ad7fb93835d98b7d5a`, half-open characters [1212, 1230).

````text
self.store.start()
````

- [ctxd/app/runtime.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/runtime.py#L1-L45) — chunk `chk_c2e860ad7fb93835d98b7d5a`, half-open characters [1320, 1338).

````text
self.store.close()
````


Alternative 2: ALL listed spans are jointly required.

- [ctxd/app/runtime.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/runtime.py#L1-L45) — chunk `chk_c2e860ad7fb93835d98b7d5a`, half-open characters [856, 880).

````text
def start(self) -> None:
````

- [ctxd/app/runtime.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/runtime.py#L1-L45) — chunk `chk_c2e860ad7fb93835d98b7d5a`, half-open characters [1157, 1199).

````text
if isinstance(self.store, ManagedBackend):
````

- [ctxd/app/runtime.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/runtime.py#L1-L45) — chunk `chk_c2e860ad7fb93835d98b7d5a`, half-open characters [1212, 1230).

````text
self.store.start()
````

- [ctxd/app/runtime.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/runtime.py#L43-L87) — chunk `chk_f22f931d9c3ee42800c88389`, half-open characters [88, 106).

````text
self.store.close()
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-016 — Are the fake or real embeddings selected by default, and is offline mode enabled initially?

Partition: holdout; family: runtime; kind: negative.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `2ff07ed88fd0055d6e04ac5026085127b34669abd688c5c7867a7cc3766f3a17`

Proposed stratum: EASY; minimum whole chunks: 300 approximate tokens; span lower bound: 21.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/config/settings.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/config/settings.py#L1-L39) — chunk `chk_783e4ae93945f638b153eb22`, half-open characters [899, 956).

````text
embedding_provider: Literal["fake", "model2vec"] = "fake"
````

- [ctxd/app/config/settings.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/config/settings.py#L1-L39) — chunk `chk_783e4ae93945f638b153eb22`, half-open characters [1161, 1192).

````text
embedding_offline: bool = False
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-017 — Trace how runtime creation shares one store and one embedding model between ingestion, both retrievers and assembly.

Partition: holdout; family: runtime; kind: joint_requirements.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `95e417d3d474c428bb727b015a42fd9ac92c11a556b7da0524fa4483145d4495`

Proposed stratum: EASY; minimum whole chunks: 229 approximate tokens; span lower bound: 35.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/runtime.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/runtime.py#L43-L87) — chunk `chk_f22f931d9c3ee42800c88389`, half-open characters [1424, 1510).

````text
ingestion = IngestionService(resolved_store, StructureAwareChunker(), embedding_model)
````

- [ctxd/app/runtime.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/runtime.py#L43-L87) — chunk `chk_f22f931d9c3ee42800c88389`, half-open characters [1515, 1556).

````text
retriever = BM25Retriever(resolved_store)
````

- [ctxd/app/runtime.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/runtime.py#L43-L87) — chunk `chk_f22f931d9c3ee42800c88389`, half-open characters [1561, 1632).

````text
semantic_retriever = SemanticRetriever(resolved_store, embedding_model)
````

- [ctxd/app/runtime.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/runtime.py#L43-L87) — chunk `chk_f22f931d9c3ee42800c88389`, half-open characters [1804, 1862).

````text
assembler=ContextAssembler(retriever, semantic_retriever),
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-018 — Is a document's deterministic identity based on its content or its tenant and source path?

Partition: development; family: ingestion; kind: identity.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `f4d1edf3d636e04925c66819029ee16cf766ee927eeda2f4d1a878cb58807c14`

Proposed stratum: EASY; minimum whole chunks: 370 approximate tokens; span lower bound: 38.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/ingestion/loaders.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/loaders.py#L1-L62) — chunk `chk_9eb7419d2276f0d82847b3fc`, half-open characters [764, 804).

````text
identity = f"{tenant_id}\0{source_path}"
````

- [ctxd/app/ingestion/loaders.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/loaders.py#L1-L62) — chunk `chk_9eb7419d2276f0d82847b3fc`, half-open characters [809, 875).

````text
return f"doc_{hashlib.sha256(identity.encode()).hexdigest()[:24]}"
````

**SUPPORTING supporting-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/ingestion/loaders.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/loaders.py#L1-L62) — chunk `chk_9eb7419d2276f0d82847b3fc`, half-open characters [1467, 1533).

````text
document_id=deterministic_document_id(tenant_id, normalized_path),
````

**OPTIONAL optional-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/ingestion/loaders.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/loaders.py#L1-L62) — chunk `chk_9eb7419d2276f0d82847b3fc`, half-open characters [1669, 1709).

````text
content_hash=content_sha256(normalized),
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-019 — Which line-ending conversions happen before document hashing?

Partition: development; family: ingestion; kind: normalization.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `ecab7013b86446c650a9dc780a909d6cf9ef01268d7710337a7248004333cf7b`

Proposed stratum: EASY; minimum whole chunks: 370 approximate tokens; span lower bound: 43.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/ingestion/loaders.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/loaders.py#L1-L62) — chunk `chk_9eb7419d2276f0d82847b3fc`, half-open characters [525, 581).

````text
return content.replace("\r\n", "\n").replace("\r", "\n")
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/ingestion/loaders.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/loaders.py#L1-L62) — chunk `chk_9eb7419d2276f0d82847b3fc`, half-open characters [1065, 1104).

````text
normalized = normalize_content(content)
````

- [ctxd/app/ingestion/loaders.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/loaders.py#L1-L62) — chunk `chk_9eb7419d2276f0d82847b3fc`, half-open characters [1669, 1709).

````text
content_hash=content_sha256(normalized),
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-020 — What happens if ingest_content receives whitespace-only text?

Partition: development; family: ingestion; kind: failure.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `f8b01b08560b5783f87646ad76fcb22751d9f267d352d6e1b15ba92f6e21c184`

Proposed stratum: EASY; minimum whole chunks: 370 approximate tokens; span lower bound: 18.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/ingestion/loaders.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/loaders.py#L1-L62) — chunk `chk_9eb7419d2276f0d82847b3fc`, half-open characters [1109, 1135).

````text
if not normalized.strip():
````

- [ctxd/app/ingestion/loaders.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/loaders.py#L1-L62) — chunk `chk_9eb7419d2276f0d82847b3fc`, half-open characters [1144, 1196).

````text
raise DocumentLoadError("document content is empty")
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-021 — Which file suffixes can TextFileLoader ingest and how does it reject unsupported types?

Partition: development; family: ingestion; kind: formats.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `15f0b86f1fa95a0ef12c84521329f5068bbf76a80d35ca403f09359ea8aa78c2`

Proposed stratum: EASY; minimum whole chunks: 223 approximate tokens; span lower bound: 43.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/ingestion/loaders.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/loaders.py#L65-L99) — chunk `chk_6a59c9f3411216c1bf86ac59`, half-open characters [45, 77).

````text
".txt": DocumentSourceType.TEXT,
````

- [ctxd/app/ingestion/loaders.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/loaders.py#L65-L99) — chunk `chk_6a59c9f3411216c1bf86ac59`, half-open characters [86, 121).

````text
".md": DocumentSourceType.MARKDOWN,
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/ingestion/loaders.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/loaders.py#L65-L99) — chunk `chk_6a59c9f3411216c1bf86ac59`, half-open characters [363, 386).

````text
if source_type is None:
````

- [ctxd/app/ingestion/loaders.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/loaders.py#L65-L99) — chunk `chk_6a59c9f3411216c1bf86ac59`, half-open characters [399, 474).

````text
raise DocumentLoadError(f"unsupported document type: {suffix or '<none>'}")
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-022 — How are undecodable UTF-8 and filesystem failures distinguished by the file loader?

Partition: development; family: ingestion; kind: failure.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `97e4e54e4eb39e617a164b0f26525de7861af2b21a3b726742ced30daca5e38c`

Proposed stratum: EASY; minimum whole chunks: 223 approximate tokens; span lower bound: 50.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/ingestion/loaders.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/loaders.py#L65-L99) — chunk `chk_6a59c9f3411216c1bf86ac59`, half-open characters [558, 591).

````text
except UnicodeDecodeError as exc:
````

- [ctxd/app/ingestion/loaders.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/loaders.py#L65-L99) — chunk `chk_6a59c9f3411216c1bf86ac59`, half-open characters [604, 683).

````text
raise DocumentLoadError(f"document is not valid UTF-8: {source_path}") from exc
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/ingestion/loaders.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/loaders.py#L65-L99) — chunk `chk_6a59c9f3411216c1bf86ac59`, half-open characters [692, 714).

````text
except OSError as exc:
````

- [ctxd/app/ingestion/loaders.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/loaders.py#L65-L99) — chunk `chk_6a59c9f3411216c1bf86ac59`, half-open characters [727, 808).

````text
raise DocumentLoadError(f"could not read document {source_path}: {exc}") from exc
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-023 — Does unchanged re-ingestion call the embedder and rebuild chunks?

Partition: development; family: ingestion; kind: idempotence.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `4dd977e7d5e967b0764a8bc4b1894e5822aecd514d135491616252982cba7e2d`

Proposed stratum: EASY; minimum whole chunks: 372 approximate tokens; span lower bound: 34.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/ingestion/service.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/service.py#L1-L64) — chunk `chk_7acfed199780cad970465fb6`, half-open characters [2061, 2136).

````text
if existing is not None and existing.content_hash == document.content_hash:
````

- [ctxd/app/ingestion/service.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/service.py#L1-L64) — chunk `chk_7acfed199780cad970465fb6`, half-open characters [2149, 2237).

````text
return existing, self.store.list_chunks(document.tenant_id, document.document_id), False
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-024 — What prevents an embedder returning the wrong number of vectors from silently corrupting document replacement?

Partition: development; family: ingestion; kind: failure.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `a25882b4645f18fc4182d2f6238f251e811ef486fe951959cfb75ad80b998866`

Proposed stratum: EASY; minimum whole chunks: 231 approximate tokens; span lower bound: 33.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/ingestion/service.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/service.py#L66-L89) — chunk `chk_06c8d62848bfc29bb0f1bb38`, half-open characters [571, 602).

````text
if len(vectors) != len(chunks):
````

- [ctxd/app/ingestion/service.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/service.py#L66-L89) — chunk `chk_06c8d62848bfc29bb0f1bb38`, half-open characters [623, 699).

````text
raise RuntimeError("embedding provider returned an unexpected vector count")
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/ingestion/service.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/service.py#L66-L89) — chunk `chk_06c8d62848bfc29bb0f1bb38`, half-open characters [859, 897).

````text
created = self.store.replace_document(
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-025 — For changed content, trace chunk creation, embedding-version capture, atomic replacement and ingestion counters.

Partition: development; family: ingestion; kind: joint_requirements.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `422368f0b8069fcb8796ca68e0dd17350742bf28eb065f8fcd61882fcdd37a57`

Proposed stratum: EASY; minimum whole chunks: 231 approximate tokens; span lower bound: 78.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/ingestion/service.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/service.py#L66-L89) — chunk `chk_06c8d62848bfc29bb0f1bb38`, half-open characters [67, 104).

````text
chunks = self.chunker.chunk(document)
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/ingestion/service.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/service.py#L66-L89) — chunk `chk_06c8d62848bfc29bb0f1bb38`, half-open characters [416, 454).

````text
version = self.embedding_model.version
````

- [ctxd/app/ingestion/service.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/service.py#L66-L89) — chunk `chk_06c8d62848bfc29bb0f1bb38`, half-open characters [471, 554).

````text
vectors = self.embedding_model.embed_documents([chunk.content for chunk in chunks])
````

**REQUIRED required-3** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/ingestion/service.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/service.py#L66-L89) — chunk `chk_06c8d62848bfc29bb0f1bb38`, half-open characters [914, 980).

````text
document, chunks, embedding_version=version, embeddings=embeddings
````

**REQUIRED required-4** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/ingestion/service.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/service.py#L66-L89) — chunk `chk_06c8d62848bfc29bb0f1bb38`, half-open characters [1156, 1221).

````text
INGESTED_DOCUMENTS_TOTAL.labels(document.source_type.value).inc()
````

- [ctxd/app/ingestion/service.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/service.py#L66-L89) — chunk `chk_06c8d62848bfc29bb0f1bb38`, half-open characters [1230, 1303).

````text
INGESTED_CHUNKS_TOTAL.labels(document.source_type.value).inc(len(chunks))
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-026 — What are the default target, hard maximum and overlap sizes for chunking?

Partition: development; family: chunking; kind: configuration.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `8f0649167b59905dc15874196f920ddf3ad365347323d029b2e3db004816705f`

Proposed stratum: EASY; minimum whole chunks: 374 approximate tokens; span lower bound: 15.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/ingestion/chunking.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/chunking.py#L1-L52) — chunk `chk_3680a7c09758b428dce8bb04`, half-open characters [764, 788).

````text
target_tokens: int = 400
````

- [ctxd/app/ingestion/chunking.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/chunking.py#L1-L52) — chunk `chk_3680a7c09758b428dce8bb04`, half-open characters [793, 814).

````text
max_tokens: int = 600
````

- [ctxd/app/ingestion/chunking.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/chunking.py#L1-L52) — chunk `chk_3680a7c09758b428dce8bb04`, half-open characters [819, 843).

````text
overlap_tokens: int = 40
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-027 — Which invalid target, maximum and overlap configurations are rejected?

Partition: development; family: chunking; kind: limits.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `efbca1f45b8e832b9e4923d663900eac8b8f936841ad2f7603be9b80a562f471`

Proposed stratum: EASY; minimum whole chunks: 374 approximate tokens; span lower bound: 33.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/ingestion/chunking.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/chunking.py#L1-L52) — chunk `chk_3680a7c09758b428dce8bb04`, half-open characters [886, 913).

````text
if self.target_tokens <= 0:
````

- [ctxd/app/ingestion/chunking.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/chunking.py#L1-L52) — chunk `chk_3680a7c09758b428dce8bb04`, half-open characters [985, 1025).

````text
if self.max_tokens < self.target_tokens:
````

- [ctxd/app/ingestion/chunking.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/chunking.py#L1-L52) — chunk `chk_3680a7c09758b428dce8bb04`, half-open characters [1124, 1196).

````text
if self.overlap_tokens < 0 or self.overlap_tokens >= self.target_tokens:
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-028 — Is ApproximateTokenCounter a model tokenizer, and what units does its regular expression count?

Partition: development; family: chunking; kind: tokenization.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `f914c7becb56a3b30a02dd88d40994128bfc117ee950e4c484faadd634afe578`

Proposed stratum: EASY; minimum whole chunks: 374 approximate tokens; span lower bound: 40.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/ingestion/chunking.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/chunking.py#L1-L52) — chunk `chk_3680a7c09758b428dce8bb04`, half-open characters [160, 210).

````text
_TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)
````

- [ctxd/app/ingestion/chunking.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/chunking.py#L1-L52) — chunk `chk_3680a7c09758b428dce8bb04`, half-open characters [433, 494).

````text
"""Deterministic word-and-punctuation token approximation."""
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-029 — How does the chunker preserve a fenced Markdown code block while finding its closing fence?

Partition: development; family: chunking; kind: formats.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `733374dcdf77a593eb4c303a68d3ace4c393ed51fad9dfc7a699f927623bff2e`

Proposed stratum: EASY; minimum whole chunks: 418 approximate tokens; span lower bound: 45.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/ingestion/chunking.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/chunking.py#L92-L138) — chunk `chk_57a0e89e3f1b34acbbaabaee`, half-open characters [267, 327).

````text
if stripped.startswith("```") or stripped.startswith("~~~"):
````

- [ctxd/app/ingestion/chunking.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/chunking.py#L92-L138) — chunk `chk_57a0e89e3f1b34acbbaabaee`, half-open characters [366, 386).

````text
fence = stripped[:3]
````

- [ctxd/app/ingestion/chunking.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/chunking.py#L92-L138) — chunk `chk_57a0e89e3f1b34acbbaabaee`, half-open characters [464, 513).

````text
closing = lines[index].lstrip().startswith(fence)
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-030 — When a block exceeds the hard token limit, which boundary is preferred before falling back to a token window?

Partition: development; family: chunking; kind: limits.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `19d23602dac028ab881abd905c694ab7c0f2bb1524733e1e173f8b9369faea94`

Proposed stratum: EASY; minimum whole chunks: 364 approximate tokens; span lower bound: 37.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/ingestion/chunking.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/chunking.py#L141-L188) — chunk `chk_f905eeac312f5041e3b1f93f`, half-open characters [246, 326).

````text
boundaries = [match.end() for match in _SENTENCE_END_RE.finditer(block.content)]
````

- [ctxd/app/ingestion/chunking.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/chunking.py#L141-L188) — chunk `chk_f905eeac312f5041e3b1f93f`, half-open characters [462, 515).

````text
token_end = min(token_start + max_tokens, len(spans))
````

- [ctxd/app/ingestion/chunking.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/chunking.py#L141-L188) — chunk `chk_f905eeac312f5041e3b1f93f`, half-open characters [731, 750).

````text
default=char_limit,
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-031 — Which inputs make a chunk ID change after an edit or reordering?

Partition: development; family: chunking; kind: identity.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `35f727e794eaf203329332b967d767b2b244190c48124086cf9cce8d0ff1f13e`

Proposed stratum: EASY; minimum whole chunks: 364 approximate tokens; span lower bound: 41.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/ingestion/chunking.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/chunking.py#L141-L188) — chunk `chk_f905eeac312f5041e3b1f93f`, half-open characters [1647, 1728).

````text
f"{document.document_id}\0{document.content_hash}\0{ordinal}\0{content}".encode()
````

- [ctxd/app/ingestion/chunking.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/chunking.py#L141-L188) — chunk `chk_f905eeac312f5041e3b1f93f`, half-open characters [1751, 1778).

````text
return f"chk_{digest[:24]}"
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-032 — Can overlap cause a single large block to repeat indefinitely?

Partition: development; family: chunking; kind: negative.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `16aa854be595e11ac26b463d51aa8afa006a9b63d55b16ec053347f30f695297`

Proposed stratum: EASY; minimum whole chunks: 352 approximate tokens; span lower bound: 42.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/ingestion/chunking.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/chunking.py#L191-L246) — chunk `chk_b6663227d98920d289616a59`, half-open characters [1835, 1886).

````text
for retained_index in range(len(group) - 1, 0, -1):
````

- [ctxd/app/ingestion/chunking.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/chunking.py#L191-L246) — chunk `chk_b6663227d98920d289616a59`, half-open characters [2205, 2273).

````text
# Always advance; a single large block must not overlap with itself.
````

- [ctxd/app/ingestion/chunking.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/chunking.py#L191-L246) — chunk `chk_b6663227d98920d289616a59`, half-open characters [2286, 2320).

````text
index = max(index + 1, next_index)
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-033 — Which source and line metadata are copied into every generated chunk?

Partition: development; family: chunking; kind: provenance.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `7948e49f3bbd58b37906fa4e8ac835aae7b0696d94c2289ca372014e547ca05c`

Proposed stratum: EASY; minimum whole chunks: 241 approximate tokens; span lower bound: 35.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/ingestion/chunking.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/chunking.py#L248-L277) — chunk `chk_0e3c6a0cb87e09918edd265f`, half-open characters [510, 546).

````text
"source_path": document.source_path,
````

- [ctxd/app/ingestion/chunking.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/chunking.py#L248-L277) — chunk `chk_0e3c6a0cb87e09918edd265f`, half-open characters [563, 601).

````text
"content_hash": document.content_hash,
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/ingestion/chunking.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/chunking.py#L248-L277) — chunk `chk_0e3c6a0cb87e09918edd265f`, half-open characters [1156, 1187).

````text
start_line=group[0].start_line,
````

- [ctxd/app/ingestion/chunking.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/chunking.py#L248-L277) — chunk `chk_0e3c6a0cb87e09918edd265f`, half-open characters [1208, 1236).

````text
end_line=group[-1].end_line,
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-034 — Explain the complete Markdown-to-chunk path: fences, oversized blocks, target grouping, overlap progress and the final hard-limit check.

Partition: development; family: chunking; kind: joint_requirements.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `332c90b14358c8d64d51b706c29c094e47945bae58da45ecdf25040a47151af8`

Proposed stratum: HARD; minimum whole chunks: 1375 approximate tokens; span lower bound: 57.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/ingestion/chunking.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/chunking.py#L92-L138) — chunk `chk_57a0e89e3f1b34acbbaabaee`, half-open characters [366, 386).

````text
fence = stripped[:3]
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/ingestion/chunking.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/chunking.py#L141-L188) — chunk `chk_f905eeac312f5041e3b1f93f`, half-open characters [1048, 1099).

````text
part = block.content[char_start:actual_end].strip()
````

**REQUIRED required-3** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/ingestion/chunking.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/chunking.py#L191-L246) — chunk `chk_b6663227d98920d289616a59`, half-open characters [1177, 1251).

````text
group_tokens + separator_tokens + block_tokens > self.config.target_tokens
````

**REQUIRED required-4** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/ingestion/chunking.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/chunking.py#L191-L246) — chunk `chk_b6663227d98920d289616a59`, half-open characters [2286, 2320).

````text
index = max(index + 1, next_index)
````

**REQUIRED required-5** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/ingestion/chunking.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/ingestion/chunking.py#L248-L277) — chunk `chk_0e3c6a0cb87e09918edd265f`, half-open characters [332, 412).

````text
raise RuntimeError("chunker produced a chunk above the configured hard maximum")
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-035 — What is the reciprocal-rank formula in HybridRetriever, and does it mix raw component scores?

Partition: development; family: fusion; kind: exact_symbol.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `7ad278ff8b6aa86979b0db4f5a425b3fb59533782b74fc8221a9a7bd33a771d1`

Proposed stratum: EASY; minimum whole chunks: 259 approximate tokens; span lower bound: 32.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/retrieval/hybrid.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/hybrid.py#L1-L39) — chunk `chk_eaac1961a377aa9ac55efddd`, half-open characters [363, 435).

````text
``RRF(d) = sum(1 / (k + rank_i(d)))``. Component scores are deliberately
````

- [ctxd/app/retrieval/hybrid.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/hybrid.py#L1-L39) — chunk `chk_eaac1961a377aa9ac55efddd`, half-open characters [440, 464).

````text
not normalized or mixed.
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-036 — What candidate depth does hybrid search choose when no depth is set, and is it always 20?

Partition: development; family: fusion; kind: configuration.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `0b2806000a0f296a718069ece10c602015e45a48bf3f810aca813374762d92dd`

Proposed stratum: EASY; minimum whole chunks: 173 approximate tokens; span lower bound: 19.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/retrieval/hybrid.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/hybrid.py#L75-L88) — chunk `chk_32075d7eaabb3fcedffe4e95`, half-open characters [170, 233).

````text
width = self.candidate_depth or max(top_k, min(100, top_k * 2))
````

**SUPPORTING supporting-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/retrieval/hybrid.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/hybrid.py#L1-L39) — chunk `chk_eaac1961a377aa9ac55efddd`, half-open characters [600, 635).

````text
candidate_depth: int | None = None,
````

**OPTIONAL optional-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/retrieval/hybrid.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/hybrid.py#L1-L39) — chunk `chk_eaac1961a377aa9ac55efddd`, half-open characters [644, 666).

````text
parallel: bool = True,
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-037 — How does fusion break equal-score ties and preserve candidates returned by only one component?

Partition: development; family: fusion; kind: determinism.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `9d003ebf4be219a5f9d79a2db23e972fa039f695dc62949d19827d1b508fb647`

Proposed stratum: EASY; minimum whole chunks: 275 approximate tokens; span lower bound: 35.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/retrieval/hybrid.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/hybrid.py#L41-L73) — chunk `chk_8f3caf269200f8f033d0e85d`, half-open characters [853, 897).

````text
# lexical-only and semantic-only candidates.
````

- [ctxd/app/retrieval/hybrid.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/hybrid.py#L41-L73) — chunk `chk_8f3caf269200f8f033d0e85d`, half-open characters [906, 978).

````text
ordered = sorted(scores, key=lambda item: (-scores[item], item))[:top_k]
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-038 — Which component ranks and raw scores survive in fused metadata?

Partition: development; family: fusion; kind: provenance.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `f3e130d9ac342fbdf51746901c8aaa207d99a026856d23e09c79b8c22b536e12`

Proposed stratum: MEDIUM; minimum whole chunks: 534 approximate tokens; span lower bound: 43.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/retrieval/hybrid.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/hybrid.py#L1-L39) — chunk `chk_eaac1961a377aa9ac55efddd`, half-open characters [1204, 1285).

````text
score_key = "raw_lexical_score" if component == "lexical" else "raw_vector_score"
````

- [ctxd/app/retrieval/hybrid.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/hybrid.py#L1-L39) — chunk `chk_eaac1961a377aa9ac55efddd`, half-open characters [1294, 1366).

````text
return {f"{component}_rank": rank, score_key: candidate.relevance_score}
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/retrieval/hybrid.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/hybrid.py#L41-L73) — chunk `chk_8f3caf269200f8f033d0e85d`, half-open characters [1268, 1296).

````text
"fused_score": scores[item],
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-039 — How many workers does parallel hybrid search use and how are the two searches joined?

Partition: development; family: fusion; kind: concurrency.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `0249fc10214353c136a2bfd66e4ce3b481f8b0b506ef6a38135cfc94d94cd198`

Proposed stratum: EASY; minimum whole chunks: 173 approximate tokens; span lower bound: 68.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/retrieval/hybrid.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/hybrid.py#L75-L88) — chunk `chk_32075d7eaabb3fcedffe4e95`, half-open characters [272, 357).

````text
with ThreadPoolExecutor(max_workers=2, thread_name_prefix="ctxd-hybrid") as executor:
````

- [ctxd/app/retrieval/hybrid.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/hybrid.py#L75-L88) — chunk `chk_32075d7eaabb3fcedffe4e95`, half-open characters [374, 452).

````text
lexical_future = executor.submit(self.lexical.search, query, tenant_id, width)
````

- [ctxd/app/retrieval/hybrid.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/hybrid.py#L75-L88) — chunk `chk_32075d7eaabb3fcedffe4e95`, half-open characters [469, 549).

````text
semantic_future = executor.submit(self.semantic.search, query, tenant_id, width)
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/retrieval/hybrid.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/hybrid.py#L75-L88) — chunk `chk_32075d7eaabb3fcedffe4e95`, half-open characters [566, 599).

````text
lexical = lexical_future.result()
````

- [ctxd/app/retrieval/hybrid.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/hybrid.py#L75-L88) — chunk `chk_32075d7eaabb3fcedffe4e95`, half-open characters [616, 651).

````text
semantic = semantic_future.result()
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-040 — What BM25 parameter defaults and admissible ranges does BM25Retriever enforce?

Partition: development; family: fusion; kind: configuration.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `fcb94d7be6893758b57132f6edf553faae53b08793137d91c34feb6fa4284284`

Proposed stratum: EASY; minimum whole chunks: 178 approximate tokens; span lower bound: 31.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/retrieval/lexical.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/lexical.py#L1-L34) — chunk `chk_3419d5fe5a59e823c782d646`, half-open characters [650, 666).

````text
k1: float = 1.5,
````

- [ctxd/app/retrieval/lexical.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/lexical.py#L1-L34) — chunk `chk_3419d5fe5a59e823c782d646`, half-open characters [675, 691).

````text
b: float = 0.75,
````

- [ctxd/app/retrieval/lexical.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/lexical.py#L1-L34) — chunk `chk_3419d5fe5a59e823c782d646`, half-open characters [715, 745).

````text
if k1 <= 0 or not 0 <= b <= 1:
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-041 — If lexical search raises, which request status and timing metrics are still recorded?

Partition: development; family: fusion; kind: failure.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `833376cd20845dd328e48c4725f7c2e04321b59564015ba57ddda8f32defc55f`

Proposed stratum: EASY; minimum whole chunks: 319 approximate tokens; span lower bound: 30.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/retrieval/lexical.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/lexical.py#L36-L82) — chunk `chk_9b5413f50ea4683c695a379f`, half-open characters [1638, 1655).

````text
except Exception:
````

- [ctxd/app/retrieval/lexical.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/lexical.py#L36-L82) — chunk `chk_9b5413f50ea4683c695a379f`, half-open characters [1668, 1684).

````text
status = "error"
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/retrieval/lexical.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/lexical.py#L36-L82) — chunk `chk_9b5413f50ea4683c695a379f`, half-open characters [1782, 1827).

````text
RETRIEVAL_REQUESTS_TOTAL.labels(status).inc()
````

- [ctxd/app/retrieval/lexical.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/lexical.py#L36-L82) — chunk `chk_9b5413f50ea4683c695a379f`, half-open characters [1840, 1882).

````text
RETRIEVAL_LATENCY_SECONDS.observe(elapsed)
````

- [ctxd/app/retrieval/lexical.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/lexical.py#L36-L82) — chunk `chk_9b5413f50ea4683c695a379f`, half-open characters [1895, 1942).

````text
LEXICAL_SEARCH_LATENCY_SECONDS.observe(elapsed)
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-042 — Describe lexical candidate provenance, fusion rank preservation, deterministic tie-breaking and final top_k truncation.

Partition: development; family: fusion; kind: joint_requirements.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `670e5ae561a24d775e7af89f22a151056b5483cba1e4bd944e4d84ccff575de2`

Proposed stratum: MEDIUM; minimum whole chunks: 853 approximate tokens; span lower bound: 73.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/retrieval/lexical.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/lexical.py#L36-L82) — chunk `chk_9b5413f50ea4683c695a379f`, half-open characters [987, 1024).

````text
"document_id": hit.chunk.document_id,
````

- [ctxd/app/retrieval/lexical.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/lexical.py#L36-L82) — chunk `chk_9b5413f50ea4683c695a379f`, half-open characters [1113, 1170).

````text
"source_path": hit.chunk.metadata.get("source_path", ""),
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/retrieval/hybrid.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/hybrid.py#L1-L39) — chunk `chk_eaac1961a377aa9ac55efddd`, half-open characters [1294, 1366).

````text
return {f"{component}_rank": rank, score_key: candidate.relevance_score}
````

**REQUIRED required-3** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/retrieval/hybrid.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/hybrid.py#L41-L73) — chunk `chk_8f3caf269200f8f033d0e85d`, half-open characters [906, 978).

````text
ordered = sorted(scores, key=lambda item: (-scores[item], item))[:top_k]
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-043 — Which exact Model2Vec repository, revision, dimension and normalization setting define the real baseline?

Partition: holdout; family: semantic; kind: version.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `70faf6eec7cebc1ed91de28fae812645ee823a2f88ed03945fca74ca061a6a38`

Proposed stratum: EASY; minimum whole chunks: 344 approximate tokens; span lower bound: 35.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/retrieval/semantic.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/semantic.py#L50-L85) — chunk `chk_34dc1a2201eb680e14066a64`, half-open characters [1268, 1305).

````text
model_id = "minishlab/potion-base-8M"
````

- [ctxd/app/retrieval/semantic.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/semantic.py#L50-L85) — chunk `chk_34dc1a2201eb680e14066a64`, half-open characters [1310, 1363).

````text
revision = "bf8b056651a2c21b8d2565580b8569da283cab23"
````

- [ctxd/app/retrieval/semantic.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/semantic.py#L50-L85) — chunk `chk_34dc1a2201eb680e14066a64`, half-open characters [1368, 1383).

````text
dimension = 256
````

- [ctxd/app/retrieval/semantic.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/semantic.py#L50-L85) — chunk `chk_34dc1a2201eb680e14066a64`, half-open characters [1441, 1496).

````text
version = f"model2vec:{model_id}@{revision}:normalized"
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-044 — Is FakeHashEmbeddingProvider a semantic model, and what does its signed hash represent?

Partition: holdout; family: semantic; kind: negative.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `bebe1494b7ec60093752fcce73766670e5dcbac0f2d959ac95847ebf32f93c3f`

Proposed stratum: MEDIUM; minimum whole chunks: 639 approximate tokens; span lower bound: 63.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/retrieval/semantic.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/semantic.py#L1-L48) — chunk `chk_0d557d99b525ff24e17bfd32`, half-open characters [1053, 1133).

````text
"""Deterministic signed feature hash fixture; not a semantic embedding model."""
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/retrieval/semantic.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/semantic.py#L50-L85) — chunk `chk_34dc1a2201eb680e14066a64`, half-open characters [159, 215).

````text
digest = blake2b(token.encode(), digest_size=8).digest()
````

- [ctxd/app/retrieval/semantic.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/semantic.py#L50-L85) — chunk `chk_34dc1a2201eb680e14066a64`, half-open characters [279, 348).

````text
values[number % self.dimension] += 1.0 if (number >> 8) & 1 else -1.0
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-045 — What makes loading the real embedding model cache-only?

Partition: holdout; family: semantic; kind: offline.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `137828fd614587535efe6d3f3369200f30a92690a04fe201aa834ed38c5d9062`

Proposed stratum: EASY; minimum whole chunks: 272 approximate tokens; span lower bound: 18.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/retrieval/semantic.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/semantic.py#L87-L127) — chunk `chk_aaf1f82be594bc84bc0fcdf6`, half-open characters [516, 541).

````text
local_files_only=offline,
````

- [ctxd/app/retrieval/semantic.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/semantic.py#L87-L127) — chunk `chk_aaf1f82be594bc84bc0fcdf6`, half-open characters [560, 623).

````text
self._model = StaticModel.from_pretrained(path, normalize=True)
````

**SUPPORTING supporting-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/retrieval/semantic.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/semantic.py#L50-L85) — chunk `chk_34dc1a2201eb680e14066a64`, half-open characters [1193, 1258).

````text
Set ``offline=True`` after pre-populating the Hugging Face cache.
````

**OPTIONAL optional-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/retrieval/semantic.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/semantic.py#L87-L127) — chunk `chk_aaf1f82be594bc84bc0fcdf6`, half-open characters [455, 503).

````text
cache_dir=str(cache_dir) if cache_dir else None,
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-046 — What happens if the loaded real model's dimension differs from its pinned contract?

Partition: holdout; family: semantic; kind: failure.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `3320f0b0332b56b39599a99a38463947d80da3f15e03304555b7ec26d195cd4c`

Proposed stratum: EASY; minimum whole chunks: 272 approximate tokens; span lower bound: 34.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/retrieval/semantic.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/semantic.py#L87-L127) — chunk `chk_aaf1f82be594bc84bc0fcdf6`, half-open characters [632, 669).

````text
if self._model.dim != self.dimension:
````

- [ctxd/app/retrieval/semantic.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/semantic.py#L87-L127) — chunk `chk_aaf1f82be594bc84bc0fcdf6`, half-open characters [718, 794).

````text
f"model dimension changed: expected {self.dimension}, got {self._model.dim}"
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-047 — How are document batches encoded, and does this provider enable multiprocessing?

Partition: holdout; family: semantic; kind: batching.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `105032d18c87bec029509ff4c05389844b956507bf367b439912fd34e08f0522`

Proposed stratum: EASY; minimum whole chunks: 272 approximate tokens; span lower bound: 14.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/retrieval/semantic.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/semantic.py#L87-L127) — chunk `chk_aaf1f82be594bc84bc0fcdf6`, half-open characters [1036, 1063).

````text
batch_size=self.batch_size,
````

- [ctxd/app/retrieval/semantic.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/semantic.py#L87-L127) — chunk `chk_aaf1f82be594bc84bc0fcdf6`, half-open characters [1076, 1100).

````text
show_progress_bar=False,
````

- [ctxd/app/retrieval/semantic.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/semantic.py#L87-L127) — chunk `chk_aaf1f82be594bc84bc0fcdf6`, half-open characters [1113, 1139).

````text
use_multiprocessing=False,
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-048 — Does semantic_candidate discard a negative raw cosine score or only clamp the public relevance value?

Partition: holdout; family: semantic; kind: provenance.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `286e9d1b98d928c385c1c583b37ba29f4e737c3f57e4d439848a5bca5bc397bf`

Proposed stratum: EASY; minimum whole chunks: 306 approximate tokens; span lower bound: 21.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/retrieval/semantic.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/semantic.py#L126-L163) — chunk `chk_3b02d87a48fdceb725b8b7d1`, half-open characters [337, 373).

````text
relevance_score=max(0.0, hit.score),
````

- [ctxd/app/retrieval/semantic.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/semantic.py#L126-L163) — chunk `chk_3b02d87a48fdceb725b8b7d1`, half-open characters [703, 733).

````text
"raw_vector_score": hit.score,
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-049 — Which tenant and embedding version accompany a query sent to the semantic index?

Partition: holdout; family: semantic; kind: isolation.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `17206a1e177b5d4bae771616395f263c7b2afe09c1146cb8c1a60870270bce74`

Proposed stratum: EASY; minimum whole chunks: 306 approximate tokens; span lower bound: 20.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/retrieval/semantic.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/semantic.py#L126-L163) — chunk `chk_3b02d87a48fdceb725b8b7d1`, half-open characters [1130, 1205).

````text
self.model.embed_query(query), tenant_id, top_k, version=self.model.version
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-050 — Trace real model loading, dimension validation, batched encoding and version-scoped query execution.

Partition: holdout; family: semantic; kind: joint_requirements.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `62c876c386239dcf6dfe22b72b8369a735eb7d38aee43c128e5431ddb1a0ee90`

Proposed stratum: MEDIUM; minimum whole chunks: 578 approximate tokens; span lower bound: 46.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/retrieval/semantic.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/semantic.py#L87-L127) — chunk `chk_aaf1f82be594bc84bc0fcdf6`, half-open characters [419, 442).

````text
revision=self.revision,
````

- [ctxd/app/retrieval/semantic.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/semantic.py#L87-L127) — chunk `chk_aaf1f82be594bc84bc0fcdf6`, half-open characters [516, 541).

````text
local_files_only=offline,
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/retrieval/semantic.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/semantic.py#L87-L127) — chunk `chk_aaf1f82be594bc84bc0fcdf6`, half-open characters [632, 669).

````text
if self._model.dim != self.dimension:
````

**REQUIRED required-3** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/retrieval/semantic.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/semantic.py#L87-L127) — chunk `chk_aaf1f82be594bc84bc0fcdf6`, half-open characters [1113, 1139).

````text
use_multiprocessing=False,
````

**REQUIRED required-4** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/retrieval/semantic.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/retrieval/semantic.py#L126-L163) — chunk `chk_3b02d87a48fdceb725b8b7d1`, half-open characters [1130, 1205).

````text
self.model.embed_query(query), tenant_id, top_k, version=self.model.version
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-051 — Which Alembic revision must PostgreSQL contain before PostgresDocumentStore starts?

Partition: development; family: postgres; kind: startup.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `7ff0ebae21f196da6bb53f229c99a17806ee65c764f6e824a774837613ecabae`

Proposed stratum: MEDIUM; minimum whole chunks: 610 approximate tokens; span lower bound: 20.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L1-L41) — chunk `chk_ac8ed91ad7163c8e0cc20d9a`, half-open characters [963, 997).

````text
_REQUIRED_REVISION = "0002_phase4"
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L40-L98) — chunk `chk_a29cb6b8f1049ab254459c12`, half-open characters [2057, 2116).

````text
if row is None or row["version_num"] != _REQUIRED_REVISION:
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-052 — How are cancellation, connection failures and other database errors mapped to storage exceptions?

Partition: development; family: postgres; kind: failure.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `dfd77bd6c8ae57c996efd5a0f76adf1ec95e73636162ee7a41dfde7aee77b46d`

Proposed stratum: EASY; minimum whole chunks: 378 approximate tokens; span lower bound: 64.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L100-L152) — chunk `chk_2cb7b5a0dee03031b70ac49a`, half-open characters [487, 515).

````text
except QueryCanceled as exc:
````

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L100-L152) — chunk `chk_2cb7b5a0dee03031b70ac49a`, half-open characters [559, 641).

````text
raise RetrievalTimeoutError(f"database operation timed out: {operation}") from exc
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L100-L152) — chunk `chk_2cb7b5a0dee03031b70ac49a`, half-open characters [650, 705).

````text
except (psycopg.OperationalError, TimeoutError) as exc:
````

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L100-L152) — chunk `chk_2cb7b5a0dee03031b70ac49a`, half-open characters [753, 835).

````text
raise StorageUnavailableError(f"database unavailable during {operation}") from exc
````

**REQUIRED required-3** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L100-L152) — chunk `chk_2cb7b5a0dee03031b70ac49a`, half-open characters [914, 984).

````text
raise StorageError(f"database operation failed: {operation}") from exc
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-053 — How does changed-document replacement serialize per-document work and protect shared tenant corpus statistics?

Partition: development; family: postgres; kind: concurrency.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `bc178e28bd48a9d3f5ad1f2a0c8f23d84e66dd14d41012c327b2bfabdde4ec09`

Proposed stratum: EASY; minimum whole chunks: 369 approximate tokens; span lower bound: 28.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L150-L212) — chunk `chk_6f37715a3ace8a428ecd718a`, half-open characters [1063, 1119).

````text
"SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
````

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L150-L212) — chunk `chk_6f37715a3ace8a428ecd718a`, half-open characters [1635, 1712).

````text
"SELECT tenant_id FROM lexical_corpus_stats WHERE tenant_id = %s FOR UPDATE",
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-054 — Which database value allows document replacement to return early when content is unchanged?

Partition: development; family: postgres; kind: idempotence.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `66b0e23426ff0dd614a64c3a638d29bede6afcfeba6cce94fdbe15a445c862ec`

Proposed stratum: EASY; minimum whole chunks: 369 approximate tokens; span lower bound: 14.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L150-L212) — chunk `chk_6f37715a3ace8a428ecd718a`, half-open characters [2234, 2287).

````text
and previous["content_hash"] == document.content_hash
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L150-L212) — chunk `chk_6f37715a3ace8a428ecd718a`, half-open characters [2319, 2331).

````text
return False
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-055 — How does replacing chunks remove stale term frequencies and vocabulary entries?

Partition: development; family: postgres; kind: indexing.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `2146935cbc005a136e9adee5ca36470ee66d6f011b35f551c9a122142d7e46b8`

Proposed stratum: EASY; minimum whole chunks: 357 approximate tokens; span lower bound: 23.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L250-L302) — chunk `chk_165b08277cfd2b3397f22686`, half-open characters [1749, 1797).

````text
SET document_frequency = document_frequency - %s
````

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L250-L302) — chunk `chk_165b08277cfd2b3397f22686`, half-open characters [2051, 2128).

````text
"DELETE FROM lexical_terms WHERE tenant_id = %s AND document_frequency <= 0",
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-056 — How does document replacement update the tenant's document count, chunk count and total lexical length?

Partition: development; family: postgres; kind: indexing.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `587b5d77ae43e2d53e53126c235182d6f745488806414e5994ba4e1c516812ce`

Proposed stratum: EASY; minimum whole chunks: 404 approximate tokens; span lower bound: 35.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L331-L405) — chunk `chk_f2a687500791e05f44aa0b40`, half-open characters [1608, 1651).

````text
indexed_documents = indexed_documents + %s,
````

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L331-L405) — chunk `chk_f2a687500791e05f44aa0b40`, half-open characters [1672, 1703).

````text
chunk_count = chunk_count + %s,
````

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L331-L405) — chunk `chk_f2a687500791e05f44aa0b40`, half-open characters [1724, 1769).

````text
total_chunk_length = total_chunk_length + %s,
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L331-L405) — chunk `chk_f2a687500791e05f44aa0b40`, half-open characters [1941, 1964).

````text
len(chunks) - len(old),
````

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L331-L405) — chunk `chk_f2a687500791e05f44aa0b40`, half-open characters [1985, 2021).

````text
total_new_length - old_total_length,
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-057 — How are malformed persisted chunk metadata and malformed chunk fields reported?

Partition: development; family: postgres; kind: failure.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `792618286b77e865390580fea1edb39bc4065809db5e67e79a7328857abad6b9`

Proposed stratum: EASY; minimum whole chunks: 382 approximate tokens; span lower bound: 25.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L440-L483) — chunk `chk_0e001abd88a5138d4f826ccb`, half-open characters [162, 229).

````text
raise StorageDataError("persisted chunk metadata is not an object")
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L440-L483) — chunk `chk_0e001abd88a5138d4f826ccb`, half-open characters [849, 912).

````text
raise StorageDataError("persisted chunk is malformed") from exc
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-058 — Which filters prevent semantic search from mixing tenants, embedding versions or dimensions?

Partition: development; family: postgres; kind: exact_search.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `01f788de7605f1d2c7608e69f0eeb1b944623a191dd7b69fc0dc9b20981c412d`

Proposed stratum: EASY; minimum whole chunks: 357 approximate tokens; span lower bound: 21.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L610-L642) — chunk `chk_299f91d2ff268bf11808d714`, half-open characters [1277, 1328).

````text
WHERE e.tenant_id = %s AND e.embedding_version = %s
````

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L610-L642) — chunk `chk_299f91d2ff268bf11808d714`, half-open characters [1347, 1367).

````text
AND e.dimension = %s
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-059 — How does exact pgvector search order equal-distance results and convert distance to similarity?

Partition: development; family: postgres; kind: determinism.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `e071690d042f6e070887b292b230dbb30dfda43b5f8a710dd8a40ec36ea45589`

Proposed stratum: EASY; minimum whole chunks: 357 approximate tokens; span lower bound: 38.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L610-L642) — chunk `chk_299f91d2ff268bf11808d714`, half-open characters [943, 1002).

````text
SELECT 1.0 - ({vector_expression} <=> %s::vector) AS score,
````

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L610-L642) — chunk `chk_299f91d2ff268bf11808d714`, half-open characters [1384, 1439).

````text
ORDER BY {vector_expression} <=> %s::vector, c.chunk_id
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-060 — Is HNSW on by default, and what vector expression changes in the experimental branch?

Partition: development; family: postgres; kind: negative.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `b0de25771e44042355f03a19232dac74c18903161bbc3419a698467b0d445469`

Proposed stratum: MEDIUM; minimum whole chunks: 754 approximate tokens; span lower bound: 29.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L40-L98) — chunk `chk_a29cb6b8f1049ab254459c12`, half-open characters [339, 362).

````text
use_hnsw: bool = False,
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L610-L642) — chunk `chk_299f91d2ff268bf11808d714`, half-open characters [814, 897).

````text
vector_expression = "e.embedding::vector(256)" if self._use_hnsw else "e.embedding"
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-061 — How is a query statement timeout scoped to a PostgreSQL retrieval transaction?

Partition: development; family: postgres; kind: timeouts.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `d56beb5fb15f1388c05da584b3f6a2f1ebf8631f276245a64f5029effcc1b773`

Proposed stratum: MEDIUM; minimum whole chunks: 890 approximate tokens; span lower bound: 46.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L610-L642) — chunk `chk_299f91d2ff268bf11808d714`, half-open characters [352, 433).

````text
with self._connection("semantic_search") as connection, connection.transaction():
````

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L547-L608) — chunk `chk_d4e926eaadcf4d176099a707`, half-open characters [2423, 2474).

````text
"SELECT set_config('statement_timeout', %s, true)",
````

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L547-L608) — chunk `chk_d4e926eaadcf4d176099a707`, half-open characters [2491, 2524).

````text
(f"{self._query_timeout_ms}ms",),
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-062 — What order does list_chunks promise across documents and ordinals?

Partition: development; family: postgres; kind: ordering.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `04a8435fcdd3798ff6d9eefd87ab57efadc12d4f40fcdfd0a51d9ef410be288d`

Proposed stratum: EASY; minimum whole chunks: 176 approximate tokens; span lower bound: 7.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L485-L507) — chunk `chk_1a8c9ad5f8b5038d9006965c`, half-open characters [485, 524).

````text
ORDER BY document_id, ordinal, chunk_id
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-063 — Trace a PostgreSQL document replacement from startup revision checks through transaction locks, stale postings removal, new chunk insertion, corpus statistics and embedding writes.

Partition: development; family: postgres; kind: joint_requirements.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `bd8c7adb788362c4674ee863c80cc20a5de882635025359aaf385ca6776d00c2`

Proposed stratum: HARD; minimum whole chunks: 1343 approximate tokens; span lower bound: 51.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L1-L41) — chunk `chk_ac8ed91ad7163c8e0cc20d9a`, half-open characters [963, 997).

````text
_REQUIRED_REVISION = "0002_phase4"
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L150-L212) — chunk `chk_6f37715a3ace8a428ecd718a`, half-open characters [932, 1014).

````text
with self._connection("document_replace") as connection, connection.transaction():
````

**REQUIRED required-3** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L250-L302) — chunk `chk_165b08277cfd2b3397f22686`, half-open characters [1749, 1797).

````text
SET document_frequency = document_frequency - %s
````

**REQUIRED required-4** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L331-L405) — chunk `chk_f2a687500791e05f44aa0b40`, half-open characters [126, 146).

````text
INSERT INTO chunks (
````

**REQUIRED required-5** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L331-L405) — chunk `chk_f2a687500791e05f44aa0b40`, half-open characters [1724, 1769).

````text
total_chunk_length = total_chunk_length + %s,
````

**REQUIRED required-6** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L331-L405) — chunk `chk_f2a687500791e05f44aa0b40`, half-open characters [2470, 2523).

````text
"INSERT INTO chunk_embeddings (tenant_id, chunk_id, "
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-064 — Audit PostgreSQL read isolation across document lookup, chunk lookup, lexical joins, semantic filters and both statistics paths.

Partition: development; family: postgres; kind: joint_requirements.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `a2b8f4964f37f3686468be3bca5879085ce68f2aaba697685bc43348a1a94b63`

Proposed stratum: HARD; minimum whole chunks: 1608 approximate tokens; span lower bound: 81.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L440-L483) — chunk `chk_0e001abd88a5138d4f826ccb`, half-open characters [1254, 1310).

````text
FROM documents WHERE tenant_id = %s AND document_id = %s
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L440-L483) — chunk `chk_0e001abd88a5138d4f826ccb`, half-open characters [1821, 1871).

````text
FROM chunks WHERE tenant_id = %s AND chunk_id = %s
````

**REQUIRED required-3** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L547-L608) — chunk `chk_d4e926eaadcf4d176099a707`, half-open characters [1225, 1264).

````text
ON p.tenant_id = %s AND p.term = q.term
````

**REQUIRED required-4** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L610-L642) — chunk `chk_299f91d2ff268bf11808d714`, half-open characters [1277, 1328).

````text
WHERE e.tenant_id = %s AND e.embedding_version = %s
````

**REQUIRED required-5** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L644-L689) — chunk `chk_15fcf4c9fdb98eb2e80e3dd4`, half-open characters [276, 349).

````text
"max(dimension) AS dimension FROM chunk_embeddings WHERE tenant_id = %s",
````

**REQUIRED required-6** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/postgres.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/postgres.py#L644-L689) — chunk `chk_15fcf4c9fdb98eb2e80e3dd4`, half-open characters [1209, 1263).

````text
LEFT JOIN lexical_terms t ON t.tenant_id = s.tenant_id
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-065 — What stops in-memory replacement from rebuilding an unchanged document?

Partition: development; family: memory; kind: idempotence.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `82a838ba9ff0e9a648a411462b06ed4de2b07e62e79d8c1347fdce184b09bed2`

Proposed stratum: EASY; minimum whole chunks: 280 approximate tokens; span lower bound: 17.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/documents.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/documents.py#L62-L99) — chunk `chk_1f296aca6378a4f5c720087a`, half-open characters [449, 524).

````text
if previous is not None and previous.content_hash == document.content_hash:
````

- [ctxd/app/storage/documents.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/documents.py#L62-L99) — chunk `chk_1f296aca6378a4f5c720087a`, half-open characters [541, 553).

````text
return False
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-066 — How does the memory store prevent a caller from mutating a stored document through a get_document result?

Partition: development; family: memory; kind: isolation.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `c033eb02cbe60a49f37aafad5ec4debf0639f3d9dac7c3be65b4900f8f9b7e5b`

Proposed stratum: EASY; minimum whole chunks: 387 approximate tokens; span lower bound: 13.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/documents.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/documents.py#L101-L147) — chunk `chk_a4eb1c7849129b7c85ccadcb`, half-open characters [1975, 2034).

````text
return document.model_copy(deep=True) if document else None
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-067 — When chunks are replaced in memory, are stale embeddings removed as well as postings?

Partition: development; family: memory; kind: cleanup.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `4665b4bb85a792c065a423772d781dc9d59dc8021a46f353fa071410d84a7f96`

Proposed stratum: EASY; minimum whole chunks: 387 approximate tokens; span lower bound: 22.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/documents.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/documents.py#L101-L147) — chunk `chk_a4eb1c7849129b7c85ccadcb`, half-open characters [1045, 1091).

````text
self._remove_chunk_locked(tenant_id, chunk_id)
````

- [ctxd/app/storage/documents.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/documents.py#L101-L147) — chunk `chk_a4eb1c7849129b7c85ccadcb`, half-open characters [1104, 1153).

````text
self._embeddings.pop((tenant_id, chunk_id), None)
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-068 — How does in-memory semantic retrieval restrict stored vectors to the requested tenant and version?

Partition: development; family: memory; kind: isolation.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `9dd8a2bbc431fd1375bbfc65f8f28faefc74683b441a6c45db62c606a0620609`

Proposed stratum: EASY; minimum whole chunks: 292 approximate tokens; span lower bound: 12.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/documents.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/documents.py#L176-L213) — chunk `chk_05846fa473cce7e95ba0a00c`, half-open characters [313, 364).

````text
if owner != tenant_id or stored_version != version:
````

- [ctxd/app/storage/documents.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/documents.py#L176-L213) — chunk `chk_05846fa473cce7e95ba0a00c`, half-open characters [385, 393).

````text
continue
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-069 — What tie-break does the in-memory index use after scoring candidates?

Partition: development; family: memory; kind: determinism.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `c4aca31210c96a4f5cb50d1575c66bfe9b16c8cf74932baa93b9856f883b1f7f`

Proposed stratum: EASY; minimum whole chunks: 292 approximate tokens; span lower bound: 22.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/documents.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/documents.py#L176-L213) — chunk `chk_05846fa473cce7e95ba0a00c`, half-open characters [542, 591).

````text
scored.sort(key=lambda item: (-item[0], item[1]))
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-070 — How is average chunk length calculated for BM25 normalization in memory?

Partition: development; family: memory; kind: indexing.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `f116db7e05373a059411a72ba379f5602e63802803b98eb4eec996c51ce352ec`

Proposed stratum: EASY; minimum whole chunks: 348 approximate tokens; span lower bound: 35.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/documents.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/documents.py#L215-L261) — chunk `chk_1a41d393fc040f9131a42a86`, half-open characters [437, 505).

````text
average_length = self._total_lexical_length[tenant_id] / corpus_size
````

- [ctxd/app/storage/documents.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/documents.py#L215-L261) — chunk `chk_1a41d393fc040f9131a42a86`, half-open characters [836, 917).

````text
length_normalization = 1 - b + b * sum(terms.values()) / max(average_length, 1.0)
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-071 — Does an empty-token lexical query return an error or an empty result?

Partition: development; family: memory; kind: negative.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `68895e5d46cbae303700ab686e18e3bc1190d153901deb9e87526c711c16d2ad`

Proposed stratum: EASY; minimum whole chunks: 348 approximate tokens; span lower bound: 16.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/documents.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/documents.py#L215-L261) — chunk `chk_1a41d393fc040f9131a42a86`, half-open characters [181, 231).

````text
query_frequency = Counter(tokenize_lexical(query))
````

- [ctxd/app/storage/documents.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/documents.py#L215-L261) — chunk `chk_1a41d393fc040f9131a42a86`, half-open characters [240, 263).

````text
if not query_frequency:
````

- [ctxd/app/storage/documents.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/documents.py#L215-L261) — chunk `chk_1a41d393fc040f9131a42a86`, half-open characters [276, 285).

````text
return []
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-072 — Trace in-memory update safety through input validation, the document lock, stale embedding cleanup, term counters, result copies and deletion.

Partition: development; family: memory; kind: joint_requirements.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `d32434c1608a2380e8525a0be48713df8fce8293811b1feac8e90b602def9072`

Proposed stratum: HARD; minimum whole chunks: 1168 approximate tokens; span lower bound: 67.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/documents.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/documents.py#L41-L60) — chunk `chk_2eef74562a84b7b09374db30`, half-open characters [931, 1010).

````text
raise ValueError("all chunks must belong to the requested document and tenant")
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/documents.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/documents.py#L62-L99) — chunk `chk_1f296aca6378a4f5c720087a`, half-open characters [401, 436).

````text
previous = self._documents.get(key)
````

**REQUIRED required-3** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/documents.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/documents.py#L101-L147) — chunk `chk_a4eb1c7849129b7c85ccadcb`, half-open characters [1104, 1153).

````text
self._embeddings.pop((tenant_id, chunk_id), None)
````

**REQUIRED required-4** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/documents.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/documents.py#L101-L147) — chunk `chk_a4eb1c7849129b7c85ccadcb`, half-open characters [1747, 1790).

````text
self._document_frequency[postings_key] += 1
````

**REQUIRED required-5** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/documents.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/documents.py#L149-L174) — chunk `chk_fc40e20cb8d46083ca5fdb5c`, half-open characters [165, 218).

````text
return chunk.model_copy(deep=True) if chunk else None
````

**REQUIRED required-6** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/storage/documents.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/storage/documents.py#L149-L174) — chunk `chk_fc40e20cb8d46083ca5fdb5c`, half-open characters [1231, 1257).

````text
return removed is not None
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-073 — Which score shape and finiteness checks are enforced before applying reranker scores?

Partition: development; family: reranking; kind: failure.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `2c2820bb7211a36ebc2d9b298438568e923a39bae6ab02934e93eda04005bdae`

Proposed stratum: EASY; minimum whole chunks: 290 approximate tokens; span lower bound: 28.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/reranking/base.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/reranking/base.py#L1-L48) — chunk `chk_74b09cb42961af2e281e13f0`, half-open characters [526, 560).

````text
if len(scores) != len(candidates):
````

- [ctxd/app/reranking/base.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/reranking/base.py#L1-L48) — chunk `chk_74b09cb42961af2e281e13f0`, half-open characters [645, 698).

````text
if any(not math.isfinite(score) for score in scores):
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-074 — How are equal reranker scores ordered, and is their raw sign preserved in metadata?

Partition: development; family: reranking; kind: determinism.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `09178f0bcd5cc41c53395ffd3bd4f8f1759301b09d452b3192dbd306d0411295`

Proposed stratum: EASY; minimum whole chunks: 290 approximate tokens; span lower bound: 40.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/reranking/base.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/reranking/base.py#L1-L48) — chunk `chk_74b09cb42961af2e281e13f0`, half-open characters [844, 884).

````text
key=lambda item: (-item[1][1], item[0]),
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/reranking/base.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/reranking/base.py#L1-L48) — chunk `chk_74b09cb42961af2e281e13f0`, half-open characters [971, 1003).

````text
"rerank_score": max(0.0, score),
````

- [ctxd/app/reranking/base.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/reranking/base.py#L1-L48) — chunk `chk_74b09cb42961af2e281e13f0`, half-open characters [1096, 1120).

````text
"reranker_score": score,
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-075 — What does RerankingRetriever return if reranking throws or changes the candidate set?

Partition: development; family: reranking; kind: failure.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `e34617bae36f15c2e1c6173a02bba256c06b119407055d39ec09c9ea67b48a8a`

Proposed stratum: EASY; minimum whole chunks: 345 approximate tokens; span lower bound: 33.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/reranking/retriever.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/reranking/retriever.py#L1-L43) — chunk `chk_aebd81bc857a71bd591b30ed`, half-open characters [1378, 1439).

````text
if not self._same_candidate_set(candidates, reranked, top_k):
````

- [ctxd/app/reranking/retriever.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/reranking/retriever.py#L1-L43) — chunk `chk_aebd81bc857a71bd591b30ed`, half-open characters [1460, 1514).

````text
raise ValueError("reranker changed the candidate set")
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/reranking/retriever.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/reranking/retriever.py#L1-L43) — chunk `chk_aebd81bc857a71bd591b30ed`, half-open characters [1722, 1739).

````text
except Exception:
````

- [ctxd/app/reranking/retriever.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/reranking/retriever.py#L1-L43) — chunk `chk_aebd81bc857a71bd591b30ed`, half-open characters [1845, 1870).

````text
return candidates[:top_k]
````

**SUPPORTING supporting-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/reranking/retriever.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/reranking/retriever.py#L1-L43) — chunk `chk_aebd81bc857a71bd591b30ed`, half-open characters [350, 431).

````text
"""Reorder a fixed upstream candidate set, falling back to its original order."""
````

**OPTIONAL optional-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/reranking/retriever.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/reranking/retriever.py#L1-L43) — chunk `chk_aebd81bc857a71bd591b30ed`, half-open characters [1756, 1828).

````text
RERANKER_REQUESTS_TOTAL.labels(self.reranker.model_id, "fallback").inc()
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-076 — Which identity constraints does _same_candidate_set actually check?

Partition: development; family: reranking; kind: contract.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `6f912194ae6f616ba2ddd7fd6681d5aa218a545d8c16323ab75ffe6ff3da5277`

Proposed stratum: EASY; minimum whole chunks: 89 approximate tokens; span lower bound: 37.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/reranking/retriever.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/reranking/retriever.py#L45-L55) — chunk `chk_5ac49a9f28afc406197f8b67`, half-open characters [316, 362).

````text
len(reranked_ids) == min(len(original), top_k)
````

- [ctxd/app/reranking/retriever.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/reranking/retriever.py#L45-L55) — chunk `chk_5ac49a9f28afc406197f8b67`, half-open characters [375, 422).

````text
and len(reranked_ids) == len(set(reranked_ids))
````

- [ctxd/app/reranking/retriever.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/reranking/retriever.py#L45-L55) — chunk `chk_5ac49a9f28afc406197f8b67`, half-open characters [435, 472).

````text
and set(reranked_ids) <= original_ids
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-077 — What offline cache check does FlashRankReranker perform before constructing Ranker?

Partition: development; family: reranking; kind: offline.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `aa652da5688442227cf4f1acb2cce07b3ea178ab3b05798623cdceafc6a49525`

Proposed stratum: EASY; minimum whole chunks: 287 approximate tokens; span lower bound: 31.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/reranking/flashrank.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/reranking/flashrank.py#L1-L50) — chunk `chk_47090bc52227dcad4663039a`, half-open characters [1101, 1165).

````text
if offline and not (cache / self.flashrank_model_name).is_dir():
````

- [ctxd/app/reranking/flashrank.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/reranking/flashrank.py#L1-L50) — chunk `chk_47090bc52227dcad4663039a`, half-open characters [1178, 1255).

````text
raise FileNotFoundError("reranker model is not present in the offline cache")
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-078 — Which TinyBERT model ID, source revision and pair-length limit are declared by the internal FlashRank wrapper?

Partition: development; family: reranking; kind: version.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `1543073d7651ea2838d5612671289e74287c17966894037fcce09d791e9042b9`

Proposed stratum: EASY; minimum whole chunks: 287 approximate tokens; span lower bound: 27.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/reranking/flashrank.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/reranking/flashrank.py#L1-L50) — chunk `chk_47090bc52227dcad4663039a`, half-open characters [607, 658).

````text
model_id = "cross-encoder/ms-marco-TinyBERT-L-2-v2"
````

- [ctxd/app/reranking/flashrank.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/reranking/flashrank.py#L1-L50) — chunk `chk_47090bc52227dcad4663039a`, half-open characters [663, 723).

````text
source_revision = "81d1926f67cb8eee2c2be17ca9f793c7c3bd20cc"
````

- [ctxd/app/reranking/flashrank.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/reranking/flashrank.py#L1-L50) — chunk `chk_47090bc52227dcad4663039a`, half-open characters [782, 798).

````text
max_length = 512
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-079 — How does FlashRank convert one-logit and multi-logit outputs into ranking scores?

Partition: development; family: reranking; kind: logits.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `76dfc93165130ad933385315bf51fc843fc4e1b41447cefaeb2a9d666fc04dc9`

Proposed stratum: MEDIUM; minimum whole chunks: 600 approximate tokens; span lower bound: 60.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/reranking/flashrank.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/reranking/flashrank.py#L52-L108) — chunk `chk_e92ef9e0d17370c3e8ea2b8e`, half-open characters [2597, 2621).

````text
if logits.shape[1] == 1:
````

- [ctxd/app/reranking/flashrank.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/reranking/flashrank.py#L52-L108) — chunk `chk_e92ef9e0d17370c3e8ea2b8e`, half-open characters [2642, 2696).

````text
batch_scores = 1.0 / (1.0 + np.exp(-logits.flatten()))
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/reranking/flashrank.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/reranking/flashrank.py#L52-L108) — chunk `chk_e92ef9e0d17370c3e8ea2b8e`, half-open characters [2739, 2795).

````text
shifted = logits - np.max(logits, axis=1, keepdims=True)
````

- [ctxd/app/reranking/flashrank.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/reranking/flashrank.py#L52-L108) — chunk `chk_e92ef9e0d17370c3e8ea2b8e`, half-open characters [2917, 2951).

````text
batch_scores = probabilities[:, 1]
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-080 — Trace the experimental reranking contract from upstream candidate count through input pairing, logit conversion, score validation, rank metadata and fallback behavior.

Partition: development; family: reranking; kind: joint_requirements.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `7e7f9e9445febcfb4dbdc5933ec3846b972af2800e77ca109fd202fb2d1a7d34`

Proposed stratum: HARD; minimum whole chunks: 1235 approximate tokens; span lower bound: 77.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/reranking/retriever.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/reranking/retriever.py#L1-L43) — chunk `chk_aebd81bc857a71bd591b30ed`, half-open characters [928, 1001).

````text
candidates = self.upstream.search(query, tenant_id, self.candidate_count)
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/reranking/flashrank.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/reranking/flashrank.py#L52-L108) — chunk `chk_e92ef9e0d17370c3e8ea2b8e`, half-open characters [1763, 1836).

````text
encoded = tokenizer.encode_batch([[query, row["text"]] for row in batch])
````

**REQUIRED required-3** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/reranking/flashrank.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/reranking/flashrank.py#L52-L108) — chunk `chk_e92ef9e0d17370c3e8ea2b8e`, half-open characters [2917, 2951).

````text
batch_scores = probabilities[:, 1]
````

**REQUIRED required-4** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/reranking/base.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/reranking/base.py#L1-L48) — chunk `chk_74b09cb42961af2e281e13f0`, half-open characters [645, 698).

````text
if any(not math.isfinite(score) for score in scores):
````

**REQUIRED required-5** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/reranking/base.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/reranking/base.py#L1-L48) — chunk `chk_74b09cb42961af2e281e13f0`, half-open characters [1141, 1179).

````text
"pre_rerank_rank": original_index + 1,
````

**REQUIRED required-6** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/reranking/retriever.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/reranking/retriever.py#L1-L43) — chunk `chk_aebd81bc857a71bd591b30ed`, half-open characters [1845, 1870).

````text
return candidates[:top_k]
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-081 — How can tracing be disabled entirely?

Partition: development; family: observability; kind: configuration.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `64a40a7bd655532137dcd0e975b7fdaef82478b9443265badae2db295c36821a`

Proposed stratum: EASY; minimum whole chunks: 175 approximate tokens; span lower bound: 7.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/observability/tracing.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/observability/tracing.py#L1-L28) — chunk `chk_282994b03b742f2091ed5bce`, half-open characters [492, 521).

````text
if not settings.otel_enabled:
````

- [ctxd/app/observability/tracing.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/observability/tracing.py#L1-L28) — chunk `chk_282994b03b742f2091ed5bce`, half-open characters [530, 536).

````text
return
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-082 — Does enabling tracing without an OTLP endpoint configure a network exporter?

Partition: development; family: observability; kind: configuration.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `1c5f8370e9dafb50ede29bca7d402deb97dd19e07316e1ca4f42522756ecd757`

Proposed stratum: EASY; minimum whole chunks: 175 approximate tokens; span lower bound: 24.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/observability/tracing.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/observability/tracing.py#L1-L28) — chunk `chk_282994b03b742f2091ed5bce`, half-open characters [809, 849).

````text
if settings.otel_exporter_otlp_endpoint:
````

- [ctxd/app/observability/tracing.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/observability/tracing.py#L1-L28) — chunk `chk_282994b03b742f2091ed5bce`, half-open characters [858, 932).

````text
exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
````

- [ctxd/app/observability/tracing.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/observability/tracing.py#L1-L28) — chunk `chk_282994b03b742f2091ed5bce`, half-open characters [941, 998).

````text
provider.add_span_processor(BatchSpanProcessor(exporter))
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-083 — Which service identity attributes are attached to the OpenTelemetry resource?

Partition: development; family: observability; kind: provenance.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `8c27cc731e69275dbba5428c91f3c8163aa64da46d2a68b5da168b9f02e462c2`

Proposed stratum: EASY; minimum whole chunks: 175 approximate tokens; span lower bound: 30.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/observability/tracing.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/observability/tracing.py#L1-L28) — chunk `chk_282994b03b742f2091ed5bce`, half-open characters [588, 622).

````text
"service.name": settings.app_name,
````

- [ctxd/app/observability/tracing.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/observability/tracing.py#L1-L28) — chunk `chk_282994b03b742f2091ed5bce`, half-open characters [635, 679).

````text
"service.version": settings.service_version,
````

- [ctxd/app/observability/tracing.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/observability/tracing.py#L1-L28) — chunk `chk_282994b03b742f2091ed5bce`, half-open characters [692, 739).

````text
"deployment.environment": settings.environment,
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-084 — Which request-scoped identifiers and exception data are emitted by JsonFormatter?

Partition: development; family: observability; kind: logging.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `b584eccbf2b6b30aef90aeda5a35489585f4104ccba5f067eca521c641f63a83`

Proposed stratum: EASY; minimum whole chunks: 279 approximate tokens; span lower bound: 50.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/observability/logging.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/observability/logging.py#L1-L34) — chunk `chk_1ed901be89d092c0bf2a4bb6`, half-open characters [674, 709).

````text
"request_id": request_id_var.get(),
````

- [ctxd/app/observability/logging.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/observability/logging.py#L1-L34) — chunk `chk_1ed901be89d092c0bf2a4bb6`, half-open characters [722, 753).

````text
"trace_id": trace_id_var.get(),
````

- [ctxd/app/observability/logging.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/observability/logging.py#L1-L34) — chunk `chk_1ed901be89d092c0bf2a4bb6`, half-open characters [766, 799).

````text
"tenant_id": tenant_id_var.get(),
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/observability/logging.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/observability/logging.py#L1-L34) — chunk `chk_1ed901be89d092c0bf2a4bb6`, half-open characters [818, 837).

````text
if record.exc_info:
````

- [ctxd/app/observability/logging.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/observability/logging.py#L1-L34) — chunk `chk_1ed901be89d092c0bf2a4bb6`, half-open characters [850, 910).

````text
payload["exception"] = self.formatException(record.exc_info)
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-085 — Does configure_logging preserve existing root handlers or replace them?

Partition: development; family: observability; kind: configuration.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `5a670334de47bd4133250ffc859ee28a7102a0a61025bceda533094b5454db4f`

Proposed stratum: EASY; minimum whole chunks: 279 approximate tokens; span lower bound: 23.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/observability/logging.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/observability/logging.py#L1-L34) — chunk `chk_1ed901be89d092c0bf2a4bb6`, half-open characters [1141, 1162).

````text
root.handlers.clear()
````

- [ctxd/app/observability/logging.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/observability/logging.py#L1-L34) — chunk `chk_1ed901be89d092c0bf2a4bb6`, half-open characters [1167, 1191).

````text
root.addHandler(handler)
````

- [ctxd/app/observability/logging.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/observability/logging.py#L1-L34) — chunk `chk_1ed901be89d092c0bf2a4bb6`, half-open characters [1196, 1224).

````text
root.setLevel(level.upper())
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-086 — Does the Synapse JSON-type check accept Python booleans as numbers or integers?

Partition: holdout; family: synapse; kind: types.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `0f9413d9da39b44c4750331402b7461a2663610a25233e8463a5760216102ca2`

Proposed stratum: EASY; minimum whole chunks: 394 approximate tokens; span lower bound: 40.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/integrations/synapse/evaluator.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/integrations/synapse/evaluator.py#L1-L60) — chunk `chk_59f66c8f8d168e8c07fa7b4c`, half-open characters [659, 684).

````text
if json_type == "number":
````

- [ctxd/app/integrations/synapse/evaluator.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/integrations/synapse/evaluator.py#L1-L60) — chunk `chk_59f66c8f8d168e8c07fa7b4c`, half-open characters [693, 762).

````text
return isinstance(value, int | float) and not isinstance(value, bool)
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/integrations/synapse/evaluator.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/integrations/synapse/evaluator.py#L1-L60) — chunk `chk_59f66c8f8d168e8c07fa7b4c`, half-open characters [802, 863).

````text
return isinstance(value, int) and not isinstance(value, bool)
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-087 — How does argument validation reject missing required keys or a malformed required-key declaration?

Partition: holdout; family: synapse; kind: validation.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `e2b348daacec1113e8b89997133ea83023858de2a2ee7b93290cedaa636b0ec0`

Proposed stratum: EASY; minimum whole chunks: 394 approximate tokens; span lower bound: 23.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/integrations/synapse/evaluator.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/integrations/synapse/evaluator.py#L1-L60) — chunk `chk_59f66c8f8d168e8c07fa7b4c`, half-open characters [1343, 1377).

````text
if not isinstance(required, list):
````

- [ctxd/app/integrations/synapse/evaluator.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/integrations/synapse/evaluator.py#L1-L60) — chunk `chk_59f66c8f8d168e8c07fa7b4c`, half-open characters [1432, 1484).

````text
if not isinstance(key, str) or key not in arguments:
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-088 — Can a selected tool be correct without matching expected_tool exactly?

Partition: holdout; family: synapse; kind: alternatives.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `9fc09a31173cefc0f97618b1c0cee12abe9c58a8e4de99adab941c6bc4926bce`

Proposed stratum: EASY; minimum whole chunks: 150 approximate tokens; span lower bound: 25.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/integrations/synapse/evaluator.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/integrations/synapse/evaluator.py#L63-L79) — chunk `chk_22bcf772b923bb80c143ca30`, half-open characters [81, 120).

````text
acceptable = set(case.acceptable_tools)
````

- [ctxd/app/integrations/synapse/evaluator.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/integrations/synapse/evaluator.py#L63-L79) — chunk `chk_22bcf772b923bb80c143ca30`, half-open characters [168, 202).

````text
acceptable.add(case.expected_tool)
````

- [ctxd/app/integrations/synapse/evaluator.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/integrations/synapse/evaluator.py#L63-L79) — chunk `chk_22bcf772b923bb80c143ca30`, half-open characters [207, 271).

````text
return selected_tool is not None and selected_tool in acceptable
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-089 — Must invocation arguments match the expected dictionary exactly, including absence of extra keys?

Partition: holdout; family: synapse; kind: negative.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `f1c14c28bf9b35dddc14f7b95ab6e7bf3a31a5e8b00fd65e44ff999daf787280`

Proposed stratum: EASY; minimum whole chunks: 150 approximate tokens; span lower bound: 23.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/integrations/synapse/evaluator.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/integrations/synapse/evaluator.py#L63-L79) — chunk `chk_22bcf772b923bb80c143ca30`, half-open characters [414, 485).

````text
return all(actual.get(key) == value for key, value in expected.items())
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-090 — How is output matching reported when no expected outcome was specified?

Partition: holdout; family: synapse; kind: output.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `d8b0eaa04ade15ad27aefe73762a0c9c0a2b9c67c61eb9a15be21d917efb208d`

Proposed stratum: EASY; minimum whole chunks: 150 approximate tokens; span lower bound: 11.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/integrations/synapse/evaluator.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/integrations/synapse/evaluator.py#L63-L79) — chunk `chk_22bcf772b923bb80c143ca30`, half-open characters [574, 607).

````text
if case.expected_outcome is None:
````

- [ctxd/app/integrations/synapse/evaluator.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/integrations/synapse/evaluator.py#L63-L79) — chunk `chk_22bcf772b923bb80c143ca30`, half-open characters [616, 636).

````text
return "not_checked"
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-091 — Which conditions jointly define task_success, including the unchecked-output case?

Partition: holdout; family: synapse; kind: joint_requirements.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `61d493b04bb0f5eb6e0297397538c4d296672c6585aef3dda55db8156036b1eb`

Proposed stratum: MEDIUM; minimum whole chunks: 538 approximate tokens; span lower bound: 14.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/integrations/synapse/evaluator.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/integrations/synapse/evaluator.py#L82-L155) — chunk `chk_6376b22bbd80e4ac2d6169b7`, half-open characters [576, 588).

````text
tool_correct
````

- [ctxd/app/integrations/synapse/evaluator.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/integrations/synapse/evaluator.py#L82-L155) — chunk `chk_6376b22bbd80e4ac2d6169b7`, half-open characters [885, 904).

````text
and arguments_valid
````

- [ctxd/app/integrations/synapse/evaluator.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/integrations/synapse/evaluator.py#L82-L155) — chunk `chk_6376b22bbd80e4ac2d6169b7`, half-open characters [917, 949).

````text
and invocation.execution_success
````

- [ctxd/app/integrations/synapse/evaluator.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/integrations/synapse/evaluator.py#L82-L155) — chunk `chk_6376b22bbd80e4ac2d6169b7`, half-open characters [962, 993).

````text
and output_status != "mismatch"
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-092 — Without an explicit error category, what is the priority of tool, schema, argument, execution and output failures?

Partition: holdout; family: synapse; kind: failure.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `473b9eefc7344541f7f528e29da8548b0e8ab02c88e9d3e94f2af9b001d03f64`

Proposed stratum: MEDIUM; minimum whole chunks: 538 approximate tokens; span lower bound: 50.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/integrations/synapse/evaluator.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/integrations/synapse/evaluator.py#L82-L155) — chunk `chk_6376b22bbd80e4ac2d6169b7`, half-open characters [1057, 1098).

````text
if category is None and not tool_correct:
````

- [ctxd/app/integrations/synapse/evaluator.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/integrations/synapse/evaluator.py#L82-L155) — chunk `chk_6376b22bbd80e4ac2d6169b7`, half-open characters [1164, 1207).

````text
elif category is None and not schema_valid:
````

- [ctxd/app/integrations/synapse/evaluator.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/integrations/synapse/evaluator.py#L82-L155) — chunk `chk_6376b22bbd80e4ac2d6169b7`, half-open characters [1279, 1325).

````text
elif category is None and not arguments_valid:
````

- [ctxd/app/integrations/synapse/evaluator.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/integrations/synapse/evaluator.py#L82-L155) — chunk `chk_6376b22bbd80e4ac2d6169b7`, half-open characters [1400, 1459).

````text
elif category is None and not invocation.execution_success:
````

- [ctxd/app/integrations/synapse/evaluator.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/integrations/synapse/evaluator.py#L82-L155) — chunk `chk_6376b22bbd80e4ac2d6169b7`, half-open characters [1530, 1617).

````text
elif category is None and invocation.execution_success and output_status == "mismatch":
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-093 — How are latency percentiles chosen, and what does an empty latency list return?

Partition: holdout; family: synapse; kind: statistics.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `cd318376eb66687983aafd8fa589516aec3fe88cf6a82336e8d1c8ae1bdd5e54`

Proposed stratum: EASY; minimum whole chunks: 394 approximate tokens; span lower bound: 26.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/integrations/synapse/evaluator.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/integrations/synapse/evaluator.py#L1-L60) — chunk `chk_59f66c8f8d168e8c07fa7b4c`, half-open characters [381, 395).

````text
if not values:
````

- [ctxd/app/integrations/synapse/evaluator.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/integrations/synapse/evaluator.py#L1-L60) — chunk `chk_59f66c8f8d168e8c07fa7b4c`, half-open characters [404, 414).

````text
return 0.0
````

- [ctxd/app/integrations/synapse/evaluator.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/integrations/synapse/evaluator.py#L1-L60) — chunk `chk_59f66c8f8d168e8c07fa7b4c`, half-open characters [448, 499).

````text
index = int(round((len(ordered) - 1) * percentile))
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-094 — Which extension must exist for the embedding migration, and which revision does it follow?

Partition: development; family: migration; kind: dependency.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `a616db0774d07049ca7333ea73c234bcb0260a038b44af859236f6d659764519`

Proposed stratum: EASY; minimum whole chunks: 245 approximate tokens; span lower bound: 22.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [migrations/versions/0002_phase4_embeddings.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/migrations/versions/0002_phase4_embeddings.py#L1-L39) — chunk `chk_d4d1ef3a7a67b1d17dc77eda`, half-open characters [166, 207).

````text
down_revision: str | None = "0001_phase3"
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [migrations/versions/0002_phase4_embeddings.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/migrations/versions/0002_phase4_embeddings.py#L1-L39) — chunk `chk_d4d1ef3a7a67b1d17dc77eda`, half-open characters [331, 382).

````text
op.execute("CREATE EXTENSION IF NOT EXISTS vector")
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-095 — Why is the embedding column unconstrained in dimension, and which dimensions are mentioned for the fixture and real baseline?

Partition: development; family: migration; kind: version.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `c1d1c68fe86aa24005dc8caf470879e4e35912ada8ec75d18be313e3139ba3b6`

Proposed stratum: EASY; minimum whole chunks: 245 approximate tokens; span lower bound: 25.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [migrations/versions/0002_phase4_embeddings.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/migrations/versions/0002_phase4_embeddings.py#L1-L39) — chunk `chk_d4d1ef3a7a67b1d17dc77eda`, half-open characters [387, 461).

````text
# An unconstrained vector column permits the 128-dimensional deterministic
````

- [migrations/versions/0002_phase4_embeddings.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/migrations/versions/0002_phase4_embeddings.py#L1-L39) — chunk `chk_d4d1ef3a7a67b1d17dc77eda`, half-open characters [466, 540).

````text
# fixture and 256-dimensional real baseline to coexist by version. Queries
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-096 — What primary key and cascade relationship bind an embedding to its tenant-scoped chunk?

Partition: development; family: migration; kind: isolation.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `79b36650e3654b6853d8b131fec6bb0ae0749320dc3d854309e38a5c5257ab40`

Proposed stratum: EASY; minimum whole chunks: 245 approximate tokens; span lower bound: 18.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [migrations/versions/0002_phase4_embeddings.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/migrations/versions/0002_phase4_embeddings.py#L1-L39) — chunk `chk_d4d1ef3a7a67b1d17dc77eda`, half-open characters [1033, 1067).

````text
PRIMARY KEY (tenant_id, chunk_id),
````

- [migrations/versions/0002_phase4_embeddings.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/migrations/versions/0002_phase4_embeddings.py#L1-L39) — chunk `chk_d4d1ef3a7a67b1d17dc77eda`, half-open characters [1130, 1187).

````text
REFERENCES chunks (tenant_id, chunk_id) ON DELETE CASCADE
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-097 — What index supports tenant and embedding-version lookup in the embedding migration?

Partition: development; family: migration; kind: indexing.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `ed3bb62bfe35abf7008fccacaedd4edfc9aee863b1fdcf43191dc36a51c337b4`

Proposed stratum: EASY; minimum whole chunks: 245 approximate tokens; span lower bound: 11.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [migrations/versions/0002_phase4_embeddings.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/migrations/versions/0002_phase4_embeddings.py#L1-L39) — chunk `chk_d4d1ef3a7a67b1d17dc77eda`, half-open characters [1207, 1255).

````text
CREATE INDEX chunk_embeddings_tenant_version_idx
````

- [migrations/versions/0002_phase4_embeddings.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/migrations/versions/0002_phase4_embeddings.py#L1-L39) — chunk `chk_d4d1ef3a7a67b1d17dc77eda`, half-open characters [1268, 1319).

````text
ON chunk_embeddings (tenant_id, embedding_version);
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-098 — Which uniqueness constraints prevent duplicate document paths and chunk ordinals within a tenant?

Partition: development; family: migration; kind: identity.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `1555302955cc26d5a63bc837fc3ca0b70cd6c082bfee2e050f9ab119702db4dd`

Proposed stratum: EASY; minimum whole chunks: 345 approximate tokens; span lower bound: 15.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [migrations/versions/0001_phase3.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/migrations/versions/0001_phase3.py#L1-L54) — chunk `chk_0156cd746246f601cba883d2`, half-open characters [906, 937).

````text
UNIQUE (tenant_id, source_path)
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [migrations/versions/0001_phase3.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/migrations/versions/0001_phase3.py#L1-L54) — chunk `chk_0156cd746246f601cba883d2`, half-open characters [1694, 1735).

````text
UNIQUE (tenant_id, document_id, ordinal),
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-099 — Which database checks protect chunk content, token counts, lexical length and line ranges?

Partition: development; family: migration; kind: limits.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `52a9f37cf178e1491bb356ae80eb8615bee424d4af71f6996c6f4971dfe6cbc3`

Proposed stratum: EASY; minimum whole chunks: 345 approximate tokens; span lower bound: 49.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [migrations/versions/0001_phase3.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/migrations/versions/0001_phase3.py#L1-L54) — chunk `chk_0156cd746246f601cba883d2`, half-open characters [1155, 1205).

````text
content text NOT NULL CHECK (length(content) > 0),
````

- [migrations/versions/0001_phase3.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/migrations/versions/0001_phase3.py#L1-L54) — chunk `chk_0156cd746246f601cba883d2`, half-open characters [1258, 1311).

````text
token_count integer NOT NULL CHECK (token_count > 0),
````

- [migrations/versions/0001_phase3.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/migrations/versions/0001_phase3.py#L1-L54) — chunk `chk_0156cd746246f601cba883d2`, half-open characters [1324, 1384).

````text
lexical_length integer NOT NULL CHECK (lexical_length >= 0),
````

- [migrations/versions/0001_phase3.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/migrations/versions/0001_phase3.py#L1-L54) — chunk `chk_0156cd746246f601cba883d2`, half-open characters [1461, 1518).

````text
end_line integer NOT NULL CHECK (end_line >= start_line),
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-100 — In which order does the lexical migration remove dependent tables, and does the embedding downgrade drop the extension?

Partition: development; family: migration; kind: rollback.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `c47b1983c1cbd2b2abe06eda551097ab58871f9f8f12d0bd4469501db799ee44`

Proposed stratum: EASY; minimum whole chunks: 485 approximate tokens; span lower bound: 30.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [migrations/versions/0001_phase3.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/migrations/versions/0001_phase3.py#L53-L98) — chunk `chk_ea779af2cb0eb48ce3b18d6c`, half-open characters [1419, 1447).

````text
DROP TABLE lexical_postings;
````

- [migrations/versions/0001_phase3.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/migrations/versions/0001_phase3.py#L53-L98) — chunk `chk_ea779af2cb0eb48ce3b18d6c`, half-open characters [1456, 1481).

````text
DROP TABLE lexical_terms;
````

- [migrations/versions/0001_phase3.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/migrations/versions/0001_phase3.py#L53-L98) — chunk `chk_ea779af2cb0eb48ce3b18d6c`, half-open characters [1490, 1522).

````text
DROP TABLE lexical_corpus_stats;
````

- [migrations/versions/0001_phase3.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/migrations/versions/0001_phase3.py#L53-L98) — chunk `chk_ea779af2cb0eb48ce3b18d6c`, half-open characters [1531, 1549).

````text
DROP TABLE chunks;
````

- [migrations/versions/0001_phase3.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/migrations/versions/0001_phase3.py#L53-L98) — chunk `chk_ea779af2cb0eb48ce3b18d6c`, half-open characters [1558, 1579).

````text
DROP TABLE documents;
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [migrations/versions/0002_phase4_embeddings.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/migrations/versions/0002_phase4_embeddings.py#L1-L39) — chunk `chk_d4d1ef3a7a67b1d17dc77eda`, half-open characters [1368, 1409).

````text
op.execute("DROP TABLE chunk_embeddings")
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-101 — Does ContextAssembler stop at the first oversized candidate or keep looking for later candidates that fit?

Partition: holdout; family: context; kind: selection.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `916149d084414f7da521bc2e89f4b26244dfc28826537a7ddf4cbbfb849d911e`

Proposed stratum: EASY; minimum whole chunks: 295 approximate tokens; span lower bound: 20.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/context/assembler.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/context/assembler.py#L1-L48) — chunk `chk_c4aed2c5cb7e318369f67cf6`, half-open characters [1719, 1782).

````text
if selected_tokens + candidate.token_cost > max_context_tokens:
````

- [ctxd/app/context/assembler.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/context/assembler.py#L1-L48) — chunk `chk_c4aed2c5cb7e318369f67cf6`, half-open characters [1803, 1815).

````text
dropped += 1
````

- [ctxd/app/context/assembler.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/context/assembler.py#L1-L48) — chunk `chk_c4aed2c5cb7e318369f67cf6`, half-open characters [1836, 1844).

````text
continue
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/context/assembler.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/context/assembler.py#L1-L48) — chunk `chk_c4aed2c5cb7e318369f67cf6`, half-open characters [1861, 1887).

````text
selected.append(candidate)
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-102 — Does assembly truncate candidate content to fill the remaining token budget?

Partition: holdout; family: context; kind: negative.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `1901f631c6a7b8a9ffb7656afd54cb2ef7252ac9b5eb973aff465f21238f26f2`

Proposed stratum: EASY; minimum whole chunks: 295 approximate tokens; span lower bound: 12.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/context/assembler.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/context/assembler.py#L1-L48) — chunk `chk_c4aed2c5cb7e318369f67cf6`, half-open characters [1861, 1887).

````text
selected.append(candidate)
````

- [ctxd/app/context/assembler.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/context/assembler.py#L1-L48) — chunk `chk_c4aed2c5cb7e318369f67cf6`, half-open characters [1904, 1943).

````text
selected_tokens += candidate.token_cost
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-103 — What retriever is used for a semantic-mode request when no semantic retriever was supplied?

Partition: holdout; family: context; kind: fallback.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `c6d93f7505e4f1cfb2a72a071635ef4d9a3bca4e9619dcb8f511728b9eec6fc0`

Proposed stratum: EASY; minimum whole chunks: 295 approximate tokens; span lower bound: 22.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/context/assembler.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/context/assembler.py#L1-L48) — chunk `chk_c4aed2c5cb7e318369f67cf6`, half-open characters [1097, 1143).

````text
selected_retriever: Retriever = self.retriever
````

- [ctxd/app/context/assembler.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/context/assembler.py#L1-L48) — chunk `chk_c4aed2c5cb7e318369f67cf6`, half-open characters [1156, 1230).

````text
if retrieval_mode == RetrievalMode.SEMANTIC and self.semantic is not None:
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-104 — How is hybrid retrieval constructed by the assembler?

Partition: holdout; family: context; kind: configuration.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `0419ba381c5e33151e3cfb6e939d764dd51537c17ddf240903a93fedb4b50e23`

Proposed stratum: EASY; minimum whole chunks: 295 approximate tokens; span lower bound: 14.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/context/assembler.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/context/assembler.py#L1-L48) — chunk `chk_c4aed2c5cb7e318369f67cf6`, half-open characters [642, 714).

````text
self.hybrid = HybridRetriever(retriever, semantic) if semantic else None
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-105 — Which packet metadata distinguish retrieved candidates, selected candidates and budget drops?

Partition: holdout; family: context; kind: accounting.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `5e786e21f75b27d0b68300398ccadbe9f8b1ba01780b9fd68c06c580be3a521c`

Proposed stratum: EASY; minimum whole chunks: 116 approximate tokens; span lower bound: 30.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/context/assembler.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/context/assembler.py#L50-L67) — chunk `chk_7975fac058b22c709aceb9fd`, half-open characters [554, 599).

````text
"retrieved_candidate_count": len(candidates),
````

- [ctxd/app/context/assembler.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/context/assembler.py#L50-L67) — chunk `chk_7975fac058b22c709aceb9fd`, half-open characters [620, 662).

````text
"selected_candidate_count": len(selected),
````

- [ctxd/app/context/assembler.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/context/assembler.py#L50-L67) — chunk `chk_7975fac058b22c709aceb9fd`, half-open characters [683, 720).

````text
"candidate_tokens": candidate_tokens,
````

- [ctxd/app/context/assembler.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/context/assembler.py#L50-L67) — chunk `chk_7975fac058b22c709aceb9fd`, half-open characters [797, 830).

````text
"dropped_due_to_budget": dropped,
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-106 — What context token and dropped-candidate metrics are recorded during assembly?

Partition: holdout; family: context; kind: observability.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `f08dd91a990988bef8f5dfba81864581dbc9de79f78310b83089c4e391cc56cd`

Proposed stratum: EASY; minimum whole chunks: 116 approximate tokens; span lower bound: 12.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/context/assembler.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/context/assembler.py#L50-L67) — chunk `chk_7975fac058b22c709aceb9fd`, half-open characters [232, 280).

````text
CONTEXT_TOKENS_SELECTED.observe(selected_tokens)
````

- [ctxd/app/context/assembler.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/context/assembler.py#L50-L67) — chunk `chk_7975fac058b22c709aceb9fd`, half-open characters [293, 338).

````text
CONTEXT_CANDIDATES_DROPPED_TOTAL.inc(dropped)
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-107 — How does nDCG avoid giving repeated source identifiers multiple gains without removing their rank positions?

Partition: development; family: evaluation; kind: correctness.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `814a89f515d30e8aa847ef838a15c2a27a5634b0781582c7297137a1ed615e5e`

Proposed stratum: EASY; minimum whole chunks: 337 approximate tokens; span lower bound: 34.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/evals/retrieval.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/evals/retrieval.py#L46-L71) — chunk `chk_d018ffa83fbc0cd0d8d4def2`, half-open characters [310, 364).

````text
for rank, source in enumerate(retrieved[:k], start=1):
````

- [ctxd/app/evals/retrieval.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/evals/retrieval.py#L46-L71) — chunk `chk_d018ffa83fbc0cd0d8d4def2`, half-open characters [373, 418).

````text
if source in relevant and source not in seen:
````

- [ctxd/app/evals/retrieval.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/evals/retrieval.py#L46-L71) — chunk `chk_d018ffa83fbc0cd0d8d4def2`, half-open characters [472, 488).

````text
seen.add(source)
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-108 — Can an unreviewed evidence case receive an answerability score in evaluate_evidence?

Partition: development; family: evaluation; kind: negative.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `cf51e151b4175a4ccc190dc1e12b3ea1960ea02705cb438320f306b6637517b8`

Proposed stratum: EASY; minimum whole chunks: 441 approximate tokens; span lower bound: 23.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/evals/evidence.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/evals/evidence.py#L152-L197) — chunk `chk_ea6d195e4b668b6a834669bf`, half-open characters [326, 363).

````text
if case.status != "VERIFIED_FIXTURE":
````

- [ctxd/app/evals/evidence.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/evals/evidence.py#L152-L197) — chunk `chk_ea6d195e4b668b6a834669bf`, half-open characters [372, 445).

````text
raise ValueError("unreviewed case cannot receive an answerability score")
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-109 — Are spans within an EvidenceAlternative jointly required or interchangeable?

Partition: development; family: evaluation; kind: alternatives.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `ae57385c840aab6d18c7f939a3a4482f4e3fba039d69096c3bba603c95d11da0`

Proposed stratum: EASY; minimum whole chunks: 338 approximate tokens; span lower bound: 26.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/evals/evidence.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/evals/evidence.py#L1-L57) — chunk `chk_2d847555d2823db2777c1c87`, half-open characters [1139, 1218).

````text
# Every span in ONE alternative must survive; alternatives are interchangeable.
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/evals/evidence.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/evals/evidence.py#L1-L57) — chunk `chk_2d847555d2823db2777c1c87`, half-open characters [1223, 1270).

````text
spans: list[EvidenceSpan] = Field(min_length=1)
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-110 — How are span endpoints beyond a chunk's length rejected even though Python slicing would tolerate them?

Partition: development; family: evaluation; kind: validation.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `34e3cd6b5140d4c4abc79df030a8ef1d7072103202db729a994951dd40fef728`

Proposed stratum: EASY; minimum whole chunks: 397 approximate tokens; span lower bound: 28.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/evals/evidence.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/evals/evidence.py#L71-L110) — chunk `chk_9a97aadf2981adbde300b3c9`, half-open characters [1541, 1570).

````text
span.end > len(chunk.content)
````

- [ctxd/app/evals/evidence.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/evals/evidence.py#L71-L110) — chunk `chk_9a97aadf2981adbde300b3c9`, half-open characters [1599, 1654).

````text
or chunk.content[span.start : span.end] != span.excerpt
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-111 — Which template, query and evidence-source overlaps make validate_split reject a partition?

Partition: development; family: evaluation; kind: leakage.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `833ca352210aceb79a22d3410e129201ebd28ced1213e36bf65bf819f79e99db`

Proposed stratum: EASY; minimum whole chunks: 384 approximate tokens; span lower bound: 67.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/evals/evidence.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/evals/evidence.py#L113-L141) — chunk `chk_8867cf50b28e00cc3747f1e3`, half-open characters [1023, 1065).

````text
groups[case.template_group].add(partition)
````

- [ctxd/app/evals/evidence.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/evals/evidence.py#L113-L141) — chunk `chk_8867cf50b28e00cc3747f1e3`, half-open characters [1074, 1137).

````text
queries[" ".join(case.query.casefold().split())].add(partition)
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/evals/evidence.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/evals/evidence.py#L113-L141) — chunk `chk_8867cf50b28e00cc3747f1e3`, half-open characters [1299, 1350).

````text
sources[case.tenant_id, span.source].add(partition)
````

- [ctxd/app/evals/evidence.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/evals/evidence.py#L113-L141) — chunk `chk_8867cf50b28e00cc3747f1e3`, half-open characters [1449, 1521).

````text
raise ValueError("template, duplicate-query or evidence-source leakage")
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-112 — What is compared to ensure a selected candidate preserves the retrieved chunk's identity, content, token count and source?

Partition: development; family: evaluation; kind: provenance.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `ebb794c188c013a3e8db1ee82379e8fd98e868d7c1d8645c334e5a2307b9f709`

Proposed stratum: EASY; minimum whole chunks: 441 approximate tokens; span lower bound: 60.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/evals/evidence.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/evals/evidence.py#L152-L197) — chunk `chk_ea6d195e4b668b6a834669bf`, half-open characters [569, 625).

````text
if any(original.get(c.identity) != c for c in selected):
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/evals/evidence.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/evals/evidence.py#L152-L197) — chunk `chk_ea6d195e4b668b6a834669bf`, half-open characters [783, 816).

````text
chunk.tenant_id != case.tenant_id
````

- [ctxd/app/evals/evidence.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/evals/evidence.py#L152-L197) — chunk `chk_ea6d195e4b668b6a834669bf`, half-open characters [829, 866).

````text
or candidate.content != chunk.content
````

- [ctxd/app/evals/evidence.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/evals/evidence.py#L152-L197) — chunk `chk_ea6d195e4b668b6a834669bf`, half-open characters [879, 919).

````text
or candidate.tokens != chunk.token_count
````

- [ctxd/app/evals/evidence.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/evals/evidence.py#L152-L197) — chunk `chk_ea6d195e4b668b6a834669bf`, half-open characters [932, 984).

````text
or candidate.source != chunk.metadata["source_path"]
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-113 — Trace evidence validation from regenerated production chunks and tenant/source locators to selection preservation, alternative coverage and union-based token precision.

Partition: development; family: evaluation; kind: joint_requirements.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `87158191920091ef927431e0c34ea371ab8be6b0d92c59091ad2e82be2caf2d7`

Proposed stratum: HARD; minimum whole chunks: 1227 approximate tokens; span lower bound: 75.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/evals/evidence.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/evals/evidence.py#L71-L110) — chunk `chk_9a97aadf2981adbde300b3c9`, half-open characters [375, 458).

````text
regenerated = [c for d in self.documents for c in StructureAwareChunker().chunk(d)]
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/evals/evidence.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/evals/evidence.py#L71-L110) — chunk `chk_9a97aadf2981adbde300b3c9`, half-open characters [1363, 1411).

````text
if chunk.metadata["source_path"] != span.source:
````

**REQUIRED required-3** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/evals/evidence.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/evals/evidence.py#L152-L197) — chunk `chk_ea6d195e4b668b6a834669bf`, half-open characters [634, 682).

````text
raise ValueError("selection changed candidates")
````

**REQUIRED required-4** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/evals/evidence.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/evals/evidence.py#L152-L197) — chunk `chk_ea6d195e4b668b6a834669bf`, half-open characters [1912, 1969).

````text
retrieved_covered[group.group_id] |= ids <= retrieved_ids
````

**REQUIRED required-5** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [ctxd/app/evals/evidence.py](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/ctxd/app/evals/evidence.py#L219-L250) — chunk `chk_37db8208e3d6d84ae86a6a47`, half-open characters [794, 857).

````text
"span_token_precision": len(labeled) / total if total else 0.0,
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-114 — Which README commands install Python 3.13 dependencies, validate the project and start the local API?

Partition: development; family: operations; kind: setup.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `7b8d08b27bffdc4773a2b18cabe08b32f3463566be84046cd34433e15bf0371e`

Proposed stratum: EASY; minimum whole chunks: 358 approximate tokens; span lower bound: 43.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [README.md](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/README.md#L107-L165) — chunk `chk_febac2b6f03f16ee2d320704`, half-open characters [1499, 1520).

````text
uv sync --python 3.13
````

- [README.md](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/README.md#L107-L165) — chunk `chk_febac2b6f03f16ee2d320704`, half-open characters [1521, 1534).

````text
uv run pytest
````

- [README.md](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/README.md#L107-L165) — chunk `chk_febac2b6f03f16ee2d320704`, half-open characters [1535, 1554).

````text
uv run ruff check .
````

- [README.md](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/README.md#L107-L165) — chunk `chk_febac2b6f03f16ee2d320704`, half-open characters [1555, 1566).

````text
uv run mypy
````

- [README.md](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/README.md#L107-L165) — chunk `chk_febac2b6f03f16ee2d320704`, half-open characters [1567, 1626).

````text
uv run uvicorn ctxd.app.main:app --host 0.0.0.0 --port 8000
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-115 — What must be started and migrated before selecting the PostgreSQL backend according to the quickstart?

Partition: development; family: operations; kind: setup.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `4090a456bd0a7e127c168f6b8f6c3ea489215ff3eb1ee1f7f2809bd5155dbe40`

Proposed stratum: EASY; minimum whole chunks: 379 approximate tokens; span lower bound: 14.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [README.md](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/README.md#L161-L224) — chunk `chk_9f6ed5aa6994ded2b7947aad`, half-open characters [194, 223).

````text
docker compose up -d postgres
````

- [README.md](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/README.md#L161-L224) — chunk `chk_9f6ed5aa6994ded2b7947aad`, half-open characters [290, 317).

````text
uv run alembic upgrade head
````

- [README.md](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/README.md#L161-L224) — chunk `chk_9f6ed5aa6994ded2b7947aad`, half-open characters [319, 348).

````text
CTXD_STORAGE_BACKEND=postgres
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-116 — Does the README claim inference, model routing, tools or a frontend are implemented?

Partition: development; family: operations; kind: negative.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `f20686386530d2d45949fc658e7f56013e9299b396489be708ffe36e5086c0d8`

Proposed stratum: EASY; minimum whole chunks: 358 approximate tokens; span lower bound: 21.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [README.md](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/README.md#L107-L165) — chunk `chk_febac2b6f03f16ee2d320704`, half-open characters [1259, 1349).

````text
**Not implemented:** inference, model routing, production reranking, tools, or a frontend.
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-117 — Why must the PostgreSQL benchmark commands be run against a dedicated database?

Partition: development; family: operations; kind: safety.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `325fcd5fe0565d413ee7de42f7c051a5b5d6477cc150d998f88b0200a73bb810`

Proposed stratum: EASY; minimum whole chunks: 357 approximate tokens; span lower bound: 14.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [README.md](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/README.md#L161-L224) — chunk `chk_9f6ed5aa6994ded2b7947aad`, half-open characters [1393, 1480).

````text
> These benchmark commands destructively reset corpus tables. Use a dedicated database.
````


Alternative 2: ALL listed spans are jointly required.

- [README.md](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/README.md#L219-L244) — chunk `chk_01dee613567777ca5ceec346`, half-open characters [0, 87).

````text
> These benchmark commands destructively reset corpus tables. Use a dedicated database.
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-118 — According to the Phase 7 and Phase 8 summaries, did improved holdout nDCG establish production-ready reranking?

Partition: development; family: operations; kind: version.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `f4edf964f0f5948794929b0beb0e54c1ebc0b13ad1821ce56d784c5e4766580c`

Proposed stratum: EASY; minimum whole chunks: 357 approximate tokens; span lower bound: 40.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [README.md](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/README.md#L219-L244) — chunk `chk_01dee613567777ca5ceec346`, half-open characters [988, 1098).

````text
Holdout nDCG@5 improved, but MRR/Recall@1 uncertainty crosses zero and CPU latency/throughput costs are large.
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [README.md](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/README.md#L219-L244) — chunk `chk_01dee613567777ca5ceec346`, half-open characters [1489, 1585).

````text
A development-selected selective reranker failed its reused-holdout uncertainty/regression gate;
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-119 — Why did the Phase 9 summary decline to promote exact-text deduplication despite preserved holdout evidence?

Partition: development; family: operations; kind: provenance.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `1ba5f3bd3ad01680b69fd07dbe0503e5893852fb0a8c83c97f08494d6a3d0808`

Proposed stratum: EASY; minimum whole chunks: 386 approximate tokens; span lower bound: 22.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [README.md](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/README.md#L244-L279) — chunk `chk_74be7ee2e441ab5315df6f37`, half-open characters [313, 451).

````text
Frozen exact-text deduplication preserved holdout evidence but did not save tokens; a separate provenance challenge exposed evidence loss.
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-120 — What tenant-header agreement do both POST endpoints require according to the quickstart?

Partition: development; family: operations; kind: contract.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `af43a10f83fbfe37fb4abe3b074433ff210521235f0f2852392de7b51dbb5da7`

Proposed stratum: EASY; minimum whole chunks: 358 approximate tokens; span lower bound: 24.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [README.md](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/README.md#L107-L165) — chunk `chk_febac2b6f03f16ee2d320704`, half-open characters [1667, 1755).

````text
Both POST endpoints require `x-tenant-id`; it must match the request body's `tenant_id`.
````


Alternative 2: ALL listed spans are jointly required.

- [README.md](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/README.md#L161-L224) — chunk `chk_9f6ed5aa6994ded2b7947aad`, half-open characters [0, 88).

````text
Both POST endpoints require `x-tenant-id`; it must match the request body's `tenant_id`.
````

Reviewer findings: pending. Do not score this proposed annotation as approved.

### phase10-121 — Summarize the documented deployment safety checklist: supported ingestion, tenant headers, PostgreSQL migrations, timeout configuration, destructive benchmark isolation and the no-inference boundary.

Partition: development; family: operations; kind: joint_requirements.

Author: phase10-assistant / DRAFT; review: UNREVIEWED; reviewer: none.

Case SHA-256: `f5e7de6cd275d064291fa397c5b6c2855e611301eb9b7615207301fcac059449`

Proposed stratum: HARD; minimum whole chunks: 1117 approximate tokens; span lower bound: 84.

Agent-authored proposed code/documentation evidence. Exact text verified; Semantic sufficiency, minimality, alternatives and clarity await human review. Behavior is at the pinned revision, not a claim about other versions. All spans within an alternative are jointly required; groups are ANDed. Supporting/optional labels are proposals, not human-verified judgments.

**REQUIRED required-1** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [README.md](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/README.md#L33-L113) — chunk `chk_22c97eda72f29dd8c72952fa`, half-open characters [1113, 1141).

````text
- `.txt` and `.md` ingestion
````

**REQUIRED required-2** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [README.md](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/README.md#L107-L165) — chunk `chk_febac2b6f03f16ee2d320704`, half-open characters [1667, 1755).

````text
Both POST endpoints require `x-tenant-id`; it must match the request body's `tenant_id`.
````


Alternative 2: ALL listed spans are jointly required.

- [README.md](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/README.md#L161-L224) — chunk `chk_9f6ed5aa6994ded2b7947aad`, half-open characters [0, 88).

````text
Both POST endpoints require `x-tenant-id`; it must match the request body's `tenant_id`.
````

**REQUIRED required-3** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [README.md](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/README.md#L161-L224) — chunk `chk_9f6ed5aa6994ded2b7947aad`, half-open characters [290, 317).

````text
uv run alembic upgrade head
````

**REQUIRED required-4** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [README.md](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/README.md#L161-L224) — chunk `chk_9f6ed5aa6994ded2b7947aad`, half-open characters [813, 858).

````text
| `CTXD_DATABASE_QUERY_TIMEOUT_MS` | `5000` |
````

**REQUIRED required-5** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [README.md](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/README.md#L161-L224) — chunk `chk_9f6ed5aa6994ded2b7947aad`, half-open characters [1393, 1480).

````text
> These benchmark commands destructively reset corpus tables. Use a dedicated database.
````


Alternative 2: ALL listed spans are jointly required.

- [README.md](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/README.md#L219-L244) — chunk `chk_01dee613567777ca5ceec346`, half-open characters [0, 87).

````text
> These benchmark commands destructively reset corpus tables. Use a dedicated database.
````

**REQUIRED required-6** (OR alternatives below)

Alternative 1: ALL listed spans are jointly required.

- [README.md](https://github.com/tatavishnurao/ctxd/blob/60ccda005fe0283dfd2f1443a5155baeccfe40b7/README.md#L107-L165) — chunk `chk_febac2b6f03f16ee2d320704`, half-open characters [1259, 1349).

````text
**Not implemented:** inference, model routing, production reranking, tools, or a frontend.
````

Reviewer findings: pending. Do not score this proposed annotation as approved.
