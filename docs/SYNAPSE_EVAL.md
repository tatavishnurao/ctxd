# Experimental Synapse/MCP Evaluation

This is an experimental evaluator for MCP servers, intended for future testing of Synapse-generated MCP servers. It is not official Synapse tooling and does not modify Synapse.

## Purpose

The adapter scores deterministic tool behavior from a generated MCP server boundary:

`codebase -> generated MCP server -> ctxd evaluator -> metrics + failure analysis`

## What is measured

- tool selection accuracy
- JSON-schema argument validity
- expected argument match rate
- execution success rate
- task success rate
- retry rate
- p50/p95/p99 latency
- failure counts for wrong tool, malformed arguments, schema violation, execution error, timeout, missing tool, ambiguous tool, incorrect output, and unexpected retry

## What is not measured yet

- LLM judging
- answer helpfulness
- multi-step agent loops
- model routing
- reranking
- private Synapse backend behavior

## Current fixture

`ctxd/app/integrations/synapse/fixture.py` provides a synthetic fake/generated MCP fixture with 50 deterministic cases. Results are synthetic and should not be reported as real Synapse performance.

## Future generated MCP server integration

The evaluator boundary accepts:

- MCP tool schemas (`McpToolSchema`)
- invocation results (`McpInvocationResult`)
- timing and metadata

A future adapter only needs to translate a real generated MCP server's schema and invocation logs into those types.

## Relationship to ctxd retrieval evaluation

Retrieval evaluation measures whether ctxd finds the right context. The MCP evaluator measures whether a generated tool surface chooses and executes the right tool with valid arguments. They are complementary and intentionally isolated.
