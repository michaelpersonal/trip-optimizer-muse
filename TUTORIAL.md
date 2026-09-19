# Tutorial: Turn Your Website into a Muse Connector

This is the full playbook we used to turn Trip Optimizer — a trip-planning engine — into a working Muse custom connector. Follow it to expose your own website or API to Muse.

## What a Muse connector is

A connector lets Muse call your service on the user's behalf. Two flavors:

- **Custom connector** (this tutorial): private to the user. You register your API's host, how it authenticates, and where the key goes. The user enters their key once through a secure form; Muse stores it in the Secure Vault and the agent never sees it again.
- **Directory publishing** (muse.ai/platform): public listing. Requires a hosted multi-tenant service with your own terms of service and privacy policy, plus Meta review. A CLI tool on someone's laptop can't be a connector — it has to be a reachable HTTPS API.

## Step 0 — Design: split reasoning from state

The single most important decision. Muse is the reasoning layer; your service should be a **deterministic state machine**:

- The agent does all judgment: generating proposals, scoring, synthesis, Q&A.
- Your service owns state and enforces invariants: versioning, idempotency, conflict detection, rendering.

This means your service needs **no LLM keys and no inference billing**. It just stores facts and refuses invalid transitions. For Trip Optimizer the invariants are:

1. Proposals are never auto-applied — apply only happens on explicit user approval.
2. Applying a stale proposal returns `PROPOSAL_CONFLICT` (the plan moved past the proposal's base version).
3. `plan.md` stays synchronized with `plan.json` after every applied change.
4. The run log is append-only; it's the crash-recovery source of truth.

Write these down first. They become your test plan later.

## Step 1 — Define the API contract

Write an OpenAPI spec before code. Ours (`openapi.yaml` in the service repo) defines:

- `POST /v1/trips` — initialize (accepts inline constraints, rubrics, activities in one call)
- `GET /v1/trips` — list + default trip
- `GET /v1/trips/{id}/plan` / `PUT` — read / replace the plan (replace bumps `v_NNN`)
- `GET|PUT /v1/trips/{id}/constraints`, `/rubrics`, `/activities`
- `POST /v1/trips/{id}/proposals`, `GET` list, `GET /v1/proposals/{pid}`
- `POST /v1/proposals/{pid}/apply` (idempotent; `PROPOSAL_CONFLICT` on stale base), `/reject`
- `POST|GET /v1/trips/{id}/run-log` — append-only log
- `GET|PUT /v1/profile`
- `DELETE /v1/trips/{id}`

Keep the surface small and deterministic. Every endpoint should do exactly one state transition.

## Step 2 — Build the service

We used Node + Fastify + TypeScript. Per trip, the service keeps a git repo on disk (`plan.json`, `plan.md`, `constraints.yaml`, `rubrics.yaml`, `activities_db.json`, `proposals/`, run log) — the same data model the original CLI used, so behavior matches.

Authentication: a single shared Bearer key is enough for personal use ("dumb key" — no OAuth server to build). Store it in a file on the server (ours: `/home/opc/.trip-optimizer-apikey`), never in code or chat. Rotate it if it ever appears anywhere it shouldn't.

## Step 3 — Deploy with real HTTPS

Connectors require a public HTTPS endpoint. Our setup:

1. **VM**: Oracle Cloud, Oracle Linux. The app runs as a systemd service behind Caddy as a reverse proxy.
2. **TLS**: Caddy with Let's Encrypt — automatic certificates, automatic renewal.
3. **Hostname**: a real domain builds trust and survives IP changes. We used DuckDNS (`tripoptimizer.duckdns.org` → the VM's public IP), pointed Caddy at it, and Let’s Encrypt issued the cert on first request.

Gotchas we hit (so you don't have to):

- **SELinux** on Oracle Linux blocked Node from executing out of the home directory — we copied the Node binary to `/usr/local/bin`.
- **OCI's VCN security list** needed manual ingress rules for ports 80/443; this can't be done from inside the VM.
- If your VM is only reachable over a private tailnet from your agent environment, use the **public IP** for deployment-time access instead.
- If your build machine sits behind an authenticated egress proxy, plain `socat`/TCP tricks may fail — a small Python `CONNECT` ProxyCommand works, and `curl` handles preemptive `Proxy-Authorization` from `$https_proxy` where libraries like `urllib` don't.

Verify before moving on: `GET /health` (or your equivalent) should return 200 over public HTTPS, and a request **without** the key should return 401. That one check proves routing, TLS, and auth enforcement all at once.

## Step 4 — Register it as a Muse connector

This is the core step. In conversation with Muse, you describe your API and Muse mints a **secure setup link** (a hosted page on `agent.meta.ai`). Four things have to come out of your API docs:

| Field | Trip Optimizer example | Why it matters |
|---|---|---|
| Provider slug | `trip-optimizer` | The connector registers as `custom.trip-optimizer`. Lowercase, no spaces. |
| API hosts | `tripoptimizer.duckdns.org` | Bare hostnames only. Egress to anything not listed here is refused, so list every host you'll call. |
| Auth scheme | `api_key` | `api_key` and OAuth 2.0 authorization-code are supported. Password logins, session cookies, request signing, and multi-secret schemes are declined — pick one of the two supported ones. |
| Key placement | `bearer_header` | The one place your API reads the key: `bearer_header`, `custom_header:<Name>`, `query_param:<name>`, or `url_path_segment:<path with {}>`. **This can't be edited afterwards** — a wrong value means registering again and re-entering the key. |

What happens next, from the user's side:

1. Muse sends a setup link (it looks like `agent.meta.ai/connect/api-key?service=...`).
2. The user opens it and enters the API key into the secure form. The key goes **straight to the Secure Vault** — not through chat, not visible to the agent.
3. Done. The connector shows up as connected. The first real API call is what actually verifies the key works.

Notes:

- Re-registering (`reconnect`) **replaces** the stored credential destructively — only do it for an expired, revoked, or rotated key.
- The stored credential is not a readable secret. At request time the agent exchanges it for a short-lived **surrogate** through `authd`; a request that skips that exchange goes out unauthenticated.

## Step 5 — Write the skill that calls it

A connector alone is just auth. The **skill** teaches the agent what to do with it. Ours lives in this repo: `SKILL.md` (workflows + operating rules) plus a thin client, `bin/trip.py`.

The client pattern (from the `skill_creator` skill — use it, don't hand-roll auth):

```python
import sys
sys.path.insert(0, "/opt/hatch/skills/skill-creator/bin")
from dynamic_credentials import dynamic_credential_entry, ensure_allowed_url

BASE = "https://tripoptimizer.duckdns.org"
CRED = "custom.trip-optimizer"
HOSTS = ["tripoptimizer.duckdns.org"]

def _request(method, path, body=None):
    url = BASE + path
    ensure_allowed_url(url, HOSTS)          # host must be in the registered list
    entry = dynamic_credential_entry(CRED)  # surrogate exchange with authd
    surrogate = str(entry["surrogate"]).strip()
    assert entry.get("placement") == "bearer_header"

    cmd = ["curl", "-sS", "--max-time", "60", "-X", method, url]
    # ... add JSON body if present ...
    # Pass the auth header via a 0600-perms curl config file —
    # the surrogate NEVER appears on the command line.
    cfg = tempfile.NamedTemporaryFile("w", suffix=".curlcfg", delete=False)
    os.chmod(cfg.name, 0o600)
    cfg.write(f'header = "Authorization: Bearer {surrogate}"\n')
    cfg.close()
    cmd += ["-K", cfg.name]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    # ... clean up temp files, parse JSON ...
```

Rules this encodes:

- `ensure_allowed_url` fails closed if the host isn't registered.
- The surrogate travels in a restricted-permissions file, never in argv (which leaks to process lists and logs).
- Use `curl`, not `urllib` — on proxied networks only curl handles the egress proxy's preemptive `Proxy-Authorization` correctly.

`SKILL.md` then maps user intents to API calls (init → `POST /v1/trips`, propose → agent generates the candidate + `POST .../proposals`, apply → `POST .../apply` only after the user approves). The skill's frontmatter `description` is the trigger surface — write it as "what this does and when to use it."

## Step 6 — Verify end-to-end through the connector

Test through the **connector path** (`bin/trip.py`), not just direct HTTPS — they exercise different auth plumbing. Our checklist:

1. `GET /health` → 200 (connector auth works at all).
2. `GET /v1/trips` → empty list, `default_trip: null` (clean slate).
3. `POST /v1/trips` with inline constraints → returns `trip_id` + `v_001`.
4. Read the plan back; confirm the version.
5. Create a proposal, apply it → version bumps; apply again → idempotent success.
6. Create a proposal against the old version, apply → `PROPOSAL_CONFLICT`.
7. Append to the run log; confirm it's append-only.
8. Delete the trip; confirm it's gone.

This exact sequence caught a real bug in our service: creating a trip *with* inline constraints returned `TRIP_NOT_FOUND`, because the registry entry was written after the per-trip docs and the doc-writer required the registry entry to exist. Direct-HTTPS testing had never combined init with inline docs, so the bug hid until the connector-path test. **Always test the combined calls your skill will actually make.**

## Checklist before you call it done

- [ ] Public HTTPS endpoint; unauthenticated requests get 401.
- [ ] Connector registered with the right hosts, scheme, and placement (placement can't be edited later).
- [ ] User completed the secure setup form; first real call verified the key.
- [ ] Skill written: `SKILL.md` with trigger description + workflows, thin client using the surrogate pattern.
- [ ] Full lifecycle verified through the connector path, including the conflict/idempotency cases.
- [ ] No secrets in any repo, chat log, or command line. Rotate any key that leaked.
- [ ] Server left clean — delete your test trips.
