# Postgres connection pool

Checkout and cart services share one pgbouncer pool of 200 connections.

## Exhaustion

When the pool is exhausted, requests queue in pgbouncer and checkout p99 latency climbs while p50 looks normal. Raise the pool only after confirming the cart cache is warm; a cold cache will exhaust any pool size.
