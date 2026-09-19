# Trip Optimizer — Proposal Lifecycle

Proposals are the ONLY way plans change outside the run loop. Statuses: `pending → applied | rejected`, plus `needs_clarification`.

## Propose
Write `proposals/prop_<unixtime>_<slug>.json` (slug = first 4 words of the request, lowercased, non-alphanumeric stripped). Fields per `data-model.md`. Rules:
- `base_version_id` = the plan's current `version_id`. This is the conflict-detection anchor.
- Candidate plan: preserve segment IDs for unchanged segments; generate new `seg_*` IDs for new segments; no overlapping `start_time`/`end_time`; respect `constraints.yaml` (hard_requirements are inviolable).
- `candidate_plan.version_id` = current version bumped by 1; `parent_version_id` = current version; `created_by` = `"propose"`.
- Include `tradeoffs` — what the change costs, not just what it gains.
- If the request is ambiguous, write `status: "needs_clarification"` with `candidate_plan: null` and `clarification: { question, options[] }`, then ask the user to pick an option before proceeding.

## Apply (exact semantics — ported from the CLI)
1. Resolve trip; read `proposals/<id>.json`. Unknown id → `PROPOSAL_NOT_FOUND`.
2. If `proposal.status == "applied"` → idempotent success: report `already_applied`, change nothing.
3. Read current `plan.json`. If `plan.version_id != proposal.base_version_id` → `PROPOSAL_CONFLICT`. Do NOT force-apply. Tell the user the plan moved and offer to regenerate the proposal against the current version.
4. If `proposal.candidate_plan == null` → refuse (nothing to apply; usually a `needs_clarification` proposal).
5. Write `candidate_plan` to `plan.json`.
6. Re-render `plan.md` from the new plan (day headers, segments in time order with times, locations, details).
7. Update proposal: `status = "applied"`.
8. Git commit `plan.json`, `plan.md`, and the proposal file: message `apply: <proposal_id> — <raw_request>`. Git failure is non-fatal (state is already written).
9. Report: `proposal_id`, `new_version_id`, `approved_by`, and the `impact_summary` (score delta, tradeoffs).

## Reject
Set `proposal.status = "rejected"`. Git commit the proposal file (non-fatal). Report confirmation. Nothing else changes.

## List / inspect
Read `proposals/*.json`, filter by `status` when asked. Summarize each: id, status, raw request, intent, scope, score delta, and for pending ones what applying would change.

## Approval policy
`propose` never applies. Present pending proposals (what changes, score delta, tradeoffs) and apply only on explicit user approval. This holds for every caller, including scheduled workflows.
