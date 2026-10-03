# BEIR evaluation: lexical vs semantic vs hybrid on real text

The first ctxd retrieval-quality measurement on public, human-judged data. It replaces nothing in the historical archive; those numbers remain synthetic-corpus results.

- **Script:** `benchmarks/beir_eval.py`, run at commit `324901e`.
- **Raw output:** `benchmarks/results/beir_eval.json`, with per-query metrics and archive SHA-256s.
- **Reproduce:** `uv run python benchmarks/beir_eval.py --datasets scifact nfcorpus`. The run takes about 2 minutes on CPU and is deterministic: two runs gave identical numbers.

## Protocol

- **Code path:** the production chunker, `BM25Retriever` (k1=1.5, b=0.75, `\w+` casefold tokens, no stemming or stopwords), `SemanticRetriever` with pinned `minishlab/potion-base-8M@bf8b0566`, and `HybridRetriever` (RRF k=60, default depth). All searches are exact. PostgreSQL would return the same rankings; storage is not under test.
- **Tuning:** none. Every parameter is the shipped default, and nothing was fitted to these datasets.
- **Unit of evaluation:** the BEIR document. A document's rank is the rank of its best chunk. Each branch retrieves 100 chunks.
- **Metrics:** BEIR conventions on the human `test` qrels. nDCG@10 uses linear graded gain; Recall@100 and MRR@10 are also reported.
- **Uncertainty:** a paired bootstrap with 2,000 resamples and a fixed seed, run at two levels:
  - *Cluster:* connected components of queries that share a relevant document. On SciFact these are informative (247 clusters, at most 4 queries each).
  - *Query:* used for NFCorpus, where 318 of 323 queries fall in one component, leaving only 6 clusters. The cluster interval there is uninformative and is flagged in the JSON. The query-level interval understates dependence and should be read as optimistic.

## Results (95% intervals)

**SciFact:** 5,183 documents (5,821 chunks), 300 queries. Cluster-level intervals.

| mode | nDCG@10 | Recall@100 | MRR@10 |
|---|---|---|---|
| lexical (BM25) | **0.662** [0.610, 0.713] | 0.879 [0.836, 0.918] | **0.632** [0.577, 0.686] |
| semantic (Model2Vec) | 0.518 [0.465, 0.573] | 0.866 [0.818, 0.908] | 0.479 [0.422, 0.537] |
| hybrid (RRF) | 0.603 [0.551, 0.655] | **0.948** [0.921, 0.971] | 0.559 [0.504, 0.614] |
| hybrid − lexical | **−0.059** [−0.094, −0.026] | **+0.069** [+0.036, +0.108] | −0.073 [−0.111, −0.035] |
| hybrid − semantic | +0.085 [+0.051, +0.119] | +0.082 [+0.045, +0.123] | +0.080 [+0.044, +0.116] |

**NFCorpus:** 3,633 documents (4,197 chunks), 323 queries. Query-level intervals.

| mode | nDCG@10 | Recall@100 | MRR@10 |
|---|---|---|---|
| lexical (BM25) | 0.309 [0.275, 0.345] | 0.234 [0.206, 0.266] | 0.521 [0.472, 0.570] |
| semantic (Model2Vec) | 0.250 [0.220, 0.280] | 0.232 [0.204, 0.260] | 0.444 [0.399, 0.490] |
| hybrid (RRF) | 0.308 [0.276, 0.343] | **0.267** [0.237, 0.298] | 0.514 [0.466, 0.564] |
| hybrid − lexical | −0.001 [−0.015, +0.012] | **+0.033** [+0.019, +0.048] | −0.007 [−0.031, +0.019] |
| hybrid − semantic | +0.059 [+0.044, +0.074] | +0.035 [+0.021, +0.050] | +0.070 [+0.041, +0.103] |

Sanity anchor: published BEIR BM25 nDCG@10 is 0.665 for SciFact and 0.325 for NFCorpus (Thakur et al., 2021). ctxd's unstemmed BM25 reproduces both within about 0.02.

## What this establishes

1. **Hybrid improves recall.** Recall@100 rises on both datasets, and the intervals exclude zero. RRF is a sound way to generate candidates.
2. **Hybrid does not improve the top of the ranking, and on SciFact it hurts it.** nDCG@10 drops by 0.059 versus BM25, with an interval excluding zero. On NFCorpus it is a tie. With this 8M static embedding model, equal-weight RRF lets a weaker semantic branch displace strong BM25 hits from the top 10.
3. **Model2Vec potion-base-8M alone is clearly weaker than BM25** on both datasets.

**Consequence for ctxd.** A ContextPacket is the top of the ranking cut to a token budget, so top-10 quality is what reaches the model. The Phase C default (hybrid whenever Model2Vec is configured) was **not supported by this evidence for small packets on SciFact-like text**; it is supported only when the budget is large enough that recall dominates.

**Decision (v0.1):** the server default retrieval mode is lexical, whatever embedding provider is configured. BM25 is the null retrieval policy, and hybrid showed one clear top-rank harm (SciFact) and no demonstrated top-rank benefit (NFCorpus is flat, and only directionally measured). Reverting is declining to promote hybrid without evidence, not tuning: no parameter was changed, and hybrid remains a supported, tested mode for recall-oriented callers (`retrieval_mode=hybrid`, or `CTXD_DEFAULT_RETRIEVAL_MODE=hybrid`). Future changes must not be selected on these test sets: using BEIR `test` for selection would contaminate the only real-text measurement the project has.

## Ties at the cutoff

The rank-10 boundary is decided by chunk-ID tie-breaking in 10 of 300 hybrid queries on SciFact and 11 of 323 on NFCorpus. Lexical has 1 and 4, semantic 0 and 3. RRF scores are sums of `1/(60+rank)`, so symmetric rank pairs tie exactly. Ranking is still deterministic, but a few percent of top-10 cutoffs are decided by identifier order rather than relevance. For exact search this is the relevant analogue of "distance-aware" recall. ANN recall-versus-exact was out of scope and was not re-measured.

## Limits

- **Scope of the finding:** Model2Vec (static embedding) on two BM25-friendly corpora; finding is provisional, not a claim that dense retrieval is useless. A contextual embedding model, or corpora with more vocabulary mismatch, could change the result.
- Two small datasets, both scientific or medical. This is not a general claim about all text.
- Document-level qrels judge ranking. They do not judge evidence-span sufficiency or provenance, so the evidence-aware selection thesis is still unmeasured.
- **NFCorpus is directional only.** Its largest query cluster holds 318 of 323 queries (6 clusters in all), so the cluster bootstrap is uninformative and the reported query-level intervals understate dependence. Only SciFact has an informative cluster structure.
- Mean per-query times (in the JSON) come from a pure-Python in-memory scan on a shared WSL2 host. They are diagnostics, not performance claims.
