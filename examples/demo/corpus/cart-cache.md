# Cart cache

The cart cache is a Redis cluster in front of Postgres. Entries expire after 30 minutes and are evicted under memory pressure.

## Flushes

A full flush is only safe outside peak hours. After a flush, warm the cache with the `cart-warm` job before re-enabling traffic; skipping the warm-up is the most common cause of checkout p99 spikes.
