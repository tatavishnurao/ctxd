# Postmortem: checkout p99 spike, September 2026

## Summary

Checkout p99 reached 2.4 s for 18 minutes after an unplanned cart cache flush during a Redis upgrade.

## Root cause

The upgrade flushed the cart cache. The `cart-warm` job did not run, every checkout read from Postgres, and the pgbouncer pool was exhausted.

## Action items

Make `cart-warm` a required step of the Redis upgrade checklist. Add an alert on cart cache hit rate below 90%.
