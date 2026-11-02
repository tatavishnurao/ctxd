#!/usr/bin/env python3
"""Incident-agent demo: ctxd as the context gate in front of an on-call agent.

Runs against a live ctxd using only the public HTTP API. Every claim is asserted,
and any failure exits non-zero, so a passing run is the evidence.

    python3 tools/demo/incident_agent_demo.py [--after-restart]

Stdlib only. Token counts are ctxd's approximate counter, not a model tokenizer.
"""

import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

API = os.environ.get("CTXD_URL", "http://localhost:8000").rstrip("/")
ACME = "demo-key-acme-0123456789abcdef0123"
GLOBEX = "demo-key-globex-0123456789abcdef012"
OPERATOR = "demo-operator-0123456789abcdef01234"
ROOT = Path(__file__).resolve().parents[2]
QUERY = "what should I do when the database connection pool is exhausted?"
CANARY = "GLOBEX-CANARY-7741"
SNAPSHOT = Path(tempfile.gettempdir()) / "ctxd-demo-ranking.json"
failures = 0


def call(method, path, key=None, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(API + path, data=data, method=method)
    request.add_header("content-type", "application/json")
    if key:
        request.add_header("authorization", f"Bearer {key}")
    for name, value in (headers or {}).items():
        request.add_header(name, value)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode()
            status = response.status
    except urllib.error.HTTPError as error:
        raw = error.read().decode()
        status = error.code
    try:
        return status, json.loads(raw)
    except json.JSONDecodeError:
        return status, raw


def check(ok, label):
    global failures
    failures += not ok
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}")


def section(title):
    print(f"\n=== {title}")


def tokens(text):
    return len(re.findall(r"\w+|[^\w\s]", text))


def ask(key, tenant, query=QUERY, budget=1000, mode=None, headers=None):
    body = {"tenant_id": tenant, "query": query, "max_context_tokens": budget}
    if mode:
        body["retrieval_mode"] = mode
    return call("POST", "/v1/query", key, body, headers)


def ingest(key, tenant, path):
    return call(
        "POST",
        "/v1/documents",
        key,
        {
            "tenant_id": tenant,
            "source_path": path.name,
            "source_type": "markdown",
            "content": path.read_text(encoding="utf-8"),
        },
    )


def ranking(packet):
    return [(c["source_id"], c["relevance_score"]) for c in packet["candidates"]]


def show(packet, limit=3):
    for rank, candidate in enumerate(packet["candidates"][:limit], 1):
        meta = candidate["metadata"]
        print(
            f"    {rank}. {meta.get('source_path')} "
            f"score={candidate['relevance_score']:.3f} tokens={candidate['token_cost']}"
        )


