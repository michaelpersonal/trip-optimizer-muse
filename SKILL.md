---
name: "trip_optimizer"
description: "Plan and optimize trips with the autoresearch pattern: init trips, research cities, run optimization loops, score plans, answer questions, and shepherd plan changes through propose/review/apply. Use when the user asks about trip planning, itineraries, or optimizing a travel plan."
---

# Trip Optimizer

## Purpose
Own the full trip-optimizer lifecycle through the hosted Trip Optimizer service: create trips, research destinations, iteratively optimize itineraries (research → mutate → score → keep/discard), answer questions about plans, and shepherd plan changes through a propose → review → apply workflow. Use when the user asks about trip planning, itineraries, or optimizing a travel plan.

## Key idea
**The agent IS the LLM provider.** All judgment — proposal generation, Q&A, scoring, research synthesis, rubric generation, debrief summarization — is done natively by the agent. The hosted service (`https://tripoptimizer.duckdns.org`) holds only deterministic state: the trip registry, per-trip git repos (`plan.json`, `plan.md`, `constraints.yaml`, `rubrics.yaml`, `activities_db.json`, `proposals/`, append-only run log). It never auto-applies proposals, and applying a stale proposal returns `PROPOSAL_CONFLICT`.

## Tooling
`bin/trip.py` — thin CLI over the hosted API, authenticated with the stored `custom.trip-optimizer` connector (API key in Bearer header, exchanged via authd surrogate; never printed, logged, or persisted).
- `trip.py GET /health` — service health.
- `trip.py GET /v1/trips` — list trips + default.
- `trip.py POST /v1/trips --body-file new.json` — init a trip.
- `trip.py GET /v1/trips/<id>/plan` — read the current plan.
- `trip.py PUT /v1/trips/<id>/plan --body-json '...'` — replace the plan (bumps version).
- `trip.py GET|PUT /v1/trips/<id>/constraints` (same for `/rubrics`, `/activities`).
- `trip.py POST /v1/trips/<id>/proposals --body-json '...'` — create a proposal.
- `trip.py GET /v1/trips/<id>/proposals` — list proposals; `trip.py GET /v1/proposals/<pid>` — one proposal.
- `trip.py POST /v1/proposals/<pid>/apply` — apply (idempotent; `PROPOSAL_CONFLICT` on stale base).
- `trip.py POST /v1/proposals/<pid>/reject` — reject.
- `trip.py POST|GET /v1/trips/<id>/run-log` — append / read the optimization log.
- `trip.py GET|PUT /v1/profile` — traveler profile.
- `trip.py DELETE /v1/trips/<id>` — delete a trip.
Requests use curl (not urllib) because this VM's egress proxy needs preemptive Proxy-Authorization from `$https_proxy`; the surrogate travels in a 0600-perms curl config file, never argv.

## State layout

All state lives on the service; the API is the only interface. Per trip the service keeps a git repo mirroring the local data model: `plan.json` (`version_id` is `v_NNN`, bumped on every applied change), `plan.md` (re-rendered after every apply), `constraints.yaml`, `rubrics.yaml`, `activities_db.json`, `proposals/<proposal_id>.json`, and an append-only run log.

## Workflows

### Show / ask — read-only
1. Resolve trip: explicit id → `default_trip` from `GET /v1/trips` → else `NO_TRIP_CONTEXT` error (tell the user to pick a trip).
2. `GET /v1/trips/<id>/plan` (filter `days` by `day_index` if asked). Answer directly from the data.

### Propose a change
1. Read the plan (`GET .../plan`), constraints, and activities.
2. Classify intent: `direct_override` (simple swap), `scoped_reoptimize` (re-optimize a portion), `structural_change` (multi-day or structural).
3. If ambiguous (request could match multiple segments), create a `needs_clarification` proposal with question + options, and ask the user to pick.
4. Otherwise generate the candidate plan: preserve segment IDs for unchanged segments, new `seg_*` IDs for new ones, no overlapping times, respect constraints. Note tradeoffs.
5. Comparative-score it against the current plan (see `references/scoring.md`); record `impact_summary` (score_before/after/delta, tradeoffs).
6. `POST /v1/trips/<id>/proposals` with the candidate, `status: "pending"`, and `base_version_id` = current plan version. **Present it to the user for review. Never auto-apply.**

