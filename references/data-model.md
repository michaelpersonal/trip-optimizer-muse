# Trip Optimizer — Data Model

Global dir: `~/.trip-optimizer/`. Per-trip dir: registered in `trips.json`, itself a git repo.

## `trips.json` (registry)

```json
{
  "trips": {
    "japan-2027": {
      "path": "/home/user/trips/japan-2027",
      "title": "Japan 2027",
      "created_at": "2027-01-05T10:00:00Z",
      "status": "active"
    }
  },
  "default_trip": "japan-2027"
}
```

Trip resolution order: explicit id → `default_trip` → error `NO_TRIP_CONTEXT`. Unknown id → `TRIP_NOT_FOUND`. Duplicate id on register → `TRIP_ID_CONFLICT`.

## `plan.json`

```json
{
  "version_id": "v_001",
  "parent_version_id": null,
  "created_at": "2027-01-05T10:00:00Z",
  "created_by": "init",
  "score": { "composite": 72.4, "components": { "experience": 75.0, "food": 80.0 } },
  "days": [
    {
      "day_index": 1,
      "date": "2027-03-15",
      "city": "Tokyo",
      "hotel": "Park Hotel Tokyo",
      "transit": { "mode": "flight", "detail": "DL295 ATL→HND" },
      "segments": [
        {
          "id": "seg_m1a2b3c4d",
          "type": "activity",
          "period": "evening",
          "title": "Shinjuku backstreet wandering",
          "details": "Omoide Yokocho and the alleys two blocks east. (Full prose paragraphs per references/writing.md — never fragments.)",
          "why": "The story or reason this stop earns its place (history, human detail, technical marvel).",
          "skip_note": "The famous nearby thing NOT worth it, and why.",
          "alternatives": [{"label": "A", "text": "Rainy-day swap: ..."}],
          "location": "Shinjuku, Tokyo",
          "start_time": "18:00",
          "end_time": "21:00",
          "tags": ["wandering", "food"]
        }
      ],
      "theme": "Day subtitle, e.g. 外滩、弄堂与梧桐树",
      "transition": "One or two sentences connecting this day to the previous one (the emotional gear-shift).",
      "notes": ""
    }
  ],
  "logistics": [
    {"heading": "签证与入境", "body": "Pre-trip prep prose..."},
    {"heading": "支付与通讯", "body": "..."},
    {"heading": "交通预订", "body": "..."},
    {"heading": "天气与穿着", "body": "..."},
    {"heading": "行李与住宿须知", "body": "..."},
    {"heading": "旅行保险", "body": "..."}
  ]
}
```

