# Trip Optimizer — Optimization Run Loop

The autoresearch ratchet: research → mutate → score → keep/discard. You run the loop; each iteration is ONE mutation.

## Mutation types

| Type | What it does |
|---|---|
| SWAP | Replace an activity with a higher-scored alternative from `activities_db.json` |
| REALLOCATE | Move a day between cities (within min/max bounds in `constraints.yaml`) |
| REORDER | Rearrange a day's activities for better geographic clustering |
| UPGRADE | Replace a restaurant with a more authentic option |
| SIMPLIFY | Remove a low-scoring activity, leave free wandering time |
| RESEARCH | Discover new options for the weakest-scoring city, then attempt a swap |

Rotate through types; if 5+ consecutive discards, force RESEARCH next.

## Loop logic

1. Read current best `plan.json` + `results.tsv` tail (iteration count, best score, recent discards to avoid repeating).
2. Pick mutation type and generate the specific mutation as a working copy of the plan (do NOT touch the committed `plan.json` yet).
3. Bump the working copy's `version_id` (`v_NNN` → next) and set `parent_version_id`.
4. Comparative-score working copy vs current best (see `scoring.md`).
5. If improved (`delta > 0`): write working copy to `plan.json`, re-render `plan.md`, git commit with a descriptive message (`upgrade: Day 5 dinner -> Tsukiji omakase (+0.8)`), append `kept=yes` row to `results.tsv`.
6. If same or worse: discard the working copy (leave `plan.json` untouched), append `kept=no` row.
7. Every 10th iteration: run absolute scoring on the current best and update `plan.json` → `score`.
8. Repeat until interrupted or a stop condition hits.

## Stop conditions
- User interrupts.
- Iteration budget reached (agree one with the user for unattended runs; default 100).
- Score plateau: no improvement in the last 25 iterations.

## Crash recovery
`results.tsv` is append-only and gitignored — it survives resets. On restart: last row gives iteration count and best score; the git log gives the kept mutations. Never repeat a discarded mutation verbatim.

## Unattended / overnight runs
Run the loop as a scheduled workflow (cron) that resumes from `results.tsv` each invocation and processes a bounded batch of iterations per run. Report on completion: baseline → final score, iteration count, top mutations kept.

## Status reporting
From `plan.json` (`score`, `version_id`) + `results.tsv` tail, report: current composite and delta vs baseline, per-dimension trend (last absolute scoring), last 5 mutations with deltas, research coverage per city (entry counts in `activities_db.json`), remaining known penalties.
