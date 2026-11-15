#!/usr/bin/env bash
# ctxd demo: one on-call question, two token budgets, two tenants.
#
# Needs a running ctxd on $CTXD_URL (default http://localhost:8000), curl and jq.
# Works with `docker compose up` or with bare `uv run uvicorn ctxd.app.main:app`:
# the demo uses lexical (BM25) retrieval, the default, which does not use embeddings.
# Use a fresh server: documents are replaced by source_path, so re-runs are safe.
set -euo pipefail

URL="${CTXD_URL:-http://localhost:8000}"
DIR="$(cd "$(dirname "$0")" && pwd)"
PAUSE="${PAUSE:-2}"
QUESTION="why did checkout p99 spike?"

bold=$'\e[1m'; dim=$'\e[2m'; green=$'\e[32m'; red=$'\e[31m'; reset=$'\e[0m'

step() { printf '\n%s▸ %s%s\n' "$bold" "$1" "$reset"; }

ingest() { # tenant file
  jq -n --arg t "$1" --arg p "$(basename "$2")" --rawfile c "$2" \
    '{tenant_id:$t, source_path:$p, source_type:"markdown", content:$c}' |
    curl -sf "$URL/v1/documents" -H 'content-type: application/json' -H "x-tenant-id: $1" -d @- >/dev/null
}

query() { # tenant budget
  jq -n --arg t "$1" --arg q "$QUESTION" --argjson b "$2" \
    '{tenant_id:$t, query:$q, max_context_tokens:$b}' |
    curl -sf "$URL/v1/query" -H 'content-type: application/json' -H "x-tenant-id: $1" -d @- |
    jq -r --arg green "$green" --arg red "$red" --arg dim "$dim" --arg reset "$reset" '
      .context as $p
      | ($p.candidates[] | "  \($green)✓\($reset) \(.metadata.source_path):\(.metadata.start_line)-\(.metadata.end_line)  \(.token_cost) tok  \($dim)bm25 \(.relevance_score * 100 | round / 100)\($reset)"),
        "  tokens \($p.context_tokens) / \($p.token_budget) budget · \($p.metadata.selected_candidate_count) of \($p.metadata.retrieved_candidate_count) chunks kept"
        + (if $p.metadata.dropped_due_to_budget > 0 then " · \($red)\($p.metadata.dropped_due_to_budget) dropped whole, none truncated\($reset)" else "" end)
        + " · \($p.metadata.retrieval_type)"'
}

step "ingest 5 runbooks for tenant acme, 1 note for tenant billing"
for f in "$DIR"/corpus/*.md; do ingest acme "$f"; printf '  %s\n' "$(basename "$f")"; done
ingest billing "$DIR/other-tenant.md"; printf '  %s(billing) other-tenant.md%s\n' "$dim" "$reset"
sleep "$PAUSE"

step "acme asks \"$QUESTION\" with a 2000-token budget"
query acme 2000
sleep "$PAUSE"

step "same question, 110-token budget"
query acme 110
sleep "$PAUSE"

step "same question as tenant billing"
query billing 2000
