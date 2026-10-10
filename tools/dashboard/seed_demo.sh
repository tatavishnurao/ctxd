#!/usr/bin/env bash
# Seed tenant "demo" with the committed sample documents in demo-docs/, then run
# one query per retrieval mode and print what the ContextPacket reports.
#
# Idempotent: re-ingesting an unchanged document replaces it with identical state,
# so running this twice leaves the same documents and chunks.
#
# Usage: ./seed_demo.sh            (API at http://localhost:8000)
#        CTXD_URL=http://host:port ./seed_demo.sh
set -euo pipefail

API="${CTXD_URL:-http://localhost:8000}"
TENANT="demo"
BUDGET=600
QUERY="what should I do when the database connection pool is exhausted?"
DOCS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/demo-docs"

if ! curl -sf "$API/ready" >/dev/null; then
  echo "ctxd is not ready at $API (start it with 'docker compose up --build' and wait for /ready)" >&2
  exit 1
fi

for file in "$DOCS_DIR"/*.md; do
  name="$(basename "$file")"
  python3 -c '
import json, sys
print(json.dumps({"tenant_id": sys.argv[1], "source_path": sys.argv[2],
                  "source_type": "markdown", "content": open(sys.argv[3], encoding="utf-8").read()}))
' "$TENANT" "$name" "$file" |
    curl -sf "$API/v1/documents" \
      -H 'content-type: application/json' -H "x-tenant-id: $TENANT" -d @- |
    python3 -c '
import json, sys
d = json.load(sys.stdin)
path, chunks, created = d["document"]["source_path"], len(d["chunks"]), d["created"]
print(f"ingested {path}: {chunks} chunks, created={created}")
'
done

echo "query: \"$QUERY\" (budget $BUDGET tokens)"
for mode in lexical semantic hybrid; do
  python3 -c '
import json, sys
print(json.dumps({"tenant_id": sys.argv[1], "query": sys.argv[2],
                  "retrieval_mode": sys.argv[3], "max_context_tokens": int(sys.argv[4])}))
' "$TENANT" "$QUERY" "$mode" "$BUDGET" |
    curl -sf "$API/v1/query" \
      -H 'content-type: application/json' -H "x-tenant-id: $TENANT" -d @- |
    python3 -c '
import json, sys
mode = sys.argv[1]
c = json.load(sys.stdin)["context"]
m = c["metadata"]
kind, budget = m["retrieval_type"], c["token_budget"]
got, kept = m["retrieved_candidate_count"], m["selected_candidate_count"]
dropped, used = m["dropped_due_to_budget"], m["selected_tokens"]
print(f"  {mode:<8} retrieval_type={kind:<8} retrieved={got} selected={kept} "
      f"dropped={dropped} selected_tokens={used}/{budget}")
' "$mode"
done
