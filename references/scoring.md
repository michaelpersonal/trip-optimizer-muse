# Trip Optimizer — Scoring Methodology

Three-pass LLM-as-judge scoring. You perform all three passes natively.

## Rubric generation (per trip, at init)

Generate `rubrics.yaml` from `constraints.yaml` + `profile.json` + `learned.json`:
- Dimensions are NOT fixed. Derive them from the trip type (a food trip gets `food_depth`; a solo backpacking trip might get `social_opportunities` instead of `accommodation_quality`). Typical seed set: experience, logistics, food, time management, budget, accommodation, transit.
- Each dimension: `weight` (sum to 1), `sub_dimensions` with 1–10 anchors written for THIS trip.
- Calibrate with learned signals: activities the user loved in past debriefs raise the anchors for similar types; hated ones become `adversarial_penalties` rules; `source_reliability` from `learned.json` adjusts how much you trust `activities_db` entries by source.
- Include an `adversarial_penalties` list: concrete flaw patterns (unconfirmed bookings, chain restaurants as highlights, vague transit like "explore the city", 2hr+ queues on a packed day) with per-violation deductions.

## Narrative dimension (always include)

Every trip's rubric gets a `narrative` dimension (~15% weight, rebalanced so weights sum to 1). It scores the plan as a piece of writing per `references/writing.md`:
- `prose_quality` (1: telegram fragments; 4: complete sentences but flat; 7: real paragraphs with some texture; 10: reads like a travel writer — sensory, specific, alive)
- `opinionatedness` (1: endorses everything equally; 4: one mild opinion; 7: explicit skips with reasons; 10: strong takes + trade-off callouts that show judgment)
- `alternatives` (1: single fixed path; 4: one backup; 7: labeled A/B/C options per day; 10: weather/mood/energy alternatives woven through every day)
- `logistics_completeness` (1: nothing before Day 1; 4: a visa line; 7: entry, payments, transport booking covered; 10: full preamble — entry, payments/connectivity, transport booking, weather/packing, group coordination)
- Penalty: any segment whose `details` is a fragment list rather than prose → −3 per occurrence (cap −15 on the dimension).

## Pass 1 — Dimension scoring
Score the plan 0–100 per sub-dimension against the rubric anchors. One-sentence justification per score. Be honest, not generous: a good plan scores in the 70s–80s; 90+ should be rare.

## Pass 2 — Adversarial critic
Fresh eyes, only looking for flaws. List concrete violations with day numbers and point deductions per the `adversarial_penalties` rules. Cap: −20 per dimension. If a flaw isn't in the rules but is clearly a flaw (e.g. a restaurant that closed), add it with a cited reason.

## Pass 3 — Holistic adjustment
Review all dimension scores together for interactions the first two passes missed. Example: "food scored high but logistics shows a 10-hour transit day — that's actually smart station-food integration, bump food +2." Cap: ±5 per dimension.

## Composite
`score = Σ (dimension_weight × dimension_score)`, 0–100. Store in `plan.json` → `score.composite` / `score.components` after absolute scoring.

## Absolute vs comparative
- **Absolute**: full three passes. Use for baselines, recalibration (every 10th run-loop iteration), and final reporting.
- **Comparative**: given old plan + new plan + mutation description, score ONLY the affected sub-dimensions and report `composite_delta`. Cheaper and more stable; use for every run-loop iteration and for proposal `impact_summary`.
- If a proposal lacks full context for scoring (no rubrics/constraints/activities), still record tradeoffs and set `score_delta: 0` rather than guessing.

## Score presentation
Report the composite with one decimal, the delta vs baseline, and the top 2–3 dimension movers. Keep justifications to one line each — the user reads these on a phone.
