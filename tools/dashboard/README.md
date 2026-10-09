# Context packet inspector (local dashboard)

A single-file, zero-build dashboard that turns a `POST /v1/query` into a live
flowchart: it shows the metrics each stage emits, the formula it computes
(BM25 / cosine / RRF, typeset with KaTeX), the full ranked candidate list, and
the greedy budget cut — with the budget slider moving the cut line in real time.

It renders immediately from a baked-in sample run, so it works with no backend
(e.g. previewed as a static page). Pointed at a running ctxd it fetches live data.

## Run it against a local stack

1. **Bring up the API.** With Docker, CORS for `http://localhost:8080` and
   `http://127.0.0.1:8080` is already enabled in `docker-compose.yml`:

   ```bash
   docker compose up --build
   ```

   Without Docker (bare uvicorn), enable CORS yourself for the origin you will
   serve the dashboard from. A shell `export` reaches uvicorn but never a
   container, which is why compose declares it explicitly:

   ```bash
   export CTXD_CORS_ALLOW_ORIGINS='["http://localhost:8080"]'
   uv run uvicorn ctxd.app.main:app
   ```

   (`["*"]` is accepted only when `CTXD_ENVIRONMENT=development`.)

2. **Serve the dashboard** from that origin and open it:

   ```bash
   cd tools/dashboard
   python3 -m http.server 8080
   # open http://localhost:8080/
   ```

3. Set *API base* to your server (default `http://localhost:8000`), type a
   query, pick a mode, and hit **Run**. Drag the budget slider to watch chunks
   move between KEPT and DROPPED.

Open the file directly (`file://`) and the browser blocks the cross-origin
fetch — always serve it over HTTP from the allowed origin.

## Notes

- CORS is off unless `CTXD_CORS_ALLOW_ORIGINS` is set, so this changes nothing
  in a default or production deployment.
- KaTeX loads from a CDN; with no network the formulae fall back to plain text.