def main():
    after_restart = "--after-restart" in sys.argv
    status, ready = call("GET", "/ready")
    if status != 200:
        sys.exit(f"ctxd is not ready at {API}: {ready}")
    print(f"ctxd ready at {API}: {ready['checks']}")

    if after_restart:
        section("Durability: the same query after an API restart")
        status, response = ask(ACME, "acme")
        packet = response["context"]
        expected = json.loads(SNAPSHOT.read_text())
        check(status == 200, "packet served without re-ingesting anything")
        check([list(r) for r in ranking(packet)] == expected, "ranking and scores are identical")
        return

    section("1. Ingest: two customers, one shared agent platform")
    corpus = sorted((ROOT / "tools/dashboard/demo-docs").glob("*.md"))
    corpus_tokens = sum(tokens(path.read_text(encoding="utf-8")) for path in corpus)
    for path in corpus:
        status, _ = ingest(ACME, "acme", path)
        check(status in (200, 201), f"acme ingested {path.name}")
    status, _ = ingest(GLOBEX, "globex", Path(__file__).with_name("globex-checkout-runbook.md"))
    check(status in (200, 201), "globex ingested its private runbook")
    _, stats = call("GET", "/v1/index/statistics", ACME)
    print(f"    acme index: {stats['indexed_documents']} docs, {stats['indexed_chunks']} chunks")

    section(f'2. Agent asks: "{QUERY}"')
    status, response = ask(ACME, "acme")
    packet = response["context"]
    meta = packet["metadata"]
    show(packet)
    top = packet["candidates"][0]
    check(status == 200, "packet returned")
    check(
        "Database connection pool exhausted" in top["content"], "top chunk holds the right section"
    )
    check(
        top["metadata"].get("source_path") == "checkout-incident-runbook.md",
        "provenance names the source file",
    )
    check(
        packet["context_tokens"] <= 1000,
        f"{packet['context_tokens']} tokens within the 1000 budget",
    )
    print(
        f"    stuffing the corpus: {corpus_tokens} tokens | packet: {packet['context_tokens']} "
        f"| dropped for budget: {meta['dropped_due_to_budget']}"
    )
    check(meta["retrieval_type"] == "lexical", "packet says lexical, and lexical is what ran")
    SNAPSHOT.write_text(json.dumps(ranking(packet)))

    section("3. Budget pressure: whole chunks only, never a cut sentence")
    size = top["token_cost"]
    _, tight = ask(ACME, "acme", budget=size - 1)
    tight = tight["context"]
    print(f"    top chunk costs {size}; budget set to {size - 1}")
    show(tight)
    check(
        top["source_id"] not in [c["source_id"] for c in tight["candidates"]],
        "top chunk dropped whole",
    )
    check(tight["metadata"]["dropped_due_to_budget"] >= 1, "the drop is reported in the packet")
    check(tight["context_tokens"] <= size - 1, "budget still respected")
    warnings = tight["metadata"].get("warnings", [])
    check("top_candidate_dropped" in warnings, f"the loss is flagged loudly: {warnings}")

    section("4. Tenant isolation, with real credentials")
    _, stolen = ask(ACME, "acme", query=f"{CANARY} database connection pool", budget=8000)
    check(CANARY not in json.dumps(stolen), "acme cannot retrieve globex's canary")
    _, own = ask(GLOBEX, "globex", query=CANARY)
    check(CANARY in json.dumps(own), "globex can retrieve its own canary (control)")
    status, _ = ask(ACME, "globex")
    check(status == 403, f"acme key naming tenant globex in the body: {status}")
    status, _ = ask(ACME, "acme", headers={"x-tenant-id": "globex"})
    check(status == 403, f"acme key forging x-tenant-id: globex: {status}")
    status, _ = ask(None, "acme")
    check(status == 401, f"no credential: {status}")
    status, _ = ask("not-a-real-key-not-a-real-key-000000", "acme")
    check(status == 401, f"unknown key: {status}")
    status, _ = call("GET", "/metrics", ACME)
    check(status == 401, f"tenant key on the operator endpoint: {status}")
    status, _ = call("GET", "/metrics", OPERATOR)
    check(status == 200, f"operator token on /metrics: {status}")

    section("5. Truth in labelling: an empty answer says it is empty")
    _, none = ask(ACME, "acme", query="zzzzqqq")
    none = none["context"]
    label = none["metadata"]["retrieval_type"]
    print(f"    candidates={len(none['candidates'])} retrieval_type={label}")
    check(
        none["candidates"] == [] and none["metadata"]["retrieval_type"] == "none",
        "nothing found is reported as none",
    )
    _, hybrid = ask(ACME, "acme", mode="hybrid")
    meta = hybrid["context"]["metadata"]
    print(
        f"    requested={meta['requested_mode']} ran={meta['retrieval_type']} "
        f"branches={meta['branch_candidate_counts']} embedding={meta.get('embedding_version')}"
    )
    check(
        meta["requested_mode"] == "hybrid",
        "the requested mode is recorded separately from what ran",
    )

    section("6. What the agent receives")
    start = top["content"].index("## Database connection pool exhausted")
    section_text = top["content"][start:].split("\n## ")[0]
    print(f"[{top['metadata'].get('source_path')}, {packet['packet_id']}]\n{section_text}")
    print(
        f"\n    Known gap: that section is {tokens(section_text)} tokens of a "
        f"{packet['context_tokens']}-token packet. ctxd selects chunks, not evidence spans."
    )


if __name__ == "__main__":
    main()
    print(f"\n{'ALL CHECKS PASSED' if not failures else f'{failures} CHECK(S) FAILED'}")
    sys.exit(1 if failures else 0)
