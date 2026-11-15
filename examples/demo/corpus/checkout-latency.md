# Checkout latency runbook

## Symptoms

Checkout p99 latency rises above 800 ms while p50 stays near 120 ms. The spike usually follows a deploy or a cache flush.

## First checks

Check the payment-gateway dashboard for elevated p99 latency on the authorize call. Check the cart cache hit rate; a hit rate below 90% means checkout is reading carts from Postgres.

## Known causes

A cold cart cache after a flush sends every checkout to Postgres, and connection pool exhaustion follows within two minutes. Payment-gateway retries with no jitter amplify the spike.