### Apply / reject
`POST /v1/proposals/<pid>/apply` or `/reject`. Follow `references/lifecycle.md` exactly. Apply is idempotent; it refuses with `PROPOSAL_CONFLICT` when the plan has moved past the proposal's `base_version_id` (regenerate instead of forcing). On success the service swaps in `candidate_plan`, bumps the version, re-renders `plan.md`, marks the proposal `applied`, and git-commits.

### Init a new trip
1. Interview: language (en|zh) first, then dates, cities (with min/max days each), travelers, budget, vibes, anti-patterns, dietary, loyalty program.
2. `POST /v1/trips` with name + inline constraints (see openapi `POST /v1/trips` schema). Then `PUT .../constraints`, `PUT .../rubrics` (rubrics generated from constraints + learned signals per `references/scoring.md`).
3. Generate the baseline plan and `PUT /v1/trips/<id>/plan` as `v_001`. The service renders `plan.md` and commits. Write it to the narrative standard in `references/writing.md` — prose, not fragments; this is not optional polish, it is the plan.
4. If language is zh: prompts, plans, and research use Chinese sources (小红书, 大众点评, 马蜂窝, 携程) and Simplified Chinese throughout.

### Research a city
For each city gather activities, restaurants, neighborhoods-for-wandering, tourist traps, and seasonal highlights using web search and the browser (real ratings/reviews beat guesses). `PUT /v1/trips/<id>/activities` with per-entry `source` (`browser` > `search_api` > `llm_knowledge`); the scorer weights entries by source trust.

### Score a plan
Run the 3-pass methodology in `references/scoring.md`: (1) dimension scores against `rubrics.yaml` anchors, (2) adversarial critic penalties, (3) holistic adjustment. Use absolute scoring for recalibration, comparative (diff-only) scoring inside the run loop.

### Run — optimization loop
Follow `references/run-loop.md`: pick a mutation type (SWAP, REALLOCATE, REORDER, UPGRADE, SIMPLIFY, RESEARCH), generate one mutation, apply to a working copy, comparative-score it, keep or discard, and `POST /v1/trips/<id>/run-log` to append the iteration. The run log is append-only and never rewritten; it is the crash-recovery source of truth. Absolute score every 10 iterations. For long unattended runs, use a scheduled workflow that resumes from the run log.

### Reoptimize (scoped)
Same as run, but mutations are constrained to the scope (`day:3`, `city:Tokyo`, `period:dinner`).

### Debrief (post-trip)
Interview per day/activity: rating 1-5, better/expected/worse vs expectation, notes. `PUT /v1/profile` with the updated traveler profile, preference signals, activity calibration, source reliability, and learned anti-patterns. These calibrate the next trip's rubrics.

## Operating Rules
1. The agent is the LLM provider; the service holds state. Never ask the user for API keys — auth uses the stored `custom.trip-optimizer` connector.
2. `apply` / `reject` are write actions: a proposal is presented first and applied only on the user's explicit approval.
3. On `PROPOSAL_CONFLICT`, regenerate the proposal against the current plan version. Never force-apply.
4. The run log is append-only and never rewritten; it is the crash-recovery source of truth.
5. The service keeps `plan.md` in sync with `plan.json` after every applied change.
6. Respect `request_language` on proposals; default to the trip language.
7. Source tags on research entries are load-bearing for scoring — never omit them.
8. Plans are written to the narrative standard in `references/writing.md`. A plan whose segments are fragment lists is not a finished plan, and the scorer will penalize it.
9. Quote version IDs, proposal IDs, and trip IDs exactly; never invent them.
10. A 401/403 is a question about the request before a question about the key: confirm the request carried the credential (via `bin/trip.py`) before touching the connector.
