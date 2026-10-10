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

   Bare uvicorn uses the in-memory store and a fake hash embedder, so semantic
   and hybrid scores there are not meaningful; judge their quality on the Docker
   stack, which runs the real Model2Vec model.

   Either command keeps the terminal busy; run the rest in a second one. The
   first boot downloads the Model2Vec model, so wait until
   `curl localhost:8000/ready` returns `{"status":"ready",...}`.

2. **Load the demo documents** into tenant `demo` (the dashboard's default
   *Tenant*). From the repository root:

   ```bash
   tools/dashboard/seed_demo.sh
   ```

   It ingests the two committed sample files in `tools/dashboard/demo-docs/`
   (`checkout-incident-runbook.md`, `engineering-handbook.md`), then runs one
   query per mode and prints `retrieval_type`, candidate counts and
   `selected_tokens` against the budget. It is safe to re-run: unchanged
   documents are replaced with identical state. Set `CTXD_URL` if the API is not
   on `http://localhost:8000`.

   A tenant with no documents returns an empty ranking (`retrieved 0`), not an
   error. Data loaded by the main README quick start lives under tenant `acme`;
   set *Tenant* to `acme` to query it instead.

3. **Serve the dashboard** from that origin and open it:

   ```bash
   cd tools/dashboard
   python3 -m http.server 8080
   # open http://localhost:8080/
   ```

4. Set *API base* to your server (default `http://localhost:8000`), type a
   query, pick a mode, and hit **Run**. Drag the budget slider to watch chunks
   move between KEPT and DROPPED. With the demo documents, try
   `what should I do when the database connection pool is exhausted?`. The
   *source* column shows each chunk's `source_path`, which for the demo data is
   the file name of one of the committed files in `demo-docs/`.
   With that query the top-ranked chunk is larger than the default 300-token
   budget, so it shows as DROPPED until you drag the slider above its size:
   whole chunks are never truncated, and the panel says so.

Open the file directly (`file://`) and the browser blocks the cross-origin
fetch — always serve it over HTTP from the allowed origin.

## Before a showcase

Start the stack once ahead of time so the image is built and the Model2Vec
model is cached, and stop it with `docker compose down` (not `down -v`, which
deletes the model cache and database volumes). Measured on a WSL2 laptop on
2026-10-10, `docker compose up --build` to `/ready` returning 200:

| Start | Time | What it includes |
|---|---|---|
| Cold (empty volumes, base images already pulled) | ~97 s | image build ~73 s, Postgres + migrations ~8 s, app start with model download ~15 s |
| Warm restart (volumes kept) | ~14 s | cached build, cached model |

A build with no Docker layer cache took ~62 s for the app image alone; pulling
the base images for the first time is extra and was not measured.

## Notes

- CORS is off unless `CTXD_CORS_ALLOW_ORIGINS` is set. `docker-compose.yml`
  sets it to the two localhost dashboard origins for local development; override
  or remove it for any deployment.
- KaTeX loads from a CDN; with no network the formulae fall back to plain text.