- `version_id`: `v_NNN`, zero-padded. Bump by 1 on every applied change; set `parent_version_id` to the previous version.
- `type`: one of `activity | meal | transit | free_time | hotel`.
- `period`: one of `morning | lunch | afternoon | dinner | evening`.
- `id`: `seg_` + base36 timestamp + 4 random chars (uniqueness is what matters, not the exact scheme).
- `score.components`: per-dimension scores from the last absolute scoring.
- `details` is prose, never fragments — see `references/writing.md`. `why`, `skip_note`, `alternatives`, `theme`, `transition` are optional but a finished plan should use them: a plan without opinions, alternatives, or a logistics preamble is not done.
- `logistics` (行前准备与后勤须知) is REQUIRED on every plan, with the standard sections (签证与入境， 支付与通讯， 交通预订， 天气与穿着， 行李与住宿须知， 旅行保险）. A plan without it is incomplete.

## `proposals/<proposal_id>.json`

```json
{
  "proposal_id": "prop_1798765432_change_day3_dinner",
  "trip_id": "japan-2027",
  "base_version_id": "v_014",
  "status": "pending",
  "requested_by": "user",
  "requested_at": "2027-02-01T12:00:00Z",
  "request_language": "en",
  "raw_request": "change day 3 dinner to something less touristy",
  "intent": "direct_override",
  "scope": { "day_index": 3, "segment_id": "seg_m1a2b3c4d", "period": "dinner" },
  "candidate_plan": { "... full Plan object, version_id bumped to v_015 ..." },
  "impact_summary": {
    "changed_segments": ["seg_m1a2b3c4d"],
    "score_before": 82.1,
    "score_after": 83.4,
    "score_delta": 1.3,
    "tradeoffs": ["Loses the sunset view from the original spot"]
  },
  "explanation": { "en": "...", "zh": "..." }
}
```

- `proposal_id`: `prop_<unixtime>_<first-4-words-slug>`.
- `status`: `pending | applied | rejected | needs_clarification`.
- `needs_clarification` proposals have `candidate_plan: null`, `impact_summary: null`, plus `clarification: { question, options: [{ day_index, segment_id, title }] }`.
- `intent`: `direct_override | scoped_reoptimize | structural_change`.

## `constraints.yaml`

```yaml
trip:
  name: "Japan 2027"
  start_date: 2027-03-15
  end_date: 2027-03-28
  total_days: 14
  travelers: 2
  origin: Atlanta
cities:
  - name: Tokyo
    key: tokyo
    min_days: 3
    max_days: 6
hard_requirements:
  - City ordering cannot change
preferences:
  priority_order: [wandering, food, culture]
  anti_patterns: [tourist traps, long queues]
  pro_patterns: [back-alley local spots, neighborhood wandering]
dietary: []
loyalty_program: marriott_bonvoy
budget: { total: 8000, currency: USD }
```

## `rubrics.yaml`

LLM-generated per trip (see `scoring.md`). Shape:

```yaml
dimensions:
  - key: experience
    weight: 0.25
    sub_dimensions:
      - key: authenticity
        anchor_10: "..."
        anchor_1: "..."
adversarial_penalties:
  - rule: "Chain restaurant listed as a food highlight"
    deduction: 5
    max_per_dimension: 20
```

Dimensions are NOT fixed — they are generated per trip type. Weights sum to 1.

## `activities_db.json`

```json
{
  "tokyo": {
    "activities": [
      {
        "name": "Yanaka Old Town wandering",
        "type": "vibe",
        "score": 8, "authenticity": 9, "uniqueness": 7,
        "notes": "Quiet old neighborhood, cat streets, traditional shops",
        "crowd_level": "low", "cost_per_person": 0, "currency": "JPY",
        "duration_hours": 2, "location": "Yanaka, Taito-ku",
        "best_time": "morning", "seasonal": null,
        "source": "dianping"
      }
    ],
    "restaurants": [
      {
        "name": "Fuunji", "cuisine": "tsukemen ramen",
        "score": 9, "authenticity": 9,
        "notes": "Legendary dipping ramen. 30 min queue but worth it.",
        "cost_per_person": 1200, "currency": "JPY",
        "location": "Shinjuku", "reservation_needed": false,
        "source": "google_maps"
      }
    ],
    "neighborhoods_for_wandering": [
      { "name": "Shimokitazawa", "vibe_score": 9, "walkability": "excellent",
        "notes": "Vintage shops, tiny bars, live music venues, no chains" }
    ],
    "tourist_traps": [
      { "name": "Robot Restaurant", "reason": "Overpriced, gimmicky, tourist-only" }
    ],
    "seasonal_highlights": ["Cherry blossom peak mid-March — Meguro River"]
  }
}
```

Every entry carries `source` (`browser` > `search_api` > `llm_knowledge`). Never omit it.

## `results.tsv` (gitignored, append-only)

Tab-separated, one row per iteration:

```
iteration	timestamp	mutation_type	description	score_before	score_after	delta	kept
47	2027-02-01T02:14:00Z	UPGRADE	Day 5 dinner -> Tsukiji omakase	86.7	87.5	0.8	yes
48	2027-02-01T02:16:00Z	SWAP	Day 3 temple -> garden walk	87.5	87.3	-0.2	no
```

Crash recovery: on restart, read the last row for iteration count and best score; never repeat a discarded mutation verbatim.

## Global memory files

`profile.json` — loyalty, dietary, stated/learned vibes, anti-patterns (stated + learned), source trust weights, trips completed.
`trip-history.json` — past trips with per-activity debrief ratings.
`learned.json` — LLM-distilled signals across all debriefs: `preference_signals[]`, `activity_calibration[]` (expected vs actual ratings), `source_reliability{}`, `anti_patterns_learned[]`.
`config.json` — `{ "language": "en" }`.
